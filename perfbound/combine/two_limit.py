# M5 / A.7 — Two-Limit Computation
#
# T_bound_HIVM = bound with avoidable gaps analytically relaxed to zero
#                (NOT by editing), subject to register/buffer/capacity/
#                divisibility constraints
# T_bound_DSL  = bound over HIVM bishengir actually emits (realized
#                structural constraints)
#
# gap = (T_bound_DSL − T_bound_HIVM) → compiler headroom;
#       (T_measured − T_bound_DSL)   → kernel-author headroom
#
# T_bound_HIVM must be computed under hardware-legality limits (the same
# constraints M2/M3 enforce), not an affine-tiling-only idealization.
#
# Source spec: .omc/specs/performance_bound_model.md §A.7

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class TwoLimitResult:
    """Two-limit gap analysis for a single kernel."""
    kernel_name: str

    t_bound_hivm_us: float       # analytically relaxed (hardware-legal)
    t_bound_dsl_us: float         # realized bishengir structure
    t_measured_us: Optional[float] = None  # from msprof (M6)

    @property
    def compiler_headroom_us(self) -> float:
        return self.t_bound_dsl_us - self.t_bound_hivm_us

    @property
    def author_headroom_us(self) -> Optional[float]:
        if self.t_measured_us is None:
            return None
        return self.t_measured_us - self.t_bound_dsl_us

    def __repr__(self) -> str:
        return (f"TwoLimit({self.kernel_name}: "
                f"HIVM={self.t_bound_hivm_us:.2f}, "
                f"DSL={self.t_bound_dsl_us:.2f}, "
                f"measured={self.t_measured_us})")


def compute_two_limit(
    kernel_name: str,
    t_bound_dsl_us: float,
    t_measured_us: Optional[float] = None,
) -> TwoLimitResult:
    """Compute T_bound_HIVM by analytically relaxing avoidable gaps.

    Args:
        kernel_name: Kernel identifier.
        t_bound_dsl_us: The realized DSL bound (from M5 combine).
        t_measured_us: Optional measured time for author-headroom gap.

    Returns:
        TwoLimitResult with compiler + author headroom gaps.

    Raises:
        NotImplementedError: Two-limit model not yet implemented.
    """
    raise NotImplementedError(
        "Two-limit computation not yet implemented. "
        "Requires M2 hardware-legality constraints and M4 analytical relaxation."
    )
