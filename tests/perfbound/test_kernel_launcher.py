# Tests for kernel_launcher.py (A.6.2 — remote Triton kernel launcher)
#
# The launcher is the on-device core: it loads a kernel module, probes for a
# standard entry point, runs it, and dumps outputs to .npy for correctness
# verification. It runs on the remote 910B3, but its three functions are
# pure enough to unit-test offline (torch CPU tensors + numpy).
#
# Source spec: .omc/plans/a6_2_blockers_scope.md Blocker 2 gap #2/#4

import sys
import types
from pathlib import Path

import numpy as np
import pytest

# scripts/ is a sibling of tests/ — make it importable.
_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(_SCRIPTS))

from kernel_launcher import load_kernel_module, run_kernel, save_outputs

torch = pytest.importorskip("torch")


# ── load_kernel_module ─────────────────────────────────────────────────

class TestLoadKernelModule:
    def test_loads_file_and_exposes_symbols(self, tmp_path):
        mod_file = tmp_path / "mykernel.py"
        mod_file.write_text("MAGIC = 42\ndef build_inputs():\n    return {}\n")
        mod = load_kernel_module(str(mod_file))
        assert mod.MAGIC == 42
        assert hasattr(mod, "build_inputs")
        assert mod.__name__ == "mykernel"

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            load_kernel_module("/nonexistent/kernel.py")


# ── run_kernel: entry-point probing ────────────────────────────────────

def _module(name: str) -> types.ModuleType:
    return types.ModuleType(name)


class TestRunKernelEntryPoints:
    def test_main_strategy_returned_directly(self):
        """A module exposing main() is called directly; its result is returned."""
        m = _module("k_main")
        sentinel = [torch.tensor([1.0, 2.0])]
        m.main = lambda: sentinel
        assert run_kernel(m, iters=1) is sentinel

    def test_build_inputs_model_returns_single_tensor(self):
        """build_inputs() + Model.forward() returning a tensor → [cpu_tensor]."""
        m = _module("k_model")
        m.build_inputs = lambda: {"x": torch.tensor([3.0, 4.0])}

        class Model:
            def forward(self, data):
                return data["x"] * 2

        m.Model = Model
        out = run_kernel(m, iters=2)
        assert isinstance(out, list) and len(out) == 1
        assert torch.allclose(out[0], torch.tensor([6.0, 8.0]))

    def test_model_returning_tuple_is_normalized_to_list(self):
        m = _module("k_tuple")
        m.build_inputs = lambda: {"x": torch.tensor([1.0])}

        class Model:
            def forward(self, data):
                return (data["x"], data["x"] + 1)

        m.Model = Model
        out = run_kernel(m, iters=1)
        assert isinstance(out, list) and len(out) == 2

    def test_no_entry_point_raises(self):
        m = _module("k_empty")
        with pytest.raises(RuntimeError, match="no build_inputs|main"):
            run_kernel(m, iters=1)

    def test_build_inputs_without_model_or_main_raises(self):
        m = _module("k_partial")
        m.build_inputs = lambda: {"x": torch.tensor([1.0])}
        with pytest.raises(RuntimeError, match="no Model class|main"):
            run_kernel(m, iters=1)

    def test_model_returning_none_raises(self):
        m = _module("k_none")
        m.build_inputs = lambda: {"x": torch.tensor([1.0])}

        class Model:
            def forward(self, data):
                return None

        m.Model = Model
        with pytest.raises(RuntimeError, match="returned None"):
            run_kernel(m, iters=1)


# ── save_outputs ───────────────────────────────────────────────────────

class TestSaveOutputs:
    def test_writes_indexed_npy_and_compat_alias(self, tmp_path):
        outs = [np.array([1.0, 2.0]), np.array([[3.0], [4.0]])]
        saved = save_outputs(outs, str(tmp_path))
        assert [p.name for p in saved] == ["kernel_output_0.npy", "kernel_output_1.npy"]
        for p in saved:
            assert p.exists()
        # Backward-compat alias points at the first output.
        alias = tmp_path / "kernel_output.npy"
        assert alias.exists()
        np.testing.assert_array_equal(np.load(alias), outs[0])

    def test_roundtrip_values_preserved(self, tmp_path):
        out = np.arange(12, dtype=np.float32).reshape(3, 4)
        saved = save_outputs([out], str(tmp_path))
        np.testing.assert_array_equal(np.load(saved[0]), out)

    def test_accepts_torch_tensors(self, tmp_path):
        saved = save_outputs([torch.tensor([5.0, 6.0])], str(tmp_path))
        np.testing.assert_array_equal(np.load(saved[0]), np.array([5.0, 6.0]))

    def test_empty_outputs_no_alias(self, tmp_path):
        saved = save_outputs([], str(tmp_path))
        assert saved == []
        assert not (tmp_path / "kernel_output.npy").exists()

    def test_creates_missing_output_dir(self, tmp_path):
        nested = tmp_path / "a" / "b" / "outputs"
        saved = save_outputs([np.array([1.0])], str(nested))
        assert saved[0].exists()
        assert (nested / "kernel_output.npy").exists()
