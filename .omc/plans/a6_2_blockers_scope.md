# A.6.2 Blockers — Scoping: bishengir Gap #1 + Remote Profile/Compile Stubs

> Scope-only (no implementation). Sizes the two things that keep A.6.2 from
> running end-to-end on real silicon. Companion to `.omc/plans/a6_2_counterfactual.md`.

---

## Verified state (2026-06-09)

| Fact | Evidence |
|------|----------|
| `bishengir-compile` **is built** | `…/AscendNPU-IR/build/bin/bishengir-compile` (117 MB, Jun 9 16:44) + `bishengir-opt`, `bishengir-lsp-server`, etc. |
| CANN present locally | `/home/shane/Ascend` exists |
| `tritonsim-hivm` built | `build/bin/tritonsim-hivm` (Jun 9 18:30) |
| Built binary is named `bishengir-compile` — **no `-a5` suffix** | `ls .../build/bin \| grep compile` → only `bishengir-compile` |
| Scripts/tests reference `bishengir-compile-a5` | `remote_bench.py:recompile_remote` default; xfail reason text |
| tritonsim-hivm drives bishengir via the dump launcher | `tools/common/triton_dsl_dump_launcher.py:106,212` — asks `bishengir-compile` to print HIVM IR, runs again for NPUIR dump |
| Crash modes (from xfail) | (1) HIVM pipeline cannot legalize `linalg.generic`; (2) `ConvertLinalgRToBinary` SmallVector assertion — both tagged "CANN 9.0.0-beta.2 compiler bugs" |

**Consequence of the reframe:** Gap #1 is a *compiler-runtime* blocker on the
`chunk_kda` kernel, not a missing-build blocker. The build path (`build_bishengir.sh`,
`reconfigure_vtriton.sh`, the 3 LLVM-20 patches) already succeeded.

---

## Blocker 1 — bishengir crash on chunk_kda (A.5 Gap #1)

### What actually fails
`tritonsim-hivm --triton-script chunk_kda…` → invokes `bishengir-compile` → crashes.
Two distinct failures are bundled under one xfail:
- **1a. Legalization**: the HIVM lowering pipeline cannot legalize a `linalg.generic`
  produced from the chunk_kda Triton.
- **1b. Codegen assertion**: `ConvertLinalgRToBinary` (a late binary-codegen pass)
  trips a `SmallVector` assertion.

Both live **inside the bishengir/CANN compiler**, not in vTriton code. `ConvertLinalgRToBinary`
was not found in the AscendNPU-IR source we checked — it is an installed/backend pass.

### Key insight that splits the scope
The **modelling path (M3 extraction)** only needs the *HIVM IR text dump*, which the
dump launcher prints **after sync-injection but before** binary codegen. The
**counterfactual path (A.6.2)** needs a *runnable binary*, which requires the codegen
pass (1b) to succeed. These have very different costs:

| Need | Requires | Blocked by |
|------|----------|-----------|
| DES graph / bound for chunk_kda (M3/M5) | HIVM dump only | 1a (if dump is before legalization failure, maybe not blocked) |
| Counterfactual delta on chunk_kda (A.6.2) | runnable binary + msprof | 1a **and** 1b |

### Resolution paths (preference order)
1. **Reproduce + capture locally (S, do first).** The toolchain is now local —
   run the exact `tritonsim-hivm --triton-script` command, capture stderr/stack,
   and pin down: at which pass does it die, and **is the HIVM dump already written
   before the crash?** If the dump survives, the *modelling* milestone can flip to
   pass independent of 1b. Spike, ~½ day.
2. **Fix the `-a5` naming bug (S, trivial).** `remote_bench.py` and the xfail text
   say `bishengir-compile-a5`; only `bishengir-compile` exists. Any remote/compile
   path will fail on a missing binary until this is corrected (or a real `-a5`
   wrapper is located). One-line default + grep for other refs.
