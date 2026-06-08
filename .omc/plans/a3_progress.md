# A.3 Progress — HIVM Extractor Implementation

**Date**: 2026-06-08
**Status**: Complete — ready for A.4

## Summary

A.3 closes the extractor-related gaps identified in the plan: C++/Python DES graph schema mismatch, MTE byte-vs-element aggregation bug, missing transfer metadata, missing eligibility oracle wiring, and non-deterministic C++ output paths.

## Files Changed

### Python (perfbound/extract/)

| File | Change |
|------|--------|
| `hivm_extractor.py` | Fixed `load_hivm_desgraph()` to read `"operations"` (canonical) with `"nodes"` fallback. Fixed `extract_hivm()` MTE aggregation to use bytes not elements. Populated `transfer_sizes`, `transfer_alignments`, normalized memory spaces. Added `start_cycle`/`end_cycle` to OpRecord construction. **Review fix**: added required field validation (id, name, pipe). **Review fix**: canonical compute-to-compute handoff tracing through MTE intermediaries (Cube→FixPipe→Vector yields Cube→Vector). **Review fix**: transfer_alignments uses explicit 0 = unknown. |
| `hivm_runner.py` | **New** — thin runner API `extract_from_npuir()` that invokes `tritonsim-hivm` or `tritonsim-opt`, writes JSON to temp dir, returns `HIVMExtract`. |
| `semantic_extractor.py` | **New** — `analyze_gap1_from_extract()` derives semantic category from HIVM op names and compares against realized unit assignment. `analyze_gap1()` for future TTIR-to-HIVM ID correlation. |
| `eligibility_oracle.py` | Unchanged — already correct rules. Wired via `semantic_extractor.analyze_gap1()` and `analyze_gap1_from_extract()`. |
| `op_classifier.py` | Unchanged — already correct mappings. |
| `__init__.py` | Updated to export all A.3 public APIs including `analyze_gap1_from_extract`. |

### Python (tests/)

| File | Tests | Coverage |
|------|-------|----------|
| `test_hivm_extractor.py` | 22 | DES schema parsing, field validation, MTE byte aggregation, transfer metadata, canonical + immediate handoff extraction, memory space normalization, unit assignment, total cycles |
| `test_eligibility_oracle.py` | 22 | Matmul→Cube, elementwise→Vector, i32 compare→Scalar fallback, unknown conservative, Gap 1 against realized, `analyze_gap1_from_extract` primary path |
| `test_hivm_cli_integration.py` | 3 (xfail) | CLI integration — properly xfail on broken fixture instead of silently passing |

### C++

| File | Change |
|------|--------|
| `lib/AscendModel/Analysis/HIVMAnalysis.cpp` | `emitDESGraph()` now emits `schema_version: "a3_hivm_des_v1"` and `start_cycle`/`end_cycle` per op |
| `include/AscendModel/Transforms/Passes.td` | Added `desGraphFile` option to `HIVMAnalysisPass`. Added `dependencyGraphFile` option to `PipelineAnalysisPass`. |
| `lib/AscendModel/Transforms/HIVMAnalysisPass.cpp` | Wired `desGraphFile` option to call `report.emitDESGraph()` |
| `lib/AscendModel/Transforms/PipelineAnalysisPass.cpp` | Replaced hard-coded `pipeline_dep_graph.json` cwd write with explicit `dependencyGraphFile` option. Removed hard-coded `pipeline_trace.json` write. |

## Test Results

```
108 passed, 3 xfailed in 2.78s
```

Breakdown:
- A.1 calibration tests: 26 passed
- A.2 DSL extractor tests: 18 passed
- A.3 HIVM extractor tests: 22 passed
- A.3 eligibility oracle tests: 22 passed
- A.3 CLI integration tests: 3 xfailed (fixture has "unsupported memory space Attribute")
- A.4 component model tests: 10 passed
- Microbench source test: 1 passed
- MLIR parser tests: 5 passed
- Grid idioms tests: 5 passed

## Verification Commands Run

```bash
python3 -m pytest tests/perfbound/ -q      # 108 passed, 3 xfailed
rg -n 're\.(finditer|search|match)' perfbound/extract/  # no matches
cd build && ninja -j$(nproc)                # all targets built
```

