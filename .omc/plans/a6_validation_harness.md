# A.6.1 Plan — Measurement Wiring: msprof Parser, Soundness Harness, Three-Level Report

> Canonical copy: `.omc/plans/a6_validation_harness.md`
> This is A.6 **part 1** (measurement + soundness validation).
> A.6.2 covers counterfactual validation (bishengir re-compile + reference diff).

---

## Context

A.5 delivered the full bound combiner and analytical two-limit (`T_bound_HIVM` /
`T_bound_DSL`). The third level of the reachability hierarchy — `T_measured` and
`author_headroom = T_measured − T_bound_DSL` — is wired through `TwoLimitResult`
but never populated.  Five gaps remain open:

| Gap | Location | Symptom |
|-----|----------|---------|
| `t_measured_us` always `None` | `run_report.py` | no `--measured-us` CLI flag |
| `run_validation()` raises `NotImplementedError` | `harness.py` | unusable |
| Report section labelled "Two-Limit (A.7)" | `report.py` | no three-level rendering |
| `MSProfRow` lacks `task_type` / `start_time_us` | `fit_constants.py:63` | cannot filter AiCore rows or group invocations |
| No `ValidationCase` struct | missing | run_validation() API underpowered |

**A.6.1 scope**: CSV parser hardening, `ValidationCase`, tri-state status, remote
910B3 runner, soundness/tightness harness, and three-level report rendering.
**A.6.2 (deferred)**: bishengir recompilation + reference-output verification +
counterfactual delta measurement.

---

## Verified facts

- **msprof output**: `msprof --application=<exe> --output=<dir>` writes
  `op_summary_*.csv` under `mindstudio_profiler_output/` (find via `rglob`).
  Columns include `Op Name`, `Task Type`, `Task Start Time(us)`,
  `Task Duration(us)`. Multiple CANN-version aliases exist.
- **Existing parser**: `MSProfRow` + `read_msprof_csv()` live in
  `perfbound/calibration/scripts/fit_constants.py:62–98`, **not** `cce_remote_bench.py`.
  Current fields: `op_name`, `op_type`, `duration_us`, `cycles`, `task_id`, `core_id`.
  Missing: `task_type` and `start_time_us` — needed to filter AiCore rows and group invocations.
- **Calibration aggregation pattern**: `fit_constants.py:250` discards bottom-third
  outliers for MTE; calibration runs ≥30 iterations then takes mean with CI.
  Validation should group rows by sequential invocation index, discard explicit
  warmup count, then take median of remaining per-invocation wall-clock durations.
- **Remote contract** (a0_perf_bound_model.md §7): sync local checkout →
  remote 910B3 via `scripts/remote_bench.py`; remote runs under `tlx` conda env
  with CANN env sourced; `mindstudio_profiler_output/` contains CSVs; parse
  `Op Name` + `Task Duration(us)` for the target kernel.
  `scripts/remote_bench.py` does **not yet exist** — A.6.1 creates it.
- **No binding-component counter in current CSV fields**: `fit_constants.py`
  does not parse per-component cycle counts. A.6.1 adds basic component-dominance
  inference from AiCore/AiCPU row filtering; full counter breakdown is A.6.2.
- **Median test values**: 1000/1100/1050 have equal mean and median (1050).
  Use outlier set (e.g. 1000/1050/5000: median=1050, mean=2350) to detect
  the mean-vs-median distinction.

---

## Changes

### 1. Extend `MSProfRow` and `read_msprof_csv()` in `fit_constants.py`

Add two fields to the existing `MSProfRow` dataclass:
```python
task_type: str = ""      # "AI_CORE", "AI_CPU", "AIV", etc.
start_time_us: float = 0.0  # Task Start Time(us)
```

Extend the alias lists in `read_msprof_csv()`:
- `task_type`: `["task_type", "Task Type", "TaskType"]`
- `start_time_us`: `["start_time(us)", "Task Start Time(us)", "StartTime(us)"]`