3. **Dump-before-codegen capture (M).** If 1b is a *late* pass, configure the launcher
   to stop after the HIVM/NPUIR dump (it already runs bishengir twice for dumps) and
   never reach `ConvertLinalgRToBinary`. Unblocks chunk_kda *modelling* without a
   compiler fix. Depends on spike (1) confirming dump precedes crash.
4. **Isolate + patch the compiler bug (L, high-risk).** Minimal `linalg.generic`
   repro → `bishengir-opt` pass bisect → patch via `patches/` (the LLVM-20 patches
   show this is an established mechanism). Needed only for a *runnable chunk_kda
   binary* (counterfactual). Upstream/CANN-version dependent; may not be tractable
   on 9.0.0-beta.2.
5. **Fallback kernel (M, de-risks A.6.2).** Pick a simpler kernel from the reference
   suite that compiles to a runnable binary today; prove the counterfactual mechanism
   there. Decouples A.6.2 validation from the chunk_kda compiler bug entirely.

### Recommended sequencing
Spike (1) → naming fix (2) → branch: if dump survives, do (3) to unblock chunk_kda
*modelling* now; for A.6.2 *counterfactual*, pursue (5) first (fast path to a green
Exp-3 result) and treat (4) as a separate, time-boxed compiler investigation.

### Open questions
- Does the HIVM dump complete before the crash? (spike answers this)
- Is `ConvertLinalgRToBinary` reachable only for runnable-binary emission, or also on
  the dump path?
- Is there a real `bishengir-compile-a5` target elsewhere, or is the name stale?

---

## Blocker 2 — Remote profile/compile stubs

### Current state
- `counterfactual._default_profile_baseline` → `NotImplementedError` on the remote branch
  (local CSV branch works).
- `counterfactual._default_compile_and_profile` → `NotImplementedError`; **`kernel_output`
  is hard-coded `None`** → correctness verification cannot run in production.
- `scripts/remote_bench.py` (266 lines) has `recompile_remote()` + `run_remote_bench(hivm_in=…)` +
  `run_msprof_remote()` + `fetch_csv_from_remote()` — structurally present, **untested**,
  and with several contract gaps below.

### Major finding: a mature remote runner already exists — reuse it
`perfbound/calibration/scripts/cce_remote_bench.py` (**779 lines, production**) already
implements the hard parts of the remote contract for the M1 calibration path:
`preflight_remote` (verifies `msprof`/`ccec` on PATH after `set_env.sh`), SSH-banner
sanitization, `source_cann()` + `ascend_runtime_lib_dirs()`, tar-based `sync_cce_files`,
msprof run, and CSV sync-back. `scripts/remote_bench.py` **reinvented this more crudely**
(naive `rsync`, raw `ssh bash`, wrong `-a5` binary name) instead of reusing it.

**Implication:** the remote infra (sync / preflight / CANN env / msprof / fetch) is *not*
greenfield. The genuinely new work is narrower: swap "what runs under msprof" from a
**ccec-compiled CCE launcher** to a **Triton kernel launched via python + torch_npu**, and
add **output dump-back**. Recommended: refactor `remote_bench.py` to reuse
`cce_remote_bench.py`'s helpers rather than maintain two divergent SSH layers.

### Gaps to close (each must be addressed)
1. **Wrong binary name** — `recompile_remote` defaults to `bishengir-compile-a5`
   (does not exist). → use `bishengir-compile`. *(S)* Shared with Blocker 1 fix #2.
2. **Execution model mismatch (the core work).** `run_remote_bench` profiles a prebuilt
   ELF at `build/bin/{kernel_name}` via `msprof --application=<exe>`. But chunk_kda is a
   **Triton/Python kernel run through torch_npu**, not a standalone C++ binary. The
   real path is `msprof --application="python launch_kernel.py"`. The `kernel_script`
   param exists but is **never used** in the msprof invocation. → a remote launcher
   Python harness that imports the kernel, runs it under torch_npu with fixed inputs,
   and is what msprof wraps. **Reuse `cce_remote_bench.py`'s sync/preflight/CANN/msprof/fetch
   helpers; only the launcher body (ccec-build → python-kernel-launch) and output dump are
   new.** *(M — adapt existing infra, not greenfield.)*
