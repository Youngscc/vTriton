# Project Context

## Background
TritonSim/vTriton is an Ascend NPU performance modeling project.  The root `README.md` describes it as an MLIR-based Ascend NPU performance modeling tool.  The repository combines:

- C++ MLIR dialect/pass tooling under `include/AscendModel/`, `lib/AscendModel/`, and `tools/`.
- Python analytical performance-bound and profiling-analysis code under `perfbound/`.
- Hardware configuration, calibration, profiling, and DES graph data under `configs/`, `perfbound/calibration/data/`, and `data/`.

The project also carries design specifications and planning material in `.omc/specs/` and `.omc/plans/`.

## Problem Being Solved
The codebase addresses performance diagnosis for Triton/Ascend workloads at two levels:

- MLIR/HIVM structural analysis: parse AscendModel MLIR or HIVM/NPUIR, schedule operations, estimate cycles, emit reports/traces/DES graphs.
- Analytical performance-bound diagnosis: combine grid-level, component-level, serialization, calibration, and profiling evidence to explain observed performance gaps.

For the `profile_utilization` workflow, the immediate question is: given real profiling active-time data, a DES graph, and calibration rates, determine whether a kernel is compute-bound, MTE-bound, inefficient, or limited by parallelism/synchronization.

## Inputs
Confirmed input types include:

- AscendModel MLIR files, e.g. `test/ascend_ops.mlir`.
- HIVM/NPUIR MLIR files, e.g. `test/hivm_add_kernel.npuir.mlir`.
- Triton DSL Python scripts for compile-only dump workflows, e.g. `test/triton_smoke.py` and `tools/common/triton_dsl_dump_launcher.py`.
- TTIR files, e.g. `test/*.ttir`.
- Hardware config JSON files under `configs/`, validated by `configs/hardware_schema.json`.
- Calibration JSON/CSV data under `perfbound/calibration/data/`.
- DES graph JSON from C++ HIVM analysis, consumed by `perfbound/extract/hivm_extractor.py`.
- msprof/op_summary CSV data consumed by `perfbound/validate/msprof_parser.py` and `perfbound/analyze/profile_utilization.py`.

## Outputs
Confirmed outputs include:

- MLIR pass output from `tritonsim-opt`.
- HIVM textual reports, DES graph JSON, dependency graph JSON, and optional Perfetto trace JSON from C++ analysis passes and `tritonsim-hivm`.
- Python `BoundResult` / `KernelReport` objects and text/JSON reports from `perfbound/combine/`.
- `OperatorBottleneckReport` objects from `perfbound/analyze/profile_utilization.py`.
- Demo JSON reports and console summaries from `scripts/demo_profile_utilization.py`.

## Main Users and Use Cases
Confirmed or strongly evidenced users/use cases:

- Developers of AscendModel MLIR passes and HIVM analysis.
- Performance-model developers validating analytical lower bounds and attribution logic.
- Researchers preparing paper/experiment evidence from `.omc/specs/`, `.omc/plans/`, and `PROGRESS.md`.
- Users running local or remote Ascend profiling workflows through scripts such as `scripts/remote_bench.py`.

待确认:

- Whether this repository is intended for production compiler users, research-only use, or both.
- The exact external release process and CI requirements.

## Project Boundaries
In scope:

- Ascend NPU performance modeling, scheduling analysis, and bottleneck diagnosis.
- Triton/Triton-Ascend/TTIR ingestion when optional dependencies are available.
- HIVM/NPUIR analysis and DES graph export.
- Calibration-backed analytical bounds and validation harnesses.

Out of scope or not confirmed:

- General-purpose kernel optimization beyond modeled recommendations is 待确认.
- Full hardware execution is not performed by core model modules; execution/profiling belongs to validation scripts and remote/hardware-dependent workflows.
- Compatibility with non-Ascend accelerators is 待确认.

## Current Stage
`PROGRESS.md` records the Python `perfbound/` plan as A.0-A.8 plus Part B. It reports A.0-A.7 as complete, A.8 as mostly done, and Part B as not started. It also records real 910B3 evidence for `chunk_kda` and remaining gaps around offline DES extraction and live counterfactual delta.

Because `PROGRESS.md` is a project progress log and not automatically verified by this document, any status claim not backed by tests or current code should be treated as "reported by PROGRESS.md".

## External Dependencies
Confirmed dependencies:

- LLVM/MLIR via CMake `find_package(MLIR)` and `find_package(LLVM)`.
- Optional Triton dialect sources from `thirdparty/triton-ascend`.
- Optional BiShengIR/HIVM/HACC/Annotation dialect artifacts from AscendNPU-IR.
- CMake, Ninja, C++17 compiler, Python.
- Python packages listed in `scripts/requirements.txt`.
- CANN/Ascend runtime for Triton DSL and hardware validation workflows.

## Relationship to Papers, Specs, and External Systems
The Python modules and comments reference `.omc/specs/performance_bound_model.md`, `.omc/specs/implementation_and_paper_plan.md`, and plans under `.omc/plans/`. Several modules explicitly state stage labels M1-M6 and A.1-A.8. `docs/perfbound/profile_utilization/` contains report/presentation material for the profile utilization workflow.

External systems referenced by code or docs:

- Triton-Ascend and AscendNPU-IR.
- CANN / torch-npu workflows.
- msprof profiling CSVs.
- Perfetto trace viewer for trace JSON.
- Remote 910B3 hardware workflow, evidenced by `PROGRESS.md` and scripts, but hardware availability is environment-dependent.

