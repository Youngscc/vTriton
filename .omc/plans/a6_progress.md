# A.6 Progress — M6 Validation Harness (Measurement + Counterfactual)

## Status: software complete & fully tested offline; live hardware runs gated

A.6 splits into two parts, both implemented:
- **A.6.1 — Measurement wiring** (committed `174d0ab`): msprof parser, tri-state
  soundness harness, three-level reachability report.
- **A.6.2 — Counterfactual validation + remote runner** (this stage): HIVM edits,
  correctness verification, counterfactual orchestration, remote 910B3 runner,
  on-device kernel launcher.

The only work that remains is **inherently hardware/compiler-gated** (running on a
real 910B3, and the CANN compiler bug) — not software-incomplete. Every offline-
testable path is covered.

---

## A.6.1 — Measurement wiring (31 tests)

| Component | File | Tests |
|-----------|------|-------|
| msprof CSV parser (AiCore filter, invocation grouping, warmup discard, median) | `perfbound/validate/msprof_parser.py` | 13 |
| Tri-state validation harness (`ValidationStatus`, `ValidationCase`, soundness excludes infra errors) | `perfbound/validate/harness.py` | 7 |
| Three-level reachability report (HIVM / DSL / measured + provenance) | `perfbound/combine/report.py`, `run_report.py` | 11 |

Key invariants: parallel device rows are **max-ed per invocation, never summed**;
`EXECUTION_ERROR` is **excluded** from the soundness denominator; binding-component
match is computed per-kernel (op-name-filtered).

---

## A.6.2 — Counterfactual validation + remote runner (93 tests)

| Component | File | Tests |
|-----------|------|-------|
| HIVM edit primitives (`raise_repeat`, `insert_pingpong`, `merge_transfers`) + no-op guards + extract-reversibility check | `perfbound/validate/hivm_edits.py` | 23 |
| Output correctness verification (numpy allclose, tolerant) | `perfbound/validate/correctness.py` | 10 |
| Counterfactual orchestration (edit → compile → verify → delta; tri-state infra discipline) | `perfbound/validate/counterfactual.py` | 19 |
| Fallback-kernel counterfactual (mechanism proven on `hivm_mixed_cv_kernel`, decoupled from chunk_kda) | `tests/.../test_counterfactual_fallback.py` | 10 |
| On-device Triton kernel launcher (load → run → dump `.npy`) | `scripts/kernel_launcher.py` | 13 |
| Remote 910B3 runner (sync, recompile, msprof, fetch CSV+npy, host config, CANN preamble) | `scripts/remote_bench.py` | 18 |

### Design decisions
- **Reachability of attribution, not the bound.** A.6.2 validates that a quantified
  gap matches a measured speedup (`output_verified AND |predicted−measured|/measured
  < 20%`, Exp-3 target), separate from A.6.1's soundness check.
- **No-op edits fail loudly.** Each edit raises if it targets zero ops; `factor=1`
  and non-adjacent merges remain legitimate no-raise outcomes. `verify_edit_via_extract`
  re-loads through the real `hivm_extractor` to confirm a model-visible field changed.
- **Tri-state infra discipline.** Compile/profile failures surface as a non-valid
  result with `notes` — never a spurious small delta.
- **Remote runner reuses the hardened contract** (CANN `set_env.sh` + conda `tlx` +
  `PYTHONPATH`, fail-loud, `op_summary_*.csv` via find→rglob fallback, `bishengir-compile`).
- **Counterfactual baseline = ELF model** (recompiled edited HIVM profiled at
  `build/bin/{kernel}`); the Triton-launcher path serves the A.6.1 measurement flow.

---

## Blockers — RESOLVED on real hardware (2026-06-10)

| Item | Original blocker | Status |
|------|------------------|--------|
| chunk_kda compile → DES graph | bishengir-compile crashes in `ConvertLinalgRToBinary` (SmallVector assertion), CANN 9.0.0-**beta.2** | ✅ **RESOLVED** — fixed in CANN 9.0.0 release; chunk_kda compiles+runs on the 910B3 (`.omc/research/hw_runs/RESULTS.md`). `TestChunkKdaCompile` xfail reason updated (now only no-NPU-on-WSL) |
| Does HIVM dump survive the crash? | Needs a live run on the device | ✅ **MOOT** — no crash to survive; full codegen succeeds. `TestDumpBeforeCodegen` docstring updated |
| Live 910B3 validation | Real device (sync → msprof → fetch → parse → soundness) | ✅ **DONE** — real T_measured=104.3 ms, author_headroom=102.9 ms, soundness PASS. Guarded by `test_chunk_kda_hw_validation.py` |
| Counterfactual delta on hardware | edit → recompile → verify → delta on device | 🟡 mechanism offline-proven (`test_counterfactual_fallback.py`) + remote wiring fixed; one live run still pending |

Real-data bug fixed in passing: the kernel profiles as Task Type **`MIX_AIC`**,
which `parse_kernel_time_us` did not recognise (matched only `AI_CORE`), so it
dropped every kernel row. Now both timing and component parsing share
`_is_aicore_task()` (recognises `AI_CORE`/`AICORE`/`MIX_AIC`/`MIX_AIV`/
`AI_VECTOR_CORE`/`AIV`). `remote_bench.py` wiring corrected to the real box
(CANN `ascend-toolkit`, conda `triton_hxl`, single-brace shell groups,
`command -v msprof` preflight, sync excludes for `.git`/`thirdparty`).

Scoping detail: `.omc/plans/a6_2_blockers_scope.md`.

---

## Test totals

- A.6.1: 31 · A.6.2: 93 · HW validation: 4 (`test_chunk_kda_hw_validation.py`)
- Full `perfbound/` suite: **317 passed, 3 skipped, 2 xfailed**
- The 2 xfails are the local milestone compile/dump tests — now xfail only
  because WSL has no NPU device (the bishengir compiler bug is resolved).
