# Repository Guidelines

## Project Goal
TritonSim/vTriton is an MLIR-based Ascend NPU performance modeling and bottleneck analysis project.  The repository contains:

- C++ MLIR dialects, passes, and CLI tools for AscendModel and HIVM analysis.
- Python `perfbound/` modules for calibration, extraction, analytical bounds, validation, and profiling-utilization diagnosis.
- Hardware configs, benchmark fixtures, profiling/demo inputs, and calibration data used by analysis workflows.

Keep project documentation grounded in repository code, configs, tests, and tracked design notes. Mark uncertain facts as `待确认`.

## Technical Stack
- C++17 with LLVM/MLIR pass infrastructure.
- CMake and Ninja for native builds.
- Optional Triton dialect integration from `thirdparty/triton-ascend`.
- Optional BiShengIR/HIVM integration from AscendNPU-IR artifacts.
- Python 3 for `perfbound/`, scripts, tests, and demo/report utilities.
- Pytest for Python tests.
- JSON/CSV inputs for hardware config, calibration, DES graphs, op summaries, and reports.

## Project Structure
- `include/AscendModel/`: public C++ headers for IR, transforms, and analysis.
- `lib/AscendModel/`: C++ implementations for the AscendModel dialect, analysis, and passes.
- `tools/`: CLI entrypoints such as `tritonsim-opt`, `tritonsim-hivm`, optional `hivm-crud`, and optional `ascend-tiling-opt`.
- `configs/`: hardware configuration JSON files and schema.
- `perfbound/`: Python performance-bound and profiling-analysis package.
- `scripts/`: build helpers, remote benchmark helpers, and demo scripts.
- `test/`: MLIR/Triton smoke inputs and benchmark scripts.
- `tests/`: pytest-based validation suite.
- `data/`: profiling/demo input data, sample CSV/JSON artifacts, and generated example reports.
- `docs/`: human-facing project documentation. Topic-specific documents may live under subdirectories such as `docs/perfbound/profile_utilization/`.
- `.agent/`: AI/agent-facing project context, architecture notes, terminology, decisions, known issues, and implementation status.
- `.omc/`: project specs, plans, progress logs, and paper/model design notes.
- `thirdparty/`: vendored upstream dependencies; treat as external unless a task explicitly targets them.

## Build, Run, and Test Commands
Initialize submodules before first native build:

```bash
git submodule update --init --recursive
./scripts/build_llvm.sh
mkdir -p build && cd build
cmake -G Ninja .. -DMLIR_DIR=$LLVM_INSTALL_PREFIX/lib/cmake/mlir -DLLVM_DIR=$LLVM_INSTALL_PREFIX/lib/cmake/llvm
ninja
```

Common native checks:

```bash
./build/bin/tritonsim-opt test/ascend_ops.mlir -ascend-perf-model
./build/bin/tritonsim-hivm --npuir-file test/hivm_add_kernel.npuir.mlir
python3 test/triton_smoke.py
```

Python checks used by the `perfbound/` stack:

```bash
PYTHONPATH=. pytest tests/perfbound
PYTHONPATH=. pytest tests/perfbound/test_profile_utilization.py
python3 -m py_compile perfbound/analyze/profile_utilization.py scripts/demo_profile_utilization.py
```

Enable CTest integration only when needed:

```bash
cmake -G Ninja .. -DASCEND_MODEL_ENABLE_TESTS=ON ...
ctest --test-dir build
```

## Local Environment
Prefer the machine-local setup documented in `LOCAL_ENVIRONMENT.md` before attempting a fresh dependency bootstrap. If that file is missing, first search for an existing Python environment and CANN/Ascend install documented elsewhere in the repository or local machine notes. Only build LLVM/CANN-related dependencies from scratch when local installs are unavailable or known incompatible.

## Code Style and Naming
- Follow the existing LLVM/MLIR-oriented C++17 style in `lib/` and `tools/`.
- Use 2-space indentation for wrapped C++ arguments.
- Use braces on their own lines for C++ functions, matching existing files.
- Keep includes grouped: LLVM/MLIR/project headers before STL headers where existing files do so.
- Use `CamelCase` for C++ types and passes, `lowerCamelCase` for C++ functions and locals.
- Use descriptive filenames such as `HIVMAnalysis.cpp`, `PipelineAnalysisPass.cpp`, or `profile_utilization.py`.
- For Python, prefer dataclasses and explicit structured objects when the code already uses them. Do not replace tested dataclasses with loose dictionaries unless there is a strong reason.
- Keep generated or temporary artifacts out of source unless they are intentional fixtures.

## Type Checking and Static Checks
- No repository-wide Python type checker configuration is currently present. Treat type-checking requirements beyond normal Python syntax and pytest as `待确认`.
- C++ static analysis beyond compiler warnings and MLIR/LLVM build checks is `待确认`.
- Always run at least syntax/compile checks for files touched:
  - Python: `python3 -m py_compile ...`
  - C++: rebuild the affected CMake target when feasible.

