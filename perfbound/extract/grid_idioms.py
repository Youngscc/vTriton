"""
M2 — Grid idiom templates for common Triton kernel patterns.

Each idiom is a function that, given problem_shape + block_sizes,
computes tile_assignment, work[], and validates hardware-legality constraints.

Supported idioms (Phase 1):
  - 1D row-block: program_id(0) → row tiles (common in reduction, softmax)
  - 2D tile grid: program_id(0,1) → (tile_m, tile_n) (matmul, flash-attn)
  - Persistent/grouped: program_id(0) → dynamic work queue

Phase 2: general affine recovery via symbolic execution of TTIR.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class TileIdiomResult:
    """Output from an idiom template."""
    tile_assignment: Dict[int, Tuple[int, ...]]
    work: Dict[int, float]
    buffer_pressure_ok: bool = True
    divisibility_ok: bool = True


def idiom_1d_row_block(
    M: int,
    BLOCK_M: int,
    ub_limit_bytes: int = 256 * 1024,   # UB capacity
    l1_limit_bytes: int = 1 * 1024 * 1024,  # L1 capacity
    elem_bytes: int = 2,                  # fp16
) -> TileIdiomResult:
    """1D row-block idiom: program_id(0) partitions M into BLOCK_M tiles.

    Grid: (ceil(M / BLOCK_M),)
    Each program handles BLOCK_M rows.
    """
    import math
    G = math.ceil(M / BLOCK_M)
    tile_assignment = {}
    work = {}
    for p in range(G):
        rows = min(BLOCK_M, M - p * BLOCK_M)
        tile_assignment[p] = (p * BLOCK_M,)
        work[p] = rows

    # Hardware-legality: check UB can hold one block
    buffer_ok = BLOCK_M * elem_bytes <= ub_limit_bytes
    div_ok = True  # 1D has no divisibility constraint beyond BLOCK_M > 0

    return TileIdiomResult(
        tile_assignment=tile_assignment,
        work=work,
        buffer_pressure_ok=buffer_ok,
        divisibility_ok=div_ok,
    )


def idiom_2d_tile_grid(
    M: int, N: int,
    BLOCK_M: int, BLOCK_N: int,
    ub_limit_bytes: int = 256 * 1024,
    l1_limit_bytes: int = 1 * 1024 * 1024,
    elem_bytes: int = 2,
) -> TileIdiomResult:
    """2D tile grid idiom: program_id(0,1) → (tile_m, tile_n).

    Grid: (ceil(M/BLOCK_M), ceil(N/BLOCK_N))
    Standard for matmul, flash-attention output loop.
    """
    import math
    G_m = math.ceil(M / BLOCK_M)
    G_n = math.ceil(N / BLOCK_N)
    G = G_m * G_n

    tile_assignment = {}
    work = {}
    for p in range(G):
        tile_m = p // G_n
        tile_n = p % G_n
        rows = min(BLOCK_M, M - tile_m * BLOCK_M)
        cols = min(BLOCK_N, N - tile_n * BLOCK_N)
        tile_assignment[p] = (tile_m * BLOCK_M, tile_n * BLOCK_N)
        work[p] = rows * cols

    # Hardware-legality
    buffer_ok = (BLOCK_M * BLOCK_N * elem_bytes <= ub_limit_bytes and
                 BLOCK_M * elem_bytes <= l1_limit_bytes)
    div_ok = True

    return TileIdiomResult(
        tile_assignment=tile_assignment,
        work=work,
        buffer_pressure_ok=buffer_ok,
        divisibility_ok=div_ok,
    )


# Registry of idioms for template matching
IDIOM_REGISTRY = {
    "1d_row_block": idiom_1d_row_block,
    "2d_tile_grid": idiom_2d_tile_grid,
    # Phase 1 additions: persistent, grouped, batched
}