`cce_remote_bench.py` imports `MSProfRow`/`read_msprof_csv` from `fit_constants`
already (confirm or fix the import), so no change needed there.

### 2. New `perfbound/validate/msprof_parser.py`

Import `MSProfRow`, `read_msprof_csv` from `fit_constants` — do not copy.

**`TimingResult` namedtuple** returned by the parser:
```python
TimingResult = namedtuple("TimingResult", ["t_us", "n_invocations", "n_warmup_discarded"])
```

**`parse_kernel_time_us(csv_path, op_name_filter, n_warmup=1) → TimingResult`**

Algorithm:
1. Load rows via `read_msprof_csv(csv_path)`.
2. Filter to AiCore rows: `task_type` contains `"AI_CORE"` (case-insensitive);
   fall back to `op_type` if `task_type` is empty (old CANN CSV).
3. If `op_name_filter` given: keep rows where `op_name` contains the filter
   (exact normalized match, not unrestricted substring).
4. Raise `ValueError` if no rows remain.
5. Sort by `start_time_us`. Group sequential rows into **invocations**:
   each invocation = one or more AiCore rows that started within a tight
   time window (gap threshold: 10× median row duration). Wall-clock latency
   per invocation = max `duration_us` across concurrent rows for that invocation
   (parallel device tasks should not be summed).
6. Discard the first `n_warmup` invocations explicitly.
7. Raise `ValueError` if fewer than 1 valid invocation remains.
8. Return `statistics.median(per_invocation_durations)`.

Edge cases to test: malformed rows (NaN / zero duration, missing field),
mixed AIC+AIV kernels, single-invocation CSV (n_warmup=0 required).

### 3. `ValidationStatus` enum + `ValidationCase` dataclass

New in `perfbound/validate/harness.py`:

```python
class ValidationStatus(str, Enum):
    PASS               = "pass"          # T_bound ≤ T_measured
    BOUND_VIOLATION    = "bound_violation"  # T_bound > T_measured (model bug)
    EXECUTION_ERROR    = "execution_error"  # compile/run/profiler infra failure
    CORRECTNESS_FAILURE = "correctness_failure"  # output mismatch (A.6.2)

@dataclass
class ValidationCase:
    kernel_name: str
    profiler_op_name: str          # what to match in Op Name column
    bound_result: BoundResult      # precomputed bound (from M5)

    # A.6.1 — measurement inputs
    csv_path: Path | None = None   # local op_summary CSV (already synced)

    # A.6.2 — compile/correctness inputs (not used in A.6.1)
    kernel_script: Path | None = None
    reference_fn: Callable | None = None
    rtol: float = 1e-3
    atol: float = 1e-5

    n_warmup: int = 1              # invocations to discard
```

Update `ValidationResult` to use `ValidationStatus`:
```python
status: ValidationStatus = ValidationStatus.EXECUTION_ERROR
```
Soundness statistics must **exclude** non-PASS and non-BOUND_VIOLATION rows
from the denominator. Only `PASS` + `BOUND_VIOLATION` count as valid measurements.

```python
@property
def soundness_rate(self) -> float:
    valid = [r for r in self.results
             if r.status in (ValidationStatus.PASS, ValidationStatus.BOUND_VIOLATION)]
    if not valid:
        return 0.0
    return sum(1 for r in valid if r.status == ValidationStatus.PASS) / len(valid)
```

### 3b. Binding-component validation in `ValidationResult`

Add to `ValidationResult`:
```python
component_match: bool | None = None  # measured dominant component matches predicted
```

Add to `msprof_parser.py`:
```python
def parse_component_durations(csv_path: Path) -> dict[str, float]:
    """Return total duration per task-type category from all rows.
    Categories: 'aicore', 'mte', 'aicpu', 'other'.
    """
```
Map CSV `task_type` values: `AI_CORE`/`AiCore`/`MIX_AIC` → `"aicore"`;
`MTE*` → `"mte"`; `AI_CPU`/`AiCPU` → `"aicpu"`.

