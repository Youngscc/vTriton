#!/usr/bin/env python3
"""
kernel_launcher.py — Remote Triton kernel launcher for msprof profiling.

Loads a kernel module by path, builds inputs, runs the kernel under
torch_npu, and dumps the output tensor(s) to .npy for correctness
verification.

Usage (on remote 910B3):
    python scripts/kernel_launcher.py \\
        --kernel test/chunk_kda_bwd_kernel_wy_dqkg_fused_opt_v2.py \\
        --output-dir kernel_outputs \\
        --iters 10

Expected kernel module interface:
    - build_inputs() → dict of kwargs (tensors on 'npu')
    - Model class with forward(data) → tuple of output tensors
      OR a main() function

The launcher writes:
    <output-dir>/kernel_output_0.npy  (first output tensor)
    <output-dir>/kernel_output_1.npy  (second output tensor, if any)
    ...
    <output-dir>/kernel_output.npy    (alias for first output, for
                                       backward compat with fetch_output)

Source spec: .omc/plans/a6_2_blockers_scope.md Blocker 2 gap #2
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
import time
from pathlib import Path


def load_kernel_module(kernel_path: str):
    """Dynamically import a Python kernel module from a file path.

    Args:
        kernel_path: Path to the .py file containing the kernel.

    Returns:
        The imported module object.

    Raises:
        FileNotFoundError: If kernel_path does not exist.
        ImportError: If the module cannot be loaded.
    """
    path = Path(kernel_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Kernel script not found: {path}")

    module_name = path.stem
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create module spec from {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def run_kernel(module, iters: int = 10) -> list:
    """Run the kernel from a loaded module and return output tensors.

    Probes the module for standard entry points in preference order:
    1. module.main() — if present, call it directly (returns outputs)
    2. module.build_inputs() + module.Model().forward(data) — standard
       Triton kernel pattern
    3. module.Model().forward(module.build_inputs()) — fallback

    Args:
        module: The imported kernel module.
        iters: Number of iterations to run (for warmup + measurement).

    Returns:
        List of output tensors (torch.Tensor on CPU).
    """
    import torch

    # Strategy 1: module has a main() function
    if hasattr(module, "main"):
        return module.main()

    # Strategy 2: build_inputs + Model
    if not hasattr(module, "build_inputs"):
        raise RuntimeError(
            f"Kernel module {module.__name__} has no build_inputs() or main(). "
            f"The launcher requires one of these entry points."
        )

    data = module.build_inputs()

    if hasattr(module, "Model"):
        model = module.Model()
        # Warmup: 1 iteration (also catches compile errors early)
        _ = model.forward({k: v.clone() if hasattr(v, 'clone') else v
                           for k, v in data.items()})

        # Timed iterations
        outputs = None
        for _ in range(iters):
            # Rebuild data each iteration to avoid in-place mutation artifacts
            run_data = module.build_inputs()
            outputs = model.forward(run_data)

        if outputs is None:
            raise RuntimeError("Model.forward() returned None")

        # Normalize to list
        if isinstance(outputs, torch.Tensor):
            outputs = [outputs]
        elif isinstance(outputs, (tuple, list)):
            outputs = list(outputs)
        else:
            outputs = [outputs]

        return [o.cpu() if hasattr(o, 'cpu') else o for o in outputs]

    raise RuntimeError(
        f"Kernel module {module.__name__} has build_inputs() but no Model class "
        f"or main() function."
    )


def save_outputs(outputs: list, output_dir: str) -> list[Path]:
    """Save output tensors to .npy files.

    Args:
        outputs: List of output tensors (on CPU).
        output_dir: Directory to write .npy files.

    Returns:
        List of paths to written .npy files.
    """
    import numpy as np

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    saved = []
    for i, tensor in enumerate(outputs):
        arr = tensor.numpy() if hasattr(tensor, 'numpy') else np.asarray(tensor)
        npy_path = out_path / f"kernel_output_{i}.npy"
        np.save(npy_path, arr)
        saved.append(npy_path)

    # Backward-compat alias: kernel_output.npy → first output
    if saved:
        import shutil
        compat_path = out_path / "kernel_output.npy"
        shutil.copy2(saved[0], compat_path)

    return saved


def main():
    parser = argparse.ArgumentParser(
        description="Launch a Triton kernel for msprof profiling.",
    )
    parser.add_argument(
        "--kernel", required=True,
        help="Path to kernel .py file (e.g. test/chunk_kda_...py)",
    )
    parser.add_argument(
        "--output-dir", default="kernel_outputs",
        help="Directory to write output .npy files",
    )
    parser.add_argument(
        "--iters", type=int, default=10,
        help="Number of kernel iterations to run (default: 10)",
    )
    args = parser.parse_args()

    print(f"[kernel_launcher] Loading kernel from {args.kernel}", file=sys.stderr)
    module = load_kernel_module(args.kernel)

    print(f"[kernel_launcher] Running {args.iters} iterations...", file=sys.stderr)
    t0 = time.time()
    outputs = run_kernel(module, iters=args.iters)
    elapsed = time.time() - t0
    print(f"[kernel_launcher] Done in {elapsed:.2f}s, "
          f"{len(outputs)} output(s)", file=sys.stderr)

    saved = save_outputs(outputs, args.output_dir)
    for p in saved:
        print(f"[kernel_launcher] Saved {p}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
