# M4 — Tier 2 Component Analytical Model (pure functions, no I/O)
#
# For each roofline component c, compute the ideal rate I_c via
# weighted-harmonic mean (Eq. 4):
#
#   I_c = Σ O_prec[c][p] / Σ (O_prec[c][p] / P_prec[p])
#
# Then the core floor:
#   T_core_floor = max_c(O_c / I_c)
#
# where O_c = total work (ops or bytes) for component c.
#
# Source spec: .omc/specs/performance_bound_model.md §1.4, §2.1, §A.4
# Ports: tilesim aicore_costmodel.py time_cube structure (not values).

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from ..calibration.constants import CubeConfig, VectorConfig, MemHierarchy, DType
from ..extract.hivm_extractor import HIVMExtract
from ..extract.op_classifier import Component, Precision


@dataclass
class ComponentRate:
    """Ideal rate I_c for a single component at a single precision."""
    component: Component
    precision: Precision
    i_c: float                  # ideal throughput (ops/us or bytes/us)
    o_c: float                  # total work for this component+precision
    t_c_floor: float           # O_c / I_c (microseconds)


@dataclass
class ComponentBound:
    """Tier 2 bound output."""
    t_core_floor_us: float      # max_c(O_c / I_c)
    binding_component: Component  # component that sets the floor

    # Per-component rates
    rates: Dict[str, ComponentRate] = field(default_factory=dict)

    # Per-component totals
    total_ops: Dict[str, float] = field(default_factory=dict)
    total_bytes: Dict[str, float] = field(default_factory=dict)

    def __repr__(self) -> str:
        return (f"ComponentBound(T_core_floor={self.t_core_floor_us:.2f} us, "
                f"binding={self.binding_component.value})")


def compute_component_floor(
    extract: HIVMExtract,
    cube: CubeConfig,
    vector: VectorConfig,
    memory: MemHierarchy,
    core_clock_ghz: float = 1.85,
) -> ComponentBound:
    """Compute T_core_floor from Tier 2 HIVM extraction.

    Args:
        extract: M3 HIVM extract output (per-component O_prec, handoffs).
        cube: Sustained Cube throughput calibration.
        vector: Sustained Vector throughput calibration.
        memory: Memory hierarchy with sustained bandwidths.
        core_clock_ghz: Core clock frequency (1.85 GHz default).

    Returns:
        ComponentBound with T_core_floor and per-component rates.

    Raises:
        NotImplementedError: Model not yet implemented.
    """
    raise NotImplementedError(
        "Component model not yet implemented. "
        "Requires M3 HIVM extractor to produce HIVMExtract first."
    )
