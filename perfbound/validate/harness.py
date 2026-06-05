# M6 — Validation Harness (NOT part of the model)
#
# The only place compilation + execution happen.  Drives the
# remote-bench-910b3 skill for:
#   1. Soundness:  T_bound ≤ T_measured  (binary, must hold 100%)
#   2. Tightness:  T_measured / T_bound   (record median)
#   3. Counterfactual validation
#
# Integration contract with remote-bench-910b3 skill (§7 of A.0 plan).
#
# Source spec: .omc/specs/performance_bound_model.md §A.6

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ValidationResult:
    """Soundness and tightness for a single kernel."""
    kernel_name: str
    t_bound_us: float
    t_measured_us: float

    is_sound: bool                 # T_bound ≤ T_measured
    tightness: float               # T_measured / T_bound

    msprof_source: str = ""        # path to op_summary CSV
    notes: str = ""


@dataclass
class ValidationSuite:
    """Results for a full validation suite."""
    results: List[ValidationResult] = field(default_factory=list)

    @property
    def soundness_rate(self) -> float:
        """Fraction of kernels where T_bound ≤ T_measured."""
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.is_sound) / len(self.results)

    @property
    def median_tightness(self) -> float:
        """Median T_measured / T_bound (on optimized kernels)."""
        if not self.results:
            return 0.0
        sorted_t = sorted(r.tightness for r in self.results)
        n = len(sorted_t)
        if n % 2 == 0:
            return (sorted_t[n // 2 - 1] + sorted_t[n // 2]) / 2
        return sorted_t[n // 2]

    @property
    def violations(self) -> List[ValidationResult]:
        """Kernels where the bound was violated (unsound)."""
        return [r for r in self.results if not r.is_sound]

    def summary(self) -> str:
        lines = [
            f"=== Validation Suite Results ===",
            f"Total kernels: {len(self.results)}",
            f"Soundness: {self.soundness_rate:.1%} ({sum(1 for r in self.results if r.is_sound)}/{len(self.results)})",
            f"Median tightness: {self.median_tightness:.3f}",
        ]
        if self.violations:
            lines.append(f"VIOLATIONS ({len(self.violations)}):")
            for v in self.violations:
                lines.append(f"  {v.kernel_name}: T_bound={v.t_bound_us:.2f} > T_measured={v.t_measured_us:.2f}")
        return "\n".join(lines)


def run_validation(
    kernel_list: List[str],
    bound_function,
    remote_bench_skill=None,
) -> ValidationSuite:
    """Compile, run, profile, and validate a list of kernels.

    Args:
        kernel_list: List of kernel names or paths to validate.
        bound_function: Callable(kernel_name) → BoundResult.
        remote_bench_skill: Optional remote-bench-910b3 skill reference.

    Returns:
        ValidationSuite with per-kernel soundness/tightness.

    Raises:
        NotImplementedError: Harness not yet implemented.
    """
    raise NotImplementedError(
        "Validation harness not yet implemented. "
        "Requires remote-bench-910b3 skill integration and M5 combiner."
    )
