# Known Issues and Risks

## Confirmed TODO/FIXME or Incomplete Implementations

| Issue | Evidence | Impact | Status |
| --- | --- | --- | --- |
| `MemoryTilingOptimizer.cpp` has TODO for other op types | `lib/AscendModel/Analysis/MemoryTilingOptimizer.cpp` contains `TODO: Handle other op types` | Tiling optimizer may not cover all operations | Open |
| `ConvertTritonToAscend.cpp` creates placeholder tensor sources | Comments and code around placeholder tensor source creation | Conversion may use placeholders where full source modeling is incomplete | Open / 待确认 impact |
| Triton-Ascend patch contains upstream TODO about CANN API | `patches/triton-ascend-compile-only-mock.patch` | Patch maintenance risk when upstream changes | Open |
| `dsl_extractor.py` raises `NotImplementedError` for unsupported grid idioms | Search result in `perfbound/extract/dsl_extractor.py` | General affine recovery may not cover every Triton kernel | Open |

## Environment and Configuration Risks

| Issue | Evidence | Impact | Status |
| --- | --- | --- | --- |
| Optional Triton support depends on local `thirdparty/triton-ascend` headers | `CMakeLists.txt` auto-detects Triton headers | TTIR/Triton workflows disabled if headers absent | Known |
| Optional BiShengIR HIVM support depends on local AscendNPU-IR build artifacts | `CMakeLists.txt` searches for BiShengIR headers/libs/objects | HIVM typed ingestion and some tools may be disabled | Known |
| Native build docs mention multiple LLVM/CMake/BiShengIR layouts | `README.md`, `BUILD.md`, `docs/DEPLOYMENT_GUIDE.md` | Environment setup can diverge across machines | Known |
| `scripts/requirements.txt` pins `torch==2.7.1+cpu` and `torch-npu==2.7.1` | Requirements file | Dependency resolution may require specific indexes or local wheels; installation process is 待确认 | Open |
| Remote/hardware tests depend on NPU/CANN/msprof availability | `PROGRESS.md`, `perfbound/validate/`, `scripts/remote_bench.py` | Cannot be fully validated on a generic local machine | Known |

## Data and Units Risks

| Issue | Evidence | Impact | Status |
| --- | --- | --- | --- |
| Fake calibration/demo data is present beside real data | `data/profile_utilization_inputs/README.md`, fake JSON descriptions | Risk of drawing conclusions from synthetic data | Mitigated by docs, still requires care |
| `data/profile_utilization_inputs/cases/real_data/` is currently untracked | `git status --short` | Long-term availability of real-data fixture is 待确认 | Open |
| MTE and compute units differ | Code uses bytes for MTE and ops/elements/FLOPs for compute | Unit mismatch can corrupt bound/utilization results | Known, tests cover many paths |
| profile_utilization uses DES work plus op_summary active time | `profile_utilization.py`, profile docs | DES model time must not be confused with profiling elapsed time | Known |
| Compute work unit differs between component model and profile utilization | `perfbound/model/component_model.py::compute_component_floor` uses `op.flops` when positive, otherwise `op.elements`; `perfbound/analyze/profile_utilization.py::_component_stats_from_des_ops` uses `op.elements * loop_multiplier` for compute components | Theoretical `component_bound` and profile `work_done` can disagree when DES contains non-zero `flops` different from `elements`; warnings may appear as `profiling work 和理论 bound work 相差 ...` and U/E may use a mixed unit contract | Open / 待确认 intended formula |
| Existing profile-utilization input-source doc says DES has no `flops`, but extractor/code now supports `flops` | `docs/perfbound/profile_utilization/input_sources.md` says current DES JSON lacks `flops`; `perfbound/extract/hivm_extractor.py::load_hivm_desgraph` reads `node.get("flops", 0)` and comments that C++ emits flops for compute ops | Documentation may be stale for current emitter; human needs to decide whether profile docs should state `flops` as available or optional | Open / 待确认 current DES emitter contract |

## Formula and Documentation Differences to Review

