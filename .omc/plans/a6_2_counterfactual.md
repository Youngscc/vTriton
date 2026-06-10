# A.6.2 Plan — Counterfactual Validation: HIVM edit → recompile → verify → delta

> Canonical next-stage plan. A.6.1 (measurement wiring + soundness) is committed
> (`174d0ab`). A.6.2 closes the **attribution-validation** half of Module 6: it
> proves the *quantified gap values* are real, not just that the bound holds.

---

## Context

A.6.1 validates the **bound** (`T_bound ≤ T_measured`, soundness + tightness).
It does **not** validate the **five-way attribution** — the claim that
`gap3_avoidable_serial = 220 µs` means removing that serialization actually
saves ~220 µs on hardware. A.6.2 closes that loop:

> hand-edit the HIVM (raise `repeat`, insert ping-pong, etc.) → recompile via
> bishengir → verify the edited kernel still produces the reference output →
> re-profile via msprof → compare `measured_delta` against `predicted_gap`.
> Valid when `output_verified AND |predicted − measured| / measured < 20%`
> (Exp 3 target, a0 §521).

The data model already exists: `perfbound/validate/counterfactual.py` defines
`CounterfactualResult` (with `quantification_error`, `is_valid`) and a
`run_counterfactual()` stub that raises `NotImplementedError`. A.6.2 implements
the runner and its three sub-capabilities (edit, verify, measure-delta).

**Why now**: with A.6.1 landed, soundness can be measured but attribution is
still unfalsifiable. A.6.2 is the last piece that makes the model's per-gap
recommendations ("merge transfers saves X") empirically defensible — the headline
deliverable of the paper's Exp 3.

---

## Critical-path blocker (must resolve FIRST)

**A.5 Gap #1 — bishengir-compile-a5 crashes in `ConvertLinalgRToBinary`
(SmallVector assertion) on CANN 9.0.0-beta.2 compiling `chunk_kda`.**

A.6.2 is *defined by* recompilation: every counterfactual is a recompile of
edited HIVM. If bishengir cannot compile the kernel, there is no after-image to
profile. This blocker currently gates `TestChunkKdaMilestone` (xfail,
`test_chunk_kda_milestone.py:9-11`).

Resolution options, in preference order:
1. **Build a working bishengir from AscendNPU-IR's own LLVM 19.1.7**
   (`scripts/build_bishengir.sh` already drafted; LLVM 19.1.7 submodule).
   Verify it compiles the *unedited* chunk_kda first — that's the gate.
2. **Isolate the crash**: minimal HIVM repro → bisect the failing pass
   (`ConvertLinalgRToBinary`). If it's an upstream assertion, patch via
   `scripts/apply_patches.sh` (already the patch-staging path).
3. **Fallback kernel**: if chunk_kda stays blocked, pick a simpler validation
   kernel from the 10-kernel reference suite that *does* compile, prove the
   counterfactual mechanism end-to-end there, and defer chunk_kda. The mechanism
   must not be coupled to one kernel.

**Acceptance for this blocker**: `bishengir-compile <chunk_kda.hivm>` exits 0 and
emits a loadable binary; `TestChunkKdaMilestone` flips from xfail to pass. This is
a prerequisite checkpoint — A.6.2 runner work can be built in parallel against
mocks, but cannot be *validated* until this clears.

---

## Scope

| In scope | Out of scope |
|----------|--------------|
| `run_counterfactual()` orchestration (edit→compile→verify→profile→compare) | New attribution math (A.5 owns gap computation) |
| HIVM edit primitives (raise `repeat`, insert ping-pong) | Auto-discovery of which edit maps to which gap (curated per-gap recipes) |
| Reference-output correctness check (rtol/atol vs reference_fn) | Bit-exact verification (numerical tolerance only) |
| Delta measurement reusing A.6.1 `parse_kernel_time_us` | New profiler parser (reuse msprof_parser) |
| bishengir recompile wiring via `scripts/remote_bench.py` | Remote infra (built in A.6.1; extend, don't rebuild) |
| CI-testable orchestration with mocked compile/profile | Hardware-path tests (xfail/skip, same as A.6.1) |

---

## Changes

### 1. HIVM edit primitives — `perfbound/validate/hivm_edits.py` (new)

Curated, gap-targeted source-to-source edits on the HIVM text (use the MLIR API
/ structured edit, **not regex** — per project rule). Each edit returns a new
HIVM file and declares which gap it neutralizes:

```python
@dataclass
class HivmEdit:
    gap_name: str                 # "gap3_avoidable_serial" etc.
    description: str
    apply: Callable[[Path], Path] # edited HIVM written to a temp path

def raise_repeat(hivm: Path, factor: int) -> Path: ...      # gap1 wrong-unit
def insert_pingpong(hivm: Path) -> Path: ...                # gap3 avoidable-serial
def merge_transfers(hivm: Path) -> Path: ...               # gap2 coalescing
```

Start with the **one** edit whose gap dominates the chosen validation kernel;
add others incrementally. Each edit must be reversible-checked: re-extract the
edited HIVM through `extract_hivm` and assert the targeted structural field
actually changed (e.g. `repeat` went up), so a no-op edit fails loudly.

### 2. Correctness verification — `perfbound/validate/correctness.py` (new)

```python
def verify_output(kernel_out, reference_fn, *args, rtol=1e-3, atol=1e-5) -> bool
```

Runs the edited kernel's device output against `reference_fn` (the
`ValidationCase.reference_fn` already threaded through A.6.1's `ValidationCase`,
harness.py:60). Uses `numpy.allclose` / `torch.allclose` with the case's
tolerances. A counterfactual whose edit corrupts output is **invalid** regardless
of timing — this is the guard that stops "optimizations" that merely skip work.

