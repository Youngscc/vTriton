# Design Decisions

This file records durable decisions that can be confirmed from code, docs, or Git history. It follows an ADR-like style.

## ADR-001: Use MLIR/C++ for native AscendModel and HIVM analysis

- Status: 已采用
- Background: The repository implements dialects, passes, and CLI tools around LLVM/MLIR.
- Decision: Native analysis and pass pipelines are implemented in C++17 using MLIR/LLVM infrastructure.
- Reason: Existing code registers MLIR dialects/passes and uses `MlirOptMain`, `add_mlir_library`, and LLVM command-line tooling.
- Impact: Builds require LLVM/MLIR CMake packages; code changes often require native rebuilds.
- Related code: `CMakeLists.txt`, `tools/tritonsim-opt/tritonsim-opt.cpp`, `include/AscendModel/`, `lib/AscendModel/`.

## ADR-002: Keep analytical Python model separate from native MLIR code

- Status: 已采用
- Background: `perfbound/` modules are organized as calibration, extraction, model, combine, validate, and analyze layers.
- Decision: Python `perfbound/` consumes structured JSON/CSV and calibration data rather than embedding MLIR traversal.
- Reason: Module comments state pure model functions have no I/O and C++ emits DES graphs for Python consumers.
- Impact: JSON schema stability between C++ emitters and Python loaders is important.
- Related code: `perfbound/__init__.py`, `perfbound/extract/hivm_extractor.py`, `perfbound/model/`, `perfbound/combine/`.

## ADR-003: Use C++ DES graph JSON as preferred HIVM extraction path

- Status: 已采用
- Background: `perfbound/extract/hivm_extractor.py` states it consumes C++-emitted structural JSON and only falls back to MLIR walking if needed.
- Decision: DES graph JSON from `HIVMAnalysis::emitDESGraph()` is the preferred bridge from native HIVM analysis to Python models.
- Reason: Keeps heavy MLIR walking in C++ and keeps Python extraction thin.
- Impact: Required fields and schema changes must update loaders, tests, and docs.
- Related code: `perfbound/extract/hivm_extractor.py`, `lib/AscendModel/Analysis/HIVMAnalysis.cpp`, `docs/perfbound/profile_utilization/input_sources.md`.

## ADR-004: Bound composition uses `max(grid, core + serial)`

- Status: 已采用
- Background: `perfbound/combine/bound_combiner.py` explicitly documents a spec divergence.
- Decision: Implement `T_bound = max(T_grid_floor, T_core_floor + T_serial_irreducible)` rather than `max(T_grid_floor, T_core_floor) + T_serial_irreducible`.
- Reason: Code comments state the additive form can be unsound because it may overstate a lower bound.
- Impact: Any paper/spec formulas should be reconciled with implemented sound composition.
- Related code: `perfbound/combine/bound_combiner.py`.

## ADR-005: Calibration uses sustained measured constants with provenance

- Status: 已采用
- Background: Calibration module comments and tests emphasize measured sustained rates, confidence intervals, and source metadata.
- Decision: `CalibrationDB` is the source of truth for Python model rates; fake calibration files are explicitly marked fake.
- Reason: Analytical lower bounds depend on sustained rates rather than datasheet peaks.
- Impact: Calibration changes require provenance and tests.
- Related code: `perfbound/calibration/constants.py`, `perfbound/calibration/calib_loader.py`, `perfbound/calibration/data/calib_910b3_v1.json`, `tests/perfbound/test_calibration_load.py`.

## ADR-006: Profile utilization returns analysis objects; JSON/UI live in demo layer

- Status: 已采用
- Background: Current code structure has `profile_utilization.py` returning `OperatorBottleneckReport` and `scripts/demo_profile_utilization.py` doing JSON conversion and UI printing.
- Decision: Keep core profile analysis free of CLI/UI/report-file writing.
- Reason: Separates analysis logic from human-facing presentation and makes tests focus on structured objects.
- Impact: Consumers that need JSON use demo-layer helpers or their own serialization.
- Related code: `perfbound/analyze/profile_utilization.py`, `scripts/demo_profile_utilization.py`, `docs/perfbound/profile_utilization/run_profile_utilization.md`.

## ADR-007: Demo runs one selected case via `ACTIVE_CASE`

- Status: 已采用
- Background: The demo keeps fake cases and real data but executes one data source at a time.
- Decision: `scripts/demo_profile_utilization.py` selects a single case through `ACTIVE_CASE`.
- Reason: Keeps UI output concise while preserving all data sources in the case table.
- Impact: Users switch case by editing `ACTIVE_CASE`; batch refresh remains in `scripts/run_profile_utilization_cases.sh`.
- Related code: `scripts/demo_profile_utilization.py`, `data/profile_utilization_inputs/README.md`.

## ADR-008: Optional Triton and BiShengIR integrations are auto-detected

- Status: 已采用
- Background: CMake searches for Triton headers and BiShengIR headers/libs/objects.
- Decision: Build with optional Triton/BiShengIR support when local artifacts exist; otherwise proceed with reduced support where possible.
- Reason: Keeps core project buildable in more environments while enabling richer workflows on configured hosts.
- Impact: Some tools/tests/features are environment-dependent.
- Related code: `CMakeLists.txt`, `tools/CMakeLists.txt`, `docs/DEPLOYMENT_GUIDE.md`.

## ADR-009: Use structured source-to-source HIVM JSON edits for counterfactuals

- Status: 已采用
- Background: `perfbound/validate/hivm_edits.py` states edits are structured JSON edits, not regex.
- Decision: Counterfactual validation edits operate on loaded HIVM JSON and write temp files instead of mutating inputs in place.
- Reason: Reduces fragility and protects original artifacts.
- Impact: Future edit primitives should follow the same structured approach.
- Related code: `perfbound/validate/hivm_edits.py`, `perfbound/validate/counterfactual.py`.

## ADR-010: Use shared analysis rate helpers

- Status: 已采用
- Background: `profile_utilization.py` and `hivm_bottleneck_diagnosis.py` had duplicate cube/vector peak-rate helper logic.
- Decision: Shared helpers live in `perfbound/analyze/rate_utils.py`.
- Reason: Avoids drift in calibration-rate conversion while preserving the existing unknown-label behavior through an option.
- Impact: Future analysis modules should reuse `rate_utils.py`.
- Related code: `perfbound/analyze/rate_utils.py`, `perfbound/analyze/profile_utilization.py`, `perfbound/analyze/hivm_bottleneck_diagnosis.py`.
