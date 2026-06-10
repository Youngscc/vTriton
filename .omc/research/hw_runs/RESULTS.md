# Real 910B3 Hardware Runs — Caveat Closure (2026-06-10)

Closes the "hardware-gated, never run on real hardware" caveats flagged on
A.5/A.6/A.7. All runs executed on the remote **910B3** (ssh host `910B3`,
8× 910B3 NPUs, CANN **9.0.0 release**, conda env `triton_hxl`, triton 3.2.0,
aarch64) via `scripts/remote_bench.py` wiring.

## 1. bishengir chunk_kda compile — RESOLVED (was the A.6 Gap-1 blocker)

The blocker was: `bishengir-compile` crashes in `ConvertLinalgRToBinary`
(SmallVector assertion) compiling chunk_kda on **CANN 9.0.0-beta.2**.

**Result:** on **CANN 9.0.0 release**, chunk_kda compiles and runs cleanly:

```
$ python test/chunk_kda_bwd_kernel_wy_dqkg_fused_opt_v2.py
✅ Kernel launched successfully
torch.Size([1, 8192, 32, 128]) torch.float32   # dq
torch.Size([1, 8192, 32, 128]) torch.float32   # dk
torch.Size([1, 8192, 32, 128]) torch.bfloat16  # dv2
torch.Size([32, 1, 8192]) torch.float32         # db
torch.Size([1, 8192, 32, 128]) torch.float32   # dg
torch.Size([32, 1, 8192, 64]) torch.float32     # dA
```

The crash was a third-party compiler bug in the beta, fixed in the release.
The "dump-before-codegen" spike (`TestDumpBeforeCodegen`) is therefore moot:
codegen completes, no crash to survive. `test_chunk_kda_milestone.py` xfail
reasons updated to reflect this (local xfail now only because WSL has no NPU).

## 2. Real T_measured + author_headroom — POPULATED (was always None)

chunk_kda profiled under `msprof` (10 iters → 6 recorded MIX_AIC invocations).
Raw CSV: `chunk_kda_op_summary.csv` (also fixtured at
`tests/perfbound/fixtures/chunk_kda_op_summary_910b3.csv`).

| Quantity | Value | Source |
|----------|-------|--------|
| T_measured | **104,326 µs** (~104 ms/launch) | msprof op_summary, 6× MIX_AIC rows ~104.3 ms each |
| T_bound (HBM floor) | 1,386 µs | analytic: 2.218e9 B / 1.6 TB/s |
| T_bound (compute floor) | 148 µs | analytic: 4.724e10 FLOP / 320 TFLOP/s bf16 |
| binding (predicted) | MTE_GM (memory) | max(floor) = HBM |
| Soundness status | **PASS** (T_bound ≤ T_measured) | `validate_from_csv` |
| Tightness | **75.3×** | T_measured / T_bound |
| author_headroom | **102,940 µs** | T_measured − T_bound_DSL (`TwoLimitResult`) |
| component_match | **False** | predicted `mte`, measured `aicore`-dominant |

### Findings
- **author_headroom is now a real number** (102.9 ms), closing the A.7/M6
  caveat that it was structurally present but never populated.
- **The naive HBM-floor bound is sound but very loose (75×)** for chunk_kda,
  and **mispredicts the binding component**: it predicts memory-bound, but the
  kernel measures as AI compute-core dominated. chunk_kda's dots use tiny
  tiles (64×32×32), so it is issue/compute bound, not HBM bound — motivating
  the tighter component/two-limit analysis over the single grid floor.

## 3. Parser bug exposed by real data — FIXED

Real chunk_kda rows have Task Type **`MIX_AIC`** (mixed cube). The timing
filter `parse_kernel_time_us` only matched `AI_CORE`/`AICORE`, so it dropped
every kernel row → `ValueError` → EXECUTION_ERROR. Meanwhile
`parse_component_durations` already mapped `MIX_AIC`. Fixed by a shared
`_is_aicore_task()` helper recognising `AI_CORE`, `AICORE`, `MIX_AIC`,
`MIX_AIV`, `AI_VECTOR_CORE`, `AIV` — used by both functions so they cannot
drift again. Guarded by `tests/perfbound/test_chunk_kda_hw_validation.py`.

## 4. remote_bench wiring fixed to the real machine

`scripts/remote_bench.py` previously hardcoded CANN `/usr/local/Ascend/cann/
set_env.sh` + conda `tlx` and emitted literal `{{ }}` (invalid bash, would
break the `||` fallbacks on first real run), plus an unrecognised `msprof
--version` preflight and a non-existent default bishengir path. Now: CANN
`ascend-toolkit/set_env.sh` + conda `triton_hxl` (both env-overridable),
single-brace shell groups, `command -v msprof` preflight, `bishengir-compile`
on PATH. Config in `~/.vtriton_remote` (host `910B3`).

## Reproduce

```bash
# config: ~/.vtriton_remote -> [remote] host=910B3 path=/root/vTriton
rsync -az --exclude=.git --exclude=build --exclude=thirdparty ./ 910B3:/root/vTriton/
ssh 910B3 'source /usr/local/Ascend/ascend-toolkit/set_env.sh && \
  conda activate triton_hxl && \
  msprof --application="python /root/vTriton/scripts/kernel_launcher.py \
    --kernel /root/vTriton/test/chunk_kda_bwd_kernel_wy_dqkg_fused_opt_v2.py \
    --output-dir /root/vTriton/kernel_outputs --iters 10" \
    --output=/root/vTriton/msprof_chunk_kda'
# fetch op_summary_*.csv, then:
pytest tests/perfbound/test_chunk_kda_hw_validation.py -q
```