In `validate_from_csv()`, after parsing `t_measured_us`, call
`parse_component_durations()` and infer the dominant category (highest total
duration). Compare against `case.bound_result.binding_component`:
- `Component.CUBE` / `Component.VECTOR` → expected `"aicore"`
- `Component.MTE_GM` / `Component.MTE_L1` / `Component.MTE_UB` → expected `"mte"`
- `Component.SCALAR` → expected `"aicpu"`
- If the dominant measured category matches the expected category, set
  `component_match=True`; else `False`. Set `None` if `task_type` fields are
  all empty (old CANN CSV without the column).

Add `component_match` to `ValidationResult.summary()` output and to test coverage:
- `test_component_match_cube_bound` — AI_CORE rows dominate → `True` for CUBE-predicted
- `test_component_match_mismatch` — MTE rows dominate → `False` for CUBE-predicted

### 4. `validate_from_csv()` and `run_validation()`

**`validate_from_csv(case: ValidationCase) → ValidationResult`** (Level A, no hardware):

```python
def validate_from_csv(case: ValidationCase) -> ValidationResult:
    if case.csv_path is None or not case.csv_path.exists():
        return ValidationResult(..., status=ValidationStatus.EXECUTION_ERROR,
                                notes="csv_path missing")
    if case.bound_result.t_bound_us <= 0:
        return ValidationResult(..., status=ValidationStatus.EXECUTION_ERROR,
                                notes="invalid bound: t_bound_us <= 0")
    try:
        timing = parse_kernel_time_us(
            case.csv_path, case.profiler_op_name, case.n_warmup)
    except (ValueError, OSError) as e:
        return ValidationResult(..., status=ValidationStatus.EXECUTION_ERROR, notes=str(e))
    is_violation = case.bound_result.t_bound_us > timing.t_us
    comp_durations = parse_component_durations(case.csv_path)
    component_match = _check_component_match(comp_durations, case.bound_result.binding_component)
    return ValidationResult(
        kernel_name=case.kernel_name,
        t_bound_us=case.bound_result.t_bound_us,
        t_measured_us=timing.t_us,
        n_invocations=timing.n_invocations,
        status=ValidationStatus.BOUND_VIOLATION if is_violation else ValidationStatus.PASS,
        tightness=timing.t_us / case.bound_result.t_bound_us,
        msprof_source=str(case.csv_path),
        component_match=component_match,
    )
```

**`run_validation(cases, remote_host, ...)` (Level B, hardware)**:

Delegates to `scripts/remote_bench.py` (new, see Change 5) for remote sync +
profile. For each case: sync → run msprof → sync back CSV → call
`validate_from_csv(case)`. Wraps all infrastructure exceptions as
`EXECUTION_ERROR` (never `BOUND_VIOLATION`).

### 5. New `scripts/remote_bench.py` (validation runner)

Adapts the `cce_remote_bench.py` pattern for validation kernels (not calibration
microbenchmarks). Responsibilities:
- SSH sync local repo → remote 910B3 under `tlx` env
- Source CANN env (`/usr/local/Ascend/cann/set_env.sh`)
- Run `msprof --application=<exe> --output=<msprof_dir>` on remote
- `rglob("mindstudio_profiler_output/**/op_summary_*.csv")` to locate output
- Sync CSV back to a local temp path
- Return the local CSV path to the caller

**Not in scope**: ssh key management, remote CANN install, kernel binary compilation.
The binary must already exist on remote (built separately or pre-staged).

### 6. Wire `t_measured_us` through the report stack

**`perfbound/combine/run_report.py`**:
- `report_from_desgraph()` + `report_from_npuir()`: add `t_measured_us: float | None = None`
- Pass to `compute_two_limit(..., t_measured_us=t_measured_us)`
- CLI: `--measured-us FLOAT` optional flag

**`perfbound/combine/report.py`** — rename section + render three levels:

