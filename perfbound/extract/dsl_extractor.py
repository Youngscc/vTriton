"""
M2 — DSL Extractor / Tier 1 input.

Parse the @triton.jit function + launch grid + shape → Tier-1 quantities:
  G, tile_assignment[p], occupancy, work[p], load_balance, redundancy.

Method: recover the affine map from tl.program_id → tile via TTIR
(tt.get_program_id, tt.load pointer arithmetic) using symbolic execution.
Common idioms as templates first (grid_idioms.py), general affine recovery second.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class GridInfo:
    """Tier 1 grid-level quantities for the bound model."""
    # Launch grid dimensions
    grid_dims: Tuple[int, ...]          # (G_x, G_y, G_z) from launch
    total_programs: int                 # G = product(grid_dims)

    # Per-program tile assignment: program_id → (tile_m, tile_n, ...)
    tile_assignment: Dict[int, Tuple[int, ...]]

    # Per-program work amount (e.g., elements computed)
    work: Dict[int, float]

    # Derived quantities
    occupancy: float                    # min(G, n_cores) / n_cores
    load_balance: float                 # mean(work) / max(work)
    redundancy: float = 1.0            # GM read amplification (default 1)

    # Busiest core (largest work)
    busiest_core_id: int = 0

    # Hardware-legality constraints (from configs/ascend_910b3.json)
    buffer_pressure_ok: bool = True
    divisibility_ok: bool = True

    @property
    def is_valid(self) -> bool:
        return self.buffer_pressure_ok and self.divisibility_ok


def extract_grid_info(
    kernel_source: str,
    launch_grid: Tuple[int, ...],
    problem_shape: Tuple[int, ...],
    block_sizes: Dict[str, int],
    n_cores: int = 20,
) -> GridInfo:
    """Extract Tier 1 grid information from a Triton kernel.

    Args:
        kernel_source: Triton kernel source code or TTIR dump path.
        launch_grid: Launch grid dimensions (G_x, G_y, G_z).
        problem_shape: Problem dimensions (M, N, K, ...).
        block_sizes: Block/tile sizes {BLOCK_M: 128, BLOCK_N: 64, ...}.
        n_cores: Number of available cores (20 for Cube, 40 for Vector-only).

    Returns:
        GridInfo with all Tier 1 quantities.

    Raises:
        NotImplementedError: For grid idioms not yet supported.
    """
    # TODO: Implement TTIR parsing via idioms
    # Phase 1: template matching (1D row-block, 2D tile, persistent/grouped)
    # Phase 2: general affine recovery via symbolic execution
    raise NotImplementedError(
        "DSL extractor not yet implemented. "
        "Phase 1: implement grid_idioms.py templates."
    )
