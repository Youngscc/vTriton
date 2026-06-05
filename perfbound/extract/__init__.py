# M2/M3 — DSL + HIVM Extractors
#
# M2 (DSL Extractor / Tier 1 input):
#   Parse Triton DSL / TTIR to recover program_id → tile affine map,
#   occupancy, load balance, redundancy(grid).  Hardware-legality
#   constraints (buffer capacity, register pressure, divisibility)
#   are first-class — illegal tilings are rejected.
#
# M3 (HIVM Extractor / Tier 2 input):
#   Consume C++-emitted structural JSON (emitDESGraph + dependency graph)
#   to extract per-component O_prec, transfer sizes, unit assignment,
#   and the handoff/barrier list.  Thin consumer — the heavy MLIR walking
#   is done in C++ HIVMAnalysis / PipelineAnalysis.