3. **`recompile_remote` CLI shape unverified.** `bishengir-compile <hivm> -o <bin>` is
   assumed; the actual invocation for an *edited HIVM* (vs a Triton script) is unknown —
   bishengir may expect NPUIR/Triton input, not hand-edited HIVM text. → confirm what
   input format the edited-HIVM recompile actually takes. *(M, depends on Blocker 1 spike.)*
4. **Device output extraction is absent.** Correctness verification needs the edited
   kernel's output tensor. Nothing dumps it. → the remote launcher (gap 2) must write
   the output (e.g. `.npy`) and ship it back, or compute pass/fail remotely vs
   `reference_fn`. Until then `verify_output` only runs under mocks. *(M.)*
5. **Wire the stubs to remote_bench.** Once 1–4 land, replace both `NotImplementedError`
   branches: `_default_profile_baseline` → `run_remote_bench` (no `hivm_in`) → parse CSV;
   `_default_compile_and_profile` → `run_remote_bench(hivm_in=edited)` → parse CSV +
   return fetched output. *(M.)*
6. **Contract conformance (a0 §7).** `conda activate tlx`, `source …/set_env.sh`,
   `PYTHONPATH=/home/dyq/triton-ascend/python`, `rglob('**/op_summary_*.csv')`, parse
   `Op Name` + `Task Duration(us)`. remote_bench partially does this; audit against §7.
   Guardrail: **no silent fallback to system Python** — fail loud on conda/CANN errors. *(S.)*
7. **A configured remote host.** All functions take `remote_host` as a free param; there
   is no pinned 910B3 target or SSH/key setup. → decide host config (env/CLI/config file)
   and document. *(S, but a prerequisite to any live run.)*

### What's testable offline vs hardware-only
- **Offline (CI):** binary-name fix, §7 command-string construction (assert the exact
  `ssh`/`msprof` strings via a fake runner), CSV parse of a captured real `op_summary`,
  stub→remote_bench dispatch with a mocked `subprocess`.
- **Hardware-only (xfail/skip):** the actual remote run, recompile, msprof capture, and
  output round-trip — gated like the existing milestone.

### Recommended sequencing
Naming fix (1) + §7 audit (6) + host config (7) are quick and unblock everything.
The **remote Triton-kernel launcher (2)** is the real deliverable and the prerequisite
for both profiling and output extraction (4); build it before wiring the stubs (5).
Recompile-input format (3) is gated on the Blocker-1 spike.

---

## Combined critical path

```
Blocker-1 spike (reproduce, capture, does-dump-survive?)   [S]  ← do first
        │
        ├─ naming fix bishengir-compile-a5 → bishengir-compile  [S]  (shared)
        │
        ├─ if dump survives → dump-before-codegen → chunk_kda MODELLING unblocked [M]
        │
        └─ remote Triton-kernel launcher (msprof-wrapped python + output dump) [L]
                   │
                   ├─ wire _default_profile_baseline → remote_bench           [M]
                   ├─ wire _default_compile_and_profile (+ output) → remote   [M]
                   └─ recompile-input-format confirm (gated on spike)          [M]
                           │
                           └─ A.6.2 COUNTERFACTUAL on fallback kernel first    [M]
                                      then chunk_kda iff compiler bug fixed     [L, optional]
```

**Rough total:** ~3 small + 5 medium + 0–1 large (the only potential large item is
patching the CANN compiler bug, which is optional / fallback-kernel-avoidable). The
remote launcher dropped from L→M once `cce_remote_bench.py` was found as a reusable base.
The single highest-leverage unknown is the Blocker-1 spike (½ day, local, no new infra) —
it decides whether chunk_kda modelling is one config flag away or needs a compiler patch,
and it informs the recompile-input format for the remote path.

## Explicitly out of scope here
- Fixing the CANN 9.0.0-beta.2 compiler bug itself (separate, time-boxed effort).
- The full B.1–B.5 experiment campaign.
- Scalar-throughput recalibration (B.4 caveat).