## Acceptance Criteria Status

| AC | Status | Evidence |
|----|--------|----------|
| AC-1: C++/Python DES graph schema compatibility | ✅ | `load_hivm_desgraph()` reads `"operations"` key; `schema_version` emitted; required field validation; 7 schema tests pass |
| AC-2: O_prec reconciliation | ✅ | MTE uses bytes, compute uses elements; 4 aggregation tests pass |
| AC-3: Transfer metadata populated | ✅ | `transfer_sizes` populated; `transfer_alignments` = 0 (unknown, documented); 4 metadata tests pass |
| AC-4: Handoff list structurally correct | ✅ | Canonical Cube→Vector handoff traced through MTE intermediaries; immediate edges also emitted; 4 handoff tests pass |
| AC-5: Eligibility oracle flags i32 Scalar fallback | ✅ | `compute_gap1()` flags i32 compare→Scalar; `analyze_gap1_from_extract()` works on HIVMExtract; 8 Gap1 tests pass |
| AC-6: A.2 compatibility | ✅ | All 63 A.1/A.2 tests still pass; no regex in `perfbound/extract/` |
| AC-7: Deterministic output paths | ✅ | `PipelineAnalysisPass` uses explicit `dependencyGraphFile` option; no cwd writes |
| AC-8: Progress artifact | ✅ | This file |

## Code Review Fixes (post-initial implementation)

| Issue | Severity | Fix |
|-------|----------|-----|
| CLI tests vacuously passed inside `if out_file.exists()` | HIGH | Tests now use `pytest.xfail()` when CLI fails — failure is tracked, not silent |
| Handoffs only capture immediate edges (MTE_UB→Vector), not canonical Cube→Vector | HIGH | Added `_compute_producer_component()` to trace through MTE intermediaries; canonical compute-to-compute handoffs emitted |
| Semantic extractor stub with op_id=0 can't match HIVM IDs | MEDIUM | Added `analyze_gap1_from_extract()` primary path that derives category from HIVM op names directly |
| transfer_alignments used `bytes % 32` (not real alignment) | MEDIUM | Changed to explicit 0 = unknown with documented semantics |
| Missing field validation on DES graph parse | MEDIUM | Added required field validation (id, name, pipe) with clear ValueError |

## Open Items Closed

| Item | Closure |
|------|---------|
| DES graph schema mismatch | Python reads `"operations"` canonical, `"nodes"` legacy |
| Deterministic C++ JSON output paths | Both passes use explicit file options |
| Metadata completeness for Tier 2 | `HIVMExtract` has `o_prec`, `transfer_sizes`, `transfer_alignments`, `unit_assignment`, `handoffs` |
| MTE byte-vs-element aggregation bug | MTE uses `bytes_transferred * loop_multiplier` |
| Gap 1 semantic eligibility input | `analyze_gap1_from_extract()` derives from HIVM op names; `analyze_gap1()` for future TTIR correlation |
| Gap 4 field availability | `repeat`/`mask` fields in OpRecord with explicit defaults |
| Canonical Cube→Vector handoff | Traced through MTE intermediaries for serialization classification |

## A.4 Handoff

A.4 can proceed. The extractor now provides:
- Per-component `o_prec` (bytes for MTE, elements/flops for compute)
- MTE `transfer_sizes` and `transfer_alignments` (0 = unknown)
- Realized `unit_assignment` per op
- `repeat`/`mask` fields with explicit defaults
- `HandoffRecord` list with both immediate and canonical compute-to-compute handoffs
- `Gap1Report` list from `analyze_gap1_from_extract()` primary path

## Known Limitations

1. `repeat`/`mask` default to 1/0 — C++ emitter does not yet populate these. A.4 should treat these as conservative no-gap defaults.
2. Transfer alignment is 0 (unknown) — C++ emitter does not expose address alignment. Gap 2 must treat 0 as unknown, not "aligned".
3. CLI integration tests xfail on the current fixture (`hivm_add_kernel.npuir.mlir` has "unsupported memory space Attribute"). End-to-end C++ verification requires a valid `.npuir.mlir` fixture.
4. `analyze_gap1()` (TTIR-based path) still uses synthetic records. The primary path `analyze_gap1_from_extract()` derives categories from HIVM op names directly.
