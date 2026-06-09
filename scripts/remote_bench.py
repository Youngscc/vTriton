#!/usr/bin/env python3
"""
remote_bench.py — Remote 910B3 validation runner for A.6.1

Syncs local repo → remote 910B3, runs msprof profiling, fetches CSV back.

Usage:
    python scripts/remote_bench.py --host <remote> --kernel <name> --output <csv_path>

Responsibilities:
- SSH sync local repo → remote 910B3 under tlx env
- Source CANN env (/usr/local/Ascend/cann/set_env.sh)
- Run msprof --application=<exe> --output=<msprof_dir> on remote
- rglob("mindstudio_profiler_output/**/op_summary_*.csv") to locate output
- Sync CSV back to a local temp path
- Return the local CSV path to the caller

Not in scope:
- SSH key management (assumes ssh-agent or key already configured)
- Remote CANN install (assumes CANN already installed)
- Kernel binary compilation (binary must already exist on remote)

Source spec: .omc/plans/a6_validation_harness.md §5
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path


def sync_to_remote(
    local_path: Path,
    remote_host: str,
    remote_path: str,
) -> None:
    """Sync local directory to remote via rsync.

    Args:
        local_path: Local directory to sync.
        remote_host: SSH host (user@hostname).
        remote_path: Remote destination path.
    """
    cmd = [
        "rsync", "-avz", "--delete",
        f"{local_path}/",
        f"{remote_host}:{remote_path}/",
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def run_msprof_remote(
    remote_host: str,
    remote_path: str,
    kernel_exe: str,
    msprof_dir: str = "msprof_output",
) -> None:
    """Run msprof profiling on remote.

    Args:
        remote_host: SSH host.
        remote_path: Remote repo path.
        kernel_exe: Path to kernel executable on remote.
        msprof_dir: Output directory for msprof (relative to remote_path).
    """
    # Source CANN env and run msprof.
    # NOTE: ssh passes the entire script string as one remote shell command.
    # Do NOT use ["ssh", host, "bash", "-c", script] — ssh joins argv with
    # spaces, so only the first token after -c becomes the command.
    # Also: `conda activate` requires the conda shell hook; source it via
    # the standard profile.d path for non-interactive shells.
    script = (
        f"cd {remote_path}"
        f" && source /usr/local/Ascend/cann/set_env.sh"
        f" && source $(conda info --base)/etc/profile.d/conda.sh"
        f" && conda activate tlx"
        f" && msprof --application={kernel_exe} --output={msprof_dir}"
    )
    cmd = ["ssh", remote_host, script]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def fetch_csv_from_remote(
    remote_host: str,
    remote_path: str,
    msprof_dir: str,
    local_output: Path,
) -> Path:
    """Fetch op_summary CSV from remote.

    Args:
        remote_host: SSH host.
        remote_path: Remote repo path.
        msprof_dir: msprof output directory (relative to remote_path).
        local_output: Local path to write CSV.

    Returns:
        Path to local CSV file.

    Raises:
        FileNotFoundError: No op_summary CSV found on remote.
    """
    # Find CSV on remote
    find_cmd = f"find {remote_path}/{msprof_dir} -name 'op_summary_*.csv' | head -n 1"
    result = subprocess.run(
        ["ssh", remote_host, find_cmd],
        check=True, capture_output=True, text=True,
    )
    remote_csv = result.stdout.strip()
    if not remote_csv:
        raise FileNotFoundError(f"No op_summary CSV found in {remote_path}/{msprof_dir}")

    # Fetch CSV
    local_output.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["scp", f"{remote_host}:{remote_csv}", str(local_output)]
    subprocess.run(cmd, check=True, capture_output=True, text=True)

    return local_output


def run_remote_bench(
    remote_host: str,
    kernel_name: str,
    kernel_script: Path | None = None,
    output_csv: Path | None = None,
    remote_path: str = "~/vTriton",
) -> Path:
    """Run remote validation benchmark.

    Args:
        remote_host: SSH host (user@hostname).
        kernel_name: Kernel identifier.
        kernel_script: Path to kernel run script (optional).
        output_csv: Local path for output CSV (auto-generated if None).
        remote_path: Remote repo path.

    Returns:
        Path to local op_summary CSV.
    """
    local_repo = Path(__file__).parent.parent

    if output_csv is None:
        tmpdir = Path(tempfile.mkdtemp())
        output_csv = tmpdir / f"{kernel_name}_op_summary.csv"

    # Sync local → remote
    sync_to_remote(local_repo, remote_host, remote_path)

    # Run msprof on remote
    kernel_exe = f"{remote_path}/build/bin/{kernel_name}"
    msprof_dir = "msprof_output"
    run_msprof_remote(remote_host, remote_path, kernel_exe, msprof_dir)

    # Fetch CSV back
    return fetch_csv_from_remote(remote_host, remote_path, msprof_dir, output_csv)


def _cli():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Remote 910B3 validation runner for A.6.1",
    )
    parser.add_argument("--host", required=True, help="Remote SSH host (user@hostname)")
    parser.add_argument("--kernel", required=True, help="Kernel name or identifier")
    parser.add_argument("--output", required=True, help="Local output CSV path")
    parser.add_argument("--script", help="Kernel run script (optional)")
    parser.add_argument("--remote-path", default="~/vTriton", help="Remote repo path")

    args = parser.parse_args()

    kernel_script = Path(args.script) if args.script else None
    output_csv = Path(args.output)

    try:
        csv_path = run_remote_bench(
            remote_host=args.host,
            kernel_name=args.kernel,
            kernel_script=kernel_script,
            output_csv=output_csv,
            remote_path=args.remote_path,
        )
        print(f"CSV fetched: {csv_path}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _cli()
