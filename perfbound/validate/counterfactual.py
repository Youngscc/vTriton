# M6 — Counterfactual Validation
#
# Hand-edit HIVM (raise repeat, insert ping-pong), recompile via bishengir,
# verify correctness (output equivalence with reference), measure delta
# via msprof.
#
# Confirms a gap's quantified value matches measured improvement
# (validates attribution, separate from validating the bound).
#
# Source spec: .omc/specs/performance_bound_model.md §A.6

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class CounterfactualResult:
    """Result of a single counterfactual experiment."""
    kernel_name: str
    gap_name: str               # e.g. "gap3_avoidable_serial"

    # Predicted
    predicted_gap_us: float

    # Measured (before → after counterfactual edit)
    t_before_us: float
    t_after_us: float
    measured_delta_us: float

    # Validity
    output_verified: bool       # did edited kernel produce same output?

    @property
    def quantification_error(self) -> float:
        """Relative error of predicted gap vs measured delta."""
        if self.measured_delta_us == 0:
            return float("inf")
        return abs(self.predicted_gap_us - self.measured_delta_us) / self.measured_delta_us

    @property
    def is_valid(self) -> bool:
        """A valid counterfactual: output verified + error < 20% (Exp 3 target)."""
        return self.output_verified and self.quantification_error < 0.20

    def __repr__(self) -> str:
        return (f"Counterfactual({self.kernel_name}/{self.gap_name}: "
                f"predicted={self.predicted_gap_us:.2f}, "
                f"measured={self.measured_delta_us:.2f}, "
                f"error={self.quantification_error:.3f}, "
                f"verified={self.output_verified})")


def run_counterfactual(
    kernel_name: str,
    gap_name: str,
    predicted_gap_us: float,
    hivm_edit_script: str,
    remote_bench_skill=None,
) -> CounterfactualResult:
    """Run a counterfactual experiment by editing HIVM and re-profiling.

    Args:
        kernel_name: Kernel to test.
        gap_name: Attribution gap being tested.
        predicted_gap_us: The gap value predicted by the model.
        hivm_edit_script: Path to script that edits HIVM (e.g., raises repeat).
        remote_bench_skill: Optional remote-bench skill reference.

    Returns:
        CounterfactualResult with pre/post timing and verification status.

    Raises:
        NotImplementedError: Counterfactual runner not yet implemented.
    """
    raise NotImplementedError(
        "Counterfactual runner not yet implemented. "
        "Requires remote-bench-910b3 for recompilation + msprof profiling."
    )