```
Reachability Hierarchy:
  1. Hardware floor  (T_bound_HIVM):  1100.00 us
  2. DSL bound       (T_bound_DSL):   1234.56 us   [compiler headroom: 134.56 us]
  3. Measured        (T_measured):    not yet measured
```

When measured and sound:
```
  3. Measured        (T_measured):    1456.78 us   [author headroom: 222.22 us]
     source: /tmp/mindstudio_profiler_output/op_summary_0.csv  n=12 invocations
```

When measured and T_bound > T_measured (violation):
```
  3. Measured        (T_measured):    1100.00 us   *** BOUND VIOLATION: T_bound=1234.56 > T_measured ***
     source: /tmp/mindstudio_profiler_output/op_summary_0.csv  n=12 invocations
```

Level 3 must also show `component_match` when available:
```
     binding component: cube (predicted=cube, match=✓)
```

Add to `ValidationResult`:
```python
n_invocations: int = 0          # valid invocations used in median
component_match: bool | None = None
```

Add to `to_dict()`:
```python
"reachability": {
    "t_bound_hivm_us": ..., "t_bound_dsl_us": ...,
    "t_measured_us": ..., "compiler_headroom_us": ..., "author_headroom_us": ...,
    "is_violation": bool,        # T_bound_DSL > T_measured when measured
    "msprof_source": str | None, # CSV path used for T_measured
    "n_invocations": int | None, # valid invocations in median
    "component_match": bool | None,
}
```

### 7. Tests

**`tests/perfbound/fixtures/op_summary_sample.csv`** (new):
Header: `Op Name,Task Type,Task Start Time(us),Task Duration(us)`
5 rows: 3 × AI_CORE for `target_kernel` (start: 0/1000/2200 µs, duration: 1000/1050/5000 µs),
1 × `AI_CPU` for `target_kernel` (excluded), 1 × `AI_CORE` for `other_kernel`.

**`tests/perfbound/test_msprof_parser.py`** (new):
- `test_aicore_filter_excludes_ai_cpu` — non-AiCore rows excluded
- `test_median_vs_mean_differ` — values 1000/1050/5000 → median=1050, not mean≈2350
- `test_timing_result_fields` — returns `TimingResult` with `.t_us`, `.n_invocations`, `.n_warmup_discarded`
- `test_warmup_discarded` — n_warmup=1 removes first invocation; `n_warmup_discarded=1`
- `test_op_name_filter_exact` — `other_kernel` rows excluded
- `test_no_rows_raises_valueerror` — `ValueError`
- `test_malformed_row_skipped` — NaN duration row → warning printed, row skipped
- `test_zero_duration_excluded` — zero-duration rows treated as malformed
- `test_zero_bound_raises_in_validate` — `ValidationCase.bound_result.t_bound_us=0` → `EXECUTION_ERROR` (not ZeroDivisionError on tightness)
- `test_component_match_cube_bound` — AI_CORE rows dominate → `component_match=True` for CUBE-predicted
- `test_component_match_mismatch` — MTE rows dominate → `component_match=False` for CUBE-predicted
- `test_component_match_none_when_no_task_type` — old CSV without Task Type column → `component_match=None`

**`tests/perfbound/test_report_measured.py`** (new):
- `test_author_headroom_flows_through` — `t_measured_us=5000.0` → `KernelReport.author_headroom_us` correct
- `test_to_text_three_levels` — "Reachability Hierarchy" in output
- `test_to_text_not_measured` — "not yet measured" when `t_measured_us=None`
- `test_to_text_bound_violation` — "BOUND VIOLATION" when T_bound > T_measured
- `test_to_text_shows_source_and_n_invocations` — source path + `n=N invocations` shown when measured
- `test_to_text_shows_component_match` — `match=✓` / `match=✗` rendered when `component_match` is set
- `test_to_dict_reachability_key` — `to_dict()["reachability"]["t_bound_dsl_us"]` present
- `test_to_dict_is_violation_flag` — `is_violation=True` when T_bound > T_measured
- `test_to_dict_msprof_source_and_n_invocations` — `reachability["msprof_source"]` and `reachability["n_invocations"]` present