### 3. Implement `run_counterfactual()` — `counterfactual.py`

Replace the `NotImplementedError` body with the orchestration:

```
1. profile baseline  → t_before_us         (reuse remote_bench + parse_kernel_time_us)
2. apply HivmEdit     → edited_hivm
3. recompile edited   → bishengir (via remote_bench, extended for --hivm-in)
4. verify_output(edited) → output_verified ; if False → is_valid=False, stop
5. profile edited     → t_after_us
6. measured_delta = t_before_us - t_after_us
7. return CounterfactualResult(predicted_gap_us, t_before, t_after, measured_delta, output_verified)
```

All infra failures (compile crash, profiler error) must surface as a distinct
non-valid result with a `notes` field — **never** silently become a small delta.
Mirror A.6.1's tri-state discipline: a failed recompile is an infra error, not a
"0 µs gap."

### 4. Extend `scripts/remote_bench.py` for recompile + HIVM input

A.6.1's `remote_bench.py` profiles an *existing* binary. A.6.2 needs:
`--hivm-in <edited.hivm>` → run bishengir on remote → produce binary → profile.
Add a `recompile_remote()` alongside `run_msprof_remote()`. Keep the single-`ssh`
-command-string discipline (already fixed in A.6.1).

### 5. Counterfactual suite driver — `perfbound/validate/harness.py`

Add `run_counterfactual_suite(cases: list[CounterfactualCase]) -> list[CounterfactualResult]`
and a summary (`% valid`, median quantification error). `CounterfactualCase`
carries: kernel, gap_name, predicted_gap_us (from the A.5 `KernelReport`), the
`HivmEdit`, and `reference_fn`. This is the Exp-3 entry point.

---

## Testability

Same two-level split as A.6.1:

- **Level A (CI, no hardware)**: unit-test edit primitives against a checked-in
  HIVM fixture (assert structural field changed, output of `extract_hivm`
  differs as expected); unit-test `verify_output` (matching/mismatching arrays);
  unit-test `run_counterfactual` orchestration with **mocked** compile + profile
  (inject `t_before`, `t_after`, verified flag) to exercise `quantification_error`
  / `is_valid` branches and the infra-error path.
- **Level B (hardware, xfail/skip)**: real bishengir recompile + msprof delta on
  910B3. Gated identically to `TestChunkKdaMilestone`.

New tests:
- `tests/perfbound/test_hivm_edits.py` — each edit changes the targeted field;
  no-op edit raises.
- `tests/perfbound/test_correctness.py` — allclose pass/fail, tolerance honored.
- `tests/perfbound/test_counterfactual.py` — mocked end-to-end: valid (<20%),
  invalid (output corrupt), invalid (error>20%), infra-error path.

---

## Verification

```bash
cd /mnt/d/work/git/vTriton

# Level A (CI):
python3 -m pytest tests/perfbound/test_hivm_edits.py \
  tests/perfbound/test_correctness.py \
  tests/perfbound/test_counterfactual.py -v

# Full regression (no new xfails beyond the bishengir milestone):
python3 -m pytest tests/perfbound/ -q

# Level B (hardware, after Gap #1 cleared):
#   bishengir-compile <chunk_kda.hivm>  → exit 0   (gate)
#   run_counterfactual_suite on chunk_kda's dominant gap → is_valid True
```

**Acceptance gate**:
1. Blocker cleared: bishengir compiles unedited chunk_kda; milestone xfail→pass.
2. Edit primitives provably change the targeted HIVM structural field.
3. `verify_output` rejects a corrupted-output counterfactual.
4. `run_counterfactual` infra failures yield a non-valid result with `notes`,
   never a spurious small delta.
5. On hardware: ≥1 gap validated at <20% quantification error (Exp 3).
6. No regression in the A.6.1 suite (219 passed / 1 skipped / 1 xfailed).

---

## Files to create / modify

| File | Action |
|------|--------|
| `scripts/build_bishengir.sh` / `apply_patches.sh` | Resolve Gap #1 (build/patch bishengir) |
| `perfbound/validate/hivm_edits.py` | **New** — gap-targeted HIVM edit primitives |
| `perfbound/validate/correctness.py` | **New** — output verification vs reference_fn |
| `perfbound/validate/counterfactual.py` | Implement `run_counterfactual()` |
| `perfbound/validate/harness.py` | `CounterfactualCase`, `run_counterfactual_suite` |
| `scripts/remote_bench.py` | Add `recompile_remote()` + `--hivm-in` |
| `tests/perfbound/test_hivm_edits.py` | **New** |
| `tests/perfbound/test_correctness.py` | **New** |
| `tests/perfbound/test_counterfactual.py` | **New** |

---

## What A.6.2 does NOT close

- Full B.1–B.5 experiment suite (A.6.2 delivers the *capability*; the campaign
  is separate).
- Scalar throughput calibration (B.4 caveat, a5_progress.md §20) — still a proxy.
- Auto-discovery of edit↔gap mappings (recipes stay curated).
- Bit-exact correctness (tolerance-based only).