| Difference | Related files / functions / formulas | Current implementation behavior | Impact | Status |
| --- | --- | --- | --- | --- |
| `T_bound` formula differs from written spec sections cited in code | `perfbound/combine/bound_combiner.py`; code cites `.omc/specs/performance_bound_model.md §4.1, §7` as `max(T_grid_floor, T_core_floor) + T_serial_irreducible` | Implementation uses `max(T_grid_floor, T_core_floor + T_serial_irreducible)` and comments that the divergence is intentional for lower-bound soundness | Readers comparing implementation to paper/spec may see a mismatch; no algorithm change should be made without design review | Open / design adopted in code, spec update 待确认 |
| ERU / REU / RSD requested metrics are not defined in scanned implementation | Repository search across code/docs/tests did not find `ERU`, `REU`, or `RSD`; implemented profile metrics are `A`, `I`, `U`, `R`, and `E` in `perfbound/analyze/profile_utilization.py::compute_realized_utilization` | No ERU/REU/RSD values are emitted by current report unless they are represented under different names | Presentation or paper text using ERU/REU/RSD needs a mapping to current `A/I/U/R/E` or new implementation | Open / 待确认 formula source |
| `profile_utilization` operator-aware compute work formula may differ from component model formula | `profile_utilization.py::_component_stats_from_des_ops`; `component_model.py::compute_component_floor`; profile docs formula currently describes compute work as `elements * loop_multiplier` | Profile utilization builds breakdown and actual work from elements, while component floor may use FLOPs | Component U/E may be hard to interpret for matmul where FLOPs != output elements | Open / 待确认 |
| `parse_kernel_time_us` matching description and code may differ | `perfbound/validate/msprof_parser.py::parse_kernel_time_us` doc/comment mentions exact normalized matching, while implementation uses substring containment for `op_name_filter` | A broader set of rows can match a filter than the text suggests | Validation can select unintended kernels when names overlap | Open |
| C++ traditional Roofline and Python Component Roofline report different concepts | `lib/AscendModel/Transforms/PerfReportPass.cpp`; `perfbound/model/component_model.py`; `perfbound/analyze/profile_utilization.py` | C++ pass computes arithmetic intensity, ridge point, achieved TFLOPS/GB/s, and compute/memory bound label; Python component model computes per-component lower-bound floors and profile utilization computes `A/I/U/R/E` | Reports may look inconsistent if users expect one roofline definition; docs now distinguish them | Known / documentation added |

## Potential Inconsistencies

| Issue | Evidence | Impact | Status |
| --- | --- | --- | --- |
| `README.md`, `BUILD.md`, and `docs/DEPLOYMENT_GUIDE.md` document different build environments/versions | Files list different LLVM/CMake/CANN contexts | New users may not know which path fits their machine | Open; document local choice before bootstrapping |
| `PROGRESS.md` contains historical and current sections that may conflict over status labels | Same file has "Current State" plus later historical milestone text | Readers may confuse old milestone text with current status | Open; prefer `docs/implementation-status.md` for maintained summary |
| `configs/README.md` lists Ascend 910C as planned, but no `ascend_910c.json` was found | `configs/README.md`, file scan | Planned support should not be treated as implemented | Open |
| `include/AscendModel/HardewareConfig.h` appears misspelled next to `HardwareConfig.h` | File scan | Could confuse include usage; actual role is 待确认 | Open |

## Missing or Unconfirmed Tests

| Area | Evidence | Status |
| --- | --- | --- |
| Repository-wide C++ build and CLI smoke checks | No maintained validation artifact is recorded in these docs for the current checkout | 待确认 |
| Full `tests/perfbound` suite for the current codebase state | No maintained validation artifact is recorded in these docs for a complete latest test run | 待确认 |
| Hardware validation on current machine | Requires NPU/CANN/remote setup | 待确认 |
| Type checking/static analysis | No config found | 待确认 |

## Reproduction Pointers

- Profile utilization targeted test: `PYTHONPATH=. pytest tests/perfbound/test_profile_utilization.py`
- HIVM/calibration targeted tests: `PYTHONPATH=. pytest tests/perfbound/test_hivm_bottleneck_cpp_reference.py tests/perfbound/test_calibration_wiring.py`
- Native smoke checks after build:
  - `./build/bin/tritonsim-opt test/ascend_ops.mlir -ascend-perf-model`
  - `./build/bin/tritonsim-hivm --npuir-file test/hivm_add_kernel.npuir.mlir`
