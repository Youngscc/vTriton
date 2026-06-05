# M5 — Bound Combiner (two-tier max + T_serial_irreducible)
#
# T_bound = max(T_grid_floor, T_core_floor) + T_serial_irreducible
#
# Composition is max (two independent lower bounds on the same wall-clock
# time), with + T_serial_irreducible attaching to the Tier-2 term.
#
# Also computes the five-way attribution (separate from 6 roofline components):
#   grid, Gap1 (wrong-unit), Gap2 (coalescing/MTE-E), Gap3 (avoidable
#   serialization/MTE-R), Gap4 (intra-unit execution/compute-E)
#
# Source spec: .omc/specs/performance_bound_model.md §3, §4.2, §A.5

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

from ..model.grid_model import GridBound
from ..model.component_model import ComponentBound
from ..model.serialization import SerializationSplit
from ..extract.op_classifier import Component


class BindingTier(str, Enum):
    """Which tier binds the overall performance."""
    GRID = "grid"
    COMPONENT = "component"
    SERIAL = "serial"


@dataclass
class Attribution:
    """Five-way gap attribution for a single kernel."""
    # Raw gaps (microseconds)
    grid_gap_us: float = 0.0
    gap1_wrong_unit_us: float = 0.0
    gap2_coalescing_us: float = 0.0
    gap3_avoidable_serial_us: float = 0.0
    gap4_intra_unit_exec_us: float = 0.0

    # As fractions of T_bound
    grid_gap_frac: float = 0.0
    gap1_frac: float = 0.0
    gap2_frac: float = 0.0
    gap3_frac: float = 0.0
    gap4_frac: float = 0.0

    def dominant_gap(self) -> tuple[str, float]:
        """Return (gap_name, fraction) of the largest gap."""
        gaps = [
            ("grid", self.grid_gap_frac),
            ("gap1_wrong_unit", self.gap1_frac),
            ("gap2_coalescing", self.gap2_frac),
            ("gap3_avoidable_serial", self.gap3_frac),
            ("gap4_intra_unit_exec", self.gap4_frac),
        ]
        return max(gaps, key=lambda x: x[1])


@dataclass
class BoundResult:
    """Final bound output for a single kernel."""
    kernel_name: str
    t_bound_us: float

    # Decomposed
    t_grid_floor_us: float
    t_core_floor_us: float
    t_serial_irreducible_us: float

    binding_tier: BindingTier
    binding_component: Optional[Component] = None

    attribution: Attribution = field(default_factory=Attribution)

    def __repr__(self) -> str:
        return (f"BoundResult({self.kernel_name}: "
                f"T_bound={self.t_bound_us:.2f} us, "
                f"binding={self.binding_tier.value})")


def combine(
    grid: GridBound,
    component: ComponentBound,
    serial: SerializationSplit,
    kernel_name: str = "unknown",
) -> BoundResult:
    """Combine Tier 1 + Tier 2 + serialization into final bound.

    Args:
        grid: Tier 1 grid floor.
        component: Tier 2 component floor.
        serial: Mandatory/avoidable serialization split.
        kernel_name: Label for the result.

    Returns:
        BoundResult with T_bound, binding tier/component, and attribution.

    Raises:
        NotImplementedError: Combiner not yet implemented.
    """
    raise NotImplementedError(
        "Bound combiner not yet implemented. "
        "Requires M4 grid + component models first."
    )
