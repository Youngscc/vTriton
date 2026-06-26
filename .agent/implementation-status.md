# Implementation Status

This document separates code existence from automated test coverage and
hardware/end-to-end validation. A feature listed as implemented is not
automatically considered hardware-validated.

## Status Matrix

| Area | Code status | Automated tests | Validation status | Evidence |
| --- | --- | --- | --- | --- |
| AscendModel dialect and pass registration | 已编码 | Test files under `test/`; CTest support is optional | Native build/smoke validation 待确认 for current checkout | `include/AscendModel/IR/`, `lib/AscendModel/IR/`, `include/AscendModel/Transforms/Passes.h`, `lib/AscendModel/Transforms/PassRegistration.cpp` |
| `tritonsim-opt` CLI | 已编码 | Build-dependent smoke inputs exist | Current local build validation 待确认 | `tools/tritonsim-opt/tritonsim-opt.cpp`, `tools/CMakeLists.txt`, `test/ascend_ops.mlir` |
| `tritonsim-hivm` CLI | 已编码 | HIVM sample inputs and pytest integration tests exist | Depends on build and optional HIVM/BiShengIR environment | `tools/tritonsim-hivm/tritonsim-hivm.cpp`, `test/hivm_add_kernel.npuir.mlir`, `tests/perfbound/test_hivm_cli_integration.py` |
| Hardware config schema and 910B/910B3 configs | 已编码 | Schema/config tests are not clearly centralized | Config semantics validated by users/tests only where consumed; broader validation 待确认 | `configs/hardware_schema.json`, `configs/ascend_910b.json`, `configs/ascend_910b3.json` |
| Calibration DB loader and dataclasses | 已编码 | 有 pytest 覆盖 | Hardware provenance is recorded in calibration/progress docs; reproducibility depends on bench data | `perfbound/calibration/constants.py`, `perfbound/calibration/calib_loader.py`, `tests/perfbound/test_calibration_load.py`, `tests/perfbound/test_calibration_wiring.py` |
| DSL/TTIR extraction | 已编码 | 有 pytest 覆盖 | Unsupported grid idioms remain possible | `perfbound/extract/dsl_extractor.py`, `perfbound/extract/mlir_parser.py`, `tests/perfbound/test_dsl_extractor.py`, `tests/perfbound/test_mlir_parser.py`, `tests/perfbound/test_grid_idioms.py` |
| HIVM DES graph extraction | 已编码 | 有 pytest 覆盖 | End-to-end emitter/loader compatibility depends on native build and DES schema stability | `perfbound/extract/hivm_extractor.py`, `lib/AscendModel/Analysis/HIVMAnalysis.cpp`, `tests/perfbound/test_hivm_extractor.py`, `tests/perfbound/test_stage_b_fixes.py` |
| Component/grid/serialization analytical models | 已编码 | 有 pytest 覆盖 | Mathematical behavior is unit-tested; hardware validation depends on separate validation harness | `perfbound/model/`, `tests/perfbound/test_component_model.py`, `tests/perfbound/test_grid_model.py`, `tests/perfbound/test_bounds.py`, `tests/perfbound/test_serialization.py` |
| Bound combiner and report model | 已编码 | 有 pytest 覆盖 | Hardware soundness/tightness validation is environment-dependent | `perfbound/combine/`, `tests/perfbound/test_combine.py`, `tests/perfbound/test_report.py`, `tests/perfbound/test_report_measured.py` |
| Validation harness and msprof parsing | 已编码 | 有 pytest 覆盖 | Real NPU/CANN/msprof validation is hardware-dependent | `perfbound/validate/`, `perfbound/validate/msprof_parser.py`, `tests/perfbound/test_validation_harness.py`, `tests/perfbound/test_msprof_parser.py`, `scripts/remote_bench.py` |
| Profile utilization analysis, including optional Scalar filtering | 已编码 | 有 pytest 覆盖 | Depends on quality and units of DES graph, `op_summary`, and calibration inputs; Scalar filtering preserves measured elapsed time | `perfbound/analyze/profile_utilization.py`, `tests/perfbound/test_profile_utilization.py` |
| HIVM bottleneck diagnosis | 已编码 | 有 pytest 覆盖 | Uses model/DES evidence; hardware truth comparison is separate | `perfbound/analyze/hivm_bottleneck_diagnosis.py`, `tests/perfbound/test_hivm_bottleneck_cpp_reference.py`, `tests/perfbound/test_calibration_wiring.py` |
| Shared analysis rate helpers | 已编码 | 间接覆盖 | Validation inherits callers' tests | `perfbound/analyze/rate_utils.py`, callers in `perfbound/analyze/` |
| Profile utilization demo and case selection | 已编码 | Script-level tests are not clearly separated; behavior is exercised by shell/docs workflows | UI/report output should be rechecked when schema changes | `scripts/demo_profile_utilization.py`, `scripts/run_profile_utilization_cases.sh`, `data/profile_utilization_inputs/README.md` |
| Component roofline / Tier 2 floor | 已编码 | 有 pytest 覆盖 | Unit contract with profile utilization is 待确认 where `flops` differs from `elements` | `perfbound/model/component_model.py`, `tests/perfbound/test_component_model.py`, `.agent/known-issues.md` |
| Native traditional Roofline report | 已编码 | Native FileCheck-style samples exist | Current native build/smoke validation 待确认 | `lib/AscendModel/Transforms/PerfReportPass.cpp`, `lib/AscendModel/Transforms/PipelineAnalysisPass.cpp`, `test/layernorm_ascend.mlir` |
| Ascend Profiling `op_summary` active-time parsing | 已编码 | 有 pytest 覆盖 | Real profiling correctness depends on msprof CSV schema compatibility | `perfbound/analyze/profile_utilization.py::_active_times_from_op_summary`, `perfbound/validate/msprof_parser.py`, `tests/perfbound/test_msprof_parser.py` |

