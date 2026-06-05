# M4 — Two Analytical Models (pure functions, no I/O, no compilation)
#
# Grid model (Tier 1):
#   T_grid_floor = T_total_work / (n_cores · occupancy · load_balance · I_binding)
#
# Component model (Tier 2):
#   I_c per component via weighted-harmonic mean (Eq. 4),
#   T_core_floor = max_c(O_c / I_c)
#
# Serialization split:
#   Classify each handoff as mandatory vs avoidable.
#   Mandatory → T_serial_irreducible.  Errs toward "avoidable"
#   to preserve bound soundness.