## Testing Requirements
- Prefer adding or updating focused tests under `tests/` or `test/` whenever changing analysis logic, pass behavior, hardware modeling, data parsing, or report formats.
- For `perfbound/`, run the narrow pytest file first, then broader related tests when shared modules change.
- If a change affects Triton ingestion or MLIR pass behavior, run both an MLIR sample and `python3 test/triton_smoke.py` when the local environment supports it.
- If a change affects profile utilization, run `tests/perfbound/test_profile_utilization.py` and update `docs/perfbound/profile_utilization/` when behavior changes.
- Tests that require real NPU hardware, remote hosts, CANN, or BiShengIR artifacts may be hardware-gated; document such limitations instead of silently claiming validation.

## Files to Avoid or Modify Carefully
- `thirdparty/`: upstream/vendor code; modify only when explicitly requested.
- `patches/`: patches applied to upstream dependencies; changes require clear rationale and revalidation.
- `perfbound/calibration/data/*.json` and `perfbound/calibration/data/*.csv`: calibration truth sources; do not change values without provenance and tests.
- `configs/*.json` and `configs/hardware_schema.json`: hardware config/schema; update docs and tests if semantics change.
- `data/profile_utilization_inputs/cases/real_data/`: real profiling/DES sample data; avoid overwriting unintentionally.
- Generated reports under `data/profile_utilization_inputs/` should only be refreshed intentionally and should match the current report schema.
- `.omc/specs/` and `.omc/plans/`: design/spec sources; do not rewrite casually.

## Data Formats and Units
- `op_summary` timings are in microseconds (`us`), including `Task Duration(us)` and component active-time columns.
- DES/HIVM durations and schedules are in cycles unless explicitly converted.
- Calibration compute rates are expressed as sustained rates; code converts TFLOPS to ops/us by multiplying by `1e6`.
- Memory bandwidth lookup returns bytes/us in the Python `perfbound` model.
- Compute work and MTE work must not be mixed: compute uses ops/FLOPs/elements as defined by the consuming module, MTE uses bytes.
- `profile_utilization.py` currently returns analysis objects; JSON serialization and UI printing live in `scripts/demo_profile_utilization.py`.
- Fake data under `data/profile_utilization_inputs/` and `perfbound/calibration/data/*fake*` is for plumbing, docs, and tests only. Do not use fake data for performance conclusions.

## Commit and Pull Request Guidance
- Use short, imperative commit subjects that name the affected subsystem.
- Keep commits narrowly scoped.
- PR descriptions should explain modeled behavior changes, list commands run, link related issues when available, and include before/after output snippets when reports or scheduler outputs change.

## Pre-Submit Checklist
Before handing off a substantial change:

1. Inspect `git status --short` and separate intentional changes from pre-existing user changes.
2. Run targeted syntax/build/test commands appropriate to the touched files.
3. Update docs when behavior, architecture, report format, data schema, or user workflow changes.
4. Do not claim hardware validation unless the relevant hardware-dependent command actually ran successfully.
5. Record unresolved issues in `.agent/known-issues.md` when they are durable rather than one-off debugging notes.


## Project Documentation Usage

Read only the project documents relevant to the current task:

- Read `.agent/project-context.md` when determining project goals, scope, or intended behavior.
- Read `.agent/architecture.md` for cross-module changes, data-flow changes, or new entrypoints.
- Read `.agent/terminology.md` when implementing or modifying domain concepts, metrics, or units.
- Read `.agent/decisions.md` before changing an established design or architectural convention.
- Read `.agent/known-issues.md` when debugging related functionality or working around known limitations.
- Read `.agent/implementation-status.md` when planning work or determining whether a feature is complete.

Do not read or rewrite every project document for small, localized tasks.
Use source code, tests, configuration, and verified specifications as the final source of truth.

## Documentation Maintenance Rules
Every time a substantive development task is completed:

1. Check whether `.agent/implementation-status.md` needs an update.
2. Add or update `.agent/decisions.md` when a long-lived design decision is introduced or changed.
3. Add or update `.agent/known-issues.md` when an unresolved problem, limitation, missing test, or environment dependency is discovered.
4. Update `.agent/architecture.md` when module boundaries, data flow, or entrypoints change.
5. Update `AGENTS.md` when long-term project rules change.
6. Do not put temporary progress, one-off debugging traces, or task-local notes in `AGENTS.md`.


## Documentation correctness

Project documentation is not assumed to be permanently correct.

When working on a task:

1. Treat source code, tests, configuration, and verified external specifications
   as stronger evidence than existing documentation.
2. If documentation conflicts with the implementation, do not silently follow it.
3. Determine whether the code or documentation is outdated.
4. Update the relevant documentation when the correct behavior can be confirmed.
5. If the correct behavior cannot be confirmed, record the conflict in
   `.agent/known-issues.md` and mark it as `待确认`.
6. Never preserve an existing statement only because it already appears in the
   documentation.

## End-of-task documentation check

After every substantial task, check whether the changes affect:

- implementation status
- architecture
- terminology
- design decisions
- known issues
- build, run, or test instructions

Update only the affected documents.
If nothing changed, do not modify documentation merely to create activity.