## Environment-Dependent or Partial Areas

| Area | Current state | Evidence / notes |
| --- | --- | --- |
| Optional Triton integration | Environment-dependent | CMake detects `thirdparty/triton-ascend` and can add `thirdparty/triton-dialect`; see `CMakeLists.txt`. |
| Optional BiShengIR/HIVM typed ingestion | Environment-dependent | CMake searches for AscendNPU-IR/BiShengIR artifacts; some tests and tools require those artifacts. |
| Remote/hardware validation | Implemented as scripts and tests, but not always runnable locally | `scripts/remote_bench.py`, `tests/perfbound/test_remote_bench.py`, `PROGRESS.md`. |
| Counterfactual validation | Software edit/analysis path is implemented; live hardware delta remains environment-dependent | `perfbound/validate/counterfactual.py`, `perfbound/validate/hivm_edits.py`, `tests/perfbound/test_counterfactual.py`. |
| Real-data profile-utilization case | Data-dependent and currently not fully stabilized as tracked fixture | `data/profile_utilization_inputs/cases/real_data/` appears in the working tree but is untracked in the current status. |

## Not Implemented or 待确认

| Item | Evidence | Status |
| --- | --- | --- |
| ERU / REU / RSD metrics | No matching implementation or docs were found in scanned code/tests/docs | 待确认; implemented profile metrics are `A/I/U/R/E` |
| Ascend 910C config | `configs/README.md` lists `ascend_910c.json` as planned, but no such config file is present | Not implemented |
| Repository-wide Python type checking | No `pyproject.toml`, `mypy.ini`, or equivalent config found | 待确认 |
| Repository-wide CI matrix | No CI workflow was identified in the scanned files | 待确认 |
| Production release/package process | Not evident from scanned code/docs | 待确认 |
| Profile-utilization compute work unit contract | `profile_utilization.py` uses `elements`; `component_model.py` prefers `flops` then falls back to `elements` | 待确认; tracked in `.agent/known-issues.md` |

## HIVM / Ascend Profiling Coverage Snapshot

| Topic | Current behavior | Coverage status |
| --- | --- | --- |
| Kernel/operator/component relationship | One selected `op_summary` row represents the kernel/operator diagnosis; DES operations are aggregated into components. | Documented in `.agent/architecture.md` and `.agent/terminology.md`; diagnosis branches are covered by `tests/perfbound/test_profile_utilization.py`. |
| Theoretical baseline source | DES graph plus `CalibrationDB`; component floor uses sustained compute rates and memory bandwidth. | Covered by component-model and HIVM extractor tests; hardware validation is separate. |
| Actual data source | `op_summary` supplies `Task Duration(us)` and active-time counters. | Covered by profile-utilization/msprof-parser tests; real schema drift remains possible. |
| Missing fields / abnormal values | DES metadata reader emits warnings; `extract_hivm` rejects `schedule_truncated=true`; profile numeric cells default to `0.0`; utilization warnings flag negative/too-large active time and ratios above `1.05`. | Edge behavior has targeted tests in profile/HIVM suites; complete input-schema validation remains 待确认. |
| Roofline | C++ traditional roofline and Python component roofline are both present. | Python model has pytest coverage; native report validation depends on native build/FileCheck-style samples. |
| Profiling aggregation and diagnosis chain | `run_from_files -> extract_hivm -> compute_component_floor_from_db -> _component_stats_from_des_ops -> analyze_operator_bottleneck -> diagnose_hivm_bottleneck_from_des_ops`. | Documented in `.agent/architecture.md`; high-level diagnosis logic has pytest coverage. |

## Maintenance Notes

Update this file when a feature moves between "only coded", "covered by
automated tests", and "validated on real hardware/end-to-end data". Avoid
recording one-off local command results unless they are tied to a durable
release, CI run, or reproducible validation artifact.
