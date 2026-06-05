# M4 — Mandatory vs Avoidable Serialization Split
#
# For each handoff between components, classify as:
#   mandatory — consumer needs producer's data AND producer/consumer are
#               on different components exchanging only via memory
#               (i.e. Cube↔Vector through GM/L2) → enters T_serial_irreducible
#   avoidable — could be eliminated by scheduling/ping-pong → Gap 3
#
# The split ERRS TOWARD "avoidable" — a non-mandatory handoff wrongly counted
# as mandatory would overstate T_bound and break the soundness guarantee.
#
# T_serial_irreducible = Σ min_cost(mandatory_handoffs)
#
# Source spec: .omc/specs/performance_bound_model.md §4.0, §A.4

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from ..extract.hivm_extractor import HandoffRecord
from ..extract.op_classifier import Component


@dataclass
class SerializationSplit:
    """Result of mandatory vs avoidable classification."""
    mandatory_handoffs: List[HandoffRecord] = field(default_factory=list)
    avoidable_handoffs: List[HandoffRecord] = field(default_factory=list)

    t_serial_irreducible_us: float = 0.0  # sum of mandatory min costs
    t_serial_avoidable_us: float = 0.0    # sum of avoidable costs (Gap 3 input)

    def __repr__(self) -> str:
        return (f"SerializationSplit(irreducible={self.t_serial_irreducible_us:.2f} us, "
                f"avoidable={self.t_serial_avoidable_us:.2f} us, "
                f"mandatory_count={len(self.mandatory_handoffs)}, "
                f"avoidable_count={len(self.avoidable_handoffs)})")


def classify_handoffs(
    handoffs: List[HandoffRecord],
    mandatory_handoff_cycles: float = 0.0,
    clock_ghz: float = 1.85,
) -> SerializationSplit:
    """Classify each handoff as mandatory or avoidable.

    A handoff is mandatory iff:
      1. The consumer component needs the producer's data (data dependency)
      2. The producer and consumer are on DIFFERENT components
      3. Those components exchange data ONLY via off-core memory (GM/L2)
         (i.e., no direct on-chip forwarding path exists)

    Cube↔Vector through GM is the canonical mandatory handoff.
    Cube→FixPipe and Vector→MTE3 are on the same path (avoidable).

    Args:
        handoffs: List of cross-component handoffs from HIVM extraction.
        mandatory_handoff_cycles: Measured minimum cycle cost for a single
                                  mandatory handoff (L0C→GM + GM→UB).
        clock_ghz: Core clock frequency.

    Returns:
        SerializationSplit with classified handoffs and T_serial_irreducible.

    Raises:
        NotImplementedError: Model not yet implemented.
    """
    raise NotImplementedError(
        "Serialization split not yet implemented. "
        "Requires M3 handoff extraction and M1 mandatory_handoff_cost."
    )
