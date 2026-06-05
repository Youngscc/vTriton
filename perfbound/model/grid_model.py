# M4 — Tier 1 Grid Analytical Model (pure function, no I/O)
#
# T_grid_floor = T_total_work / (n_cores · occupancy · load_balance · I_binding)
#
# Consumes M2 GridInfo + M1 CalibrationDB.
# bytes_in scaled by redundancy(grid) (=1 by default, conservative).
#
# Source spec: .omc/specs/performance_bound_model.md §1.4, §A.4

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..calibration.constants import CoreConfig
from ..extract.dsl_extractor import GridInfo


@dataclass
class GridBound:
    """Tier 1 bound output."""
    t_grid_floor_us: float       # lower bound from grid occupancy

    # Decomposed terms (for diagnostics)
    total_work: float             # aggregate work across all programs
    n_cores: int                  # cores used
    occupancy: float              # min(G, n_cores) / n_cores
    load_balance: float           # mean(work) / max(work)
    redundancy: float             # GM read amplification (≥1)
    i_binding: float              # HW throughput at binding component

    busiest_core_id: int          # core with max work (for Tier 2 analysis)

    def __repr__(self) -> str:
        return (f"GridBound(T_grid_floor={self.t_grid_floor_us:.2f} us, "
                f"occupancy={self.occupancy:.3f}, "
                f"load_balance={self.load_balance:.3f}, "
                f"i_binding={self.i_binding:.1f})")


def compute_grid_floor(
    grid: GridInfo,
    core: CoreConfig,
    i_binding: float,
) -> GridBound:
    """Compute T_grid_floor from Tier 1 grid information.

    Args:
        grid: M2-extracted grid quantities.
        core: Core topology (AIC/AIV counts, clock).
        i_binding: Hardware throughput at the binding component
                   (e.g., BW_gm_ub for memory-bound, P_cube for compute-bound).
                   Units: B/us or GFLOP/s — must match total_work units.

    Returns:
        GridBound with T_grid_floor and all decomposed terms.

    Raises:
        NotImplementedError: Model not yet implemented.
    """
    raise NotImplementedError(
        "Grid model not yet implemented. "
        "Requires M2 DSL extractor to produce GridInfo first."
    )