**`tests/perfbound/test_validation_harness.py`** (new):
- `test_validate_from_csv_pass` — T_measured > T_bound → `PASS`
- `test_validate_from_csv_violation` — T_measured < T_bound → `BOUND_VIOLATION`
- `test_validate_from_csv_missing_csv` — missing path → `EXECUTION_ERROR`
- `test_validate_from_csv_empty_csv` → `EXECUTION_ERROR`
- `test_soundness_rate_excludes_errors` — 1 PASS + 1 EXECUTION_ERROR → rate=1.0 (denom=1)
- `test_soundness_rate_with_violation` — 1 PASS + 1 VIOLATION → rate=0.5

---

## Verification

```bash
cd /mnt/d/work/git/vTriton

# All new tests (no hardware needed):
python3 -m pytest tests/perfbound/test_msprof_parser.py \
  tests/perfbound/test_report_measured.py \
  tests/perfbound/test_validation_harness.py -v

# Regression (174 existing + new; 3 xfails still expected):
python3 -m pytest tests/perfbound/ -q

# Smoke --measured-us flag (requires existing des.json):
python3 -m perfbound.combine.run_report \
  --desgraph /tmp/kda_des.json --grid 128,32 --measured-us 2500.0 \
  | grep -A8 "Reachability"
```

**Acceptance gate**:
1. Parser: median-vs-mean test passes; warmup discard explicit; malformed rows skipped
2. Harness: `EXECUTION_ERROR` never counted in soundness denominator
3. Report: three-level hierarchy renders; bound violation labelled distinctly
4. `to_dict()["reachability"]` present with `is_violation` field
5. No regression in existing 174-test suite

---

## Files to create / modify

| File | Action |
|------|--------|
| `perfbound/calibration/scripts/fit_constants.py` | Add `task_type`, `start_time_us` to `MSProfRow` |
| `tests/perfbound/test_calibration_extraction.py` | Update for new fields |
| `perfbound/validate/msprof_parser.py` | **New** — `TimingResult`, `parse_kernel_time_us()`, `parse_component_durations()` |
| `perfbound/validate/harness.py` | `ValidationStatus`, `ValidationCase`, `n_invocations`/`component_match` on `ValidationResult`, implement harness |
| `scripts/remote_bench.py` | **New** — remote 910B3 sync + msprof runner |
| `perfbound/combine/run_report.py` | `--measured-us` + `t_measured_us` param |
| `perfbound/combine/report.py` | Three-level rendering + `reachability` dict |
| `tests/perfbound/fixtures/op_summary_sample.csv` | **New** fixture |
| `tests/perfbound/test_msprof_parser.py` | **New** |
| `tests/perfbound/test_report_measured.py` | **New** |
| `tests/perfbound/test_validation_harness.py` | **New** |

---

## Open items this stage closes

| Item | Closed by |
|------|-----------|
| `t_measured_us` always None; no `--measured-us` CLI | Change 6 |
| `run_validation()` NotImplementedError | Change 4 |
| "Two-Limit (A.7)" label; no three-level rendering | Change 6 |
| `MSProfRow` missing `task_type` / `start_time_us` | Change 1 |
| No `ValidationCase` struct; `run_validation()` API underpowered | Change 3 |
| Hardware failures counted as bound violations | Change 3 (tri-state) |
| No remote runner for validation | Change 5 |

## Does NOT close (A.6.2 scope)

- `run_counterfactual()` — hand-edit HIVM + bishengir recompile + delta measure
- Bishengir compilation from source within the harness
- Reference-output correctness verification
- `TestChunkKdaCompile` xfail (Gap #1 — HIVM parser)
- Scalar throughput calibration (B.4 caveat from a5_progress.md)
- Full B.1–B.5 experiment suite
