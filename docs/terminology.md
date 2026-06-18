# Terminology

| 中文名称 | English | 缩写 | 精确定义 | 代码位置 | 区别/备注 |
| --- | --- | --- | --- | --- | --- |
| AscendModel 方言 | AscendModel dialect | - | 本项目自定义 MLIR dialect，用于表示 Ascend 性能建模相关操作。 | `include/AscendModel/IR/`, `lib/AscendModel/IR/` | 区别于 Triton dialect 和 BiShengIR/HIVM dialect。 |
| HIVM IR | HIVM IR / NPUIR | HIVM / NPUIR | Ascend/BiShengIR 侧的低层 IR，供 HIVM-native 调度、同步、trace 分析使用。 | `tools/tritonsim-hivm/`, `lib/AscendModel/Analysis/HIVMAnalysis.cpp` | 不是 AscendModel dialect；可能由 Triton DSL dump 得到。 |
| DES graph | DES graph JSON | DES | C++ HIVM 分析导出的结构化 JSON，包含 operations、pipe、duration、dependencies、bytes/elements、可选 flops 等字段，供 Python `extract_hivm` 消费。 | `perfbound/extract/hivm_extractor.py`, `docs/perfbound/profile_utilization/input_sources.md` | 用于模型/诊断输入；不是 profiling 真实耗时。`flops` 当前存在文档口径差异，见 `docs/known-issues.md`。 |
| op_summary | msprof op summary CSV | - | msprof 导出的 profiling 汇总 CSV，含 `Task Duration(us)` 和 component active-time 字段。 | `perfbound/analyze/profile_utilization.py`, `perfbound/validate/msprof_parser.py` | 提供真实 elapsed/active time；不同于 DES 模型时间。 |
| 校准数据库 | Calibration database | CalibrationDB | Python dataclass 集合，承载 sustained hardware rates、CI、source、n_runs 和 memory bandwidth table。 | `perfbound/calibration/constants.py`, `perfbound/calibration/calib_loader.py` | 区别于 `configs/*.json` 的架构配置。 |
| 硬件配置 | Hardware configuration | - | JSON 描述硬件 clock、memory spaces、compute units、data movers、pipeline 和 performance_model。 | `configs/*.json`, `configs/hardware_schema.json`, `lib/AscendModel/Analysis/HardwareConfig.cpp` | 主要供 C++建模/配置；CalibrationDB 供 Python sustained-rate 模型。 |
| Component | Component | - | Roofline/性能模型中的硬件组件枚举：cube、vector、scalar、mte_gm、mte_l1、mte_ub。 | `perfbound/extract/op_classifier.py` | Pipe 是调度/IR 层概念，component 是模型聚合层概念。 |
| Kernel | Kernel | - | profiling 中被 `op_summary` 记录和选择的执行单元；`profile_utilization.py` 通过 `kernel_name` 过滤后选择 `Task Duration(us)` 最大的候选行。 | `perfbound/analyze/profile_utilization.py::_read_op_summary_row` | 在 profile utilization 文档中常与 operator 级诊断对应；不是单个 DES op。 |
| 算子级诊断对象 | Operator-level diagnosis target | Operator | `profile_utilization.py` 中的 operator 指一个被分析的 kernel/profile row 及其 DES operations 聚合结果。 | `OperatorBottleneckReport`, `run_from_files` | 不等同于 DES graph 里的每个 operation。 |
| DES operation | DES operation | OpRecord | HIVM DES graph 中的单个 modeled operation，含 `id/name/pipe/duration/start_cycle/end_cycle/depends_on/bytes/elements/flops/...`。 | `perfbound/extract/hivm_extractor.py::OpRecord` | 多个 DES operations 聚合成一个 kernel/operator 的 component 统计。 |
| Cube | Cube core / matrix engine | Cube | Ascend 矩阵计算路径，典型用于 matmul/dot 类 work。 | `Component.CUBE`, `configs/README.md` | 与 Vector 相比处理矩阵/块计算。 |
| Vector | Vector core / SIMD engine | Vector | Ascend SIMD/vector 计算路径，典型用于 elementwise/reduction 等 work。 | `Component.VECTOR`, `configs/README.md` | 与 Scalar 不同，Vector 是模型里的有效 compute component。 |
| Scalar | Scalar/control component | Scalar | profile utilization 中用于承载 scalar/control active time 的 component；也用于 exposed control/sync 诊断。 | `perfbound/analyze/profile_utilization.py` | work 可能为 0 但 active time 高；和 compute work component 不完全等价。 |
| MTE | Memory Transfer Engine | MTE | 数据搬运组件集合；模型拆为 `mte_gm`、`mte_l1`、`mte_ub`。 | `perfbound/extract/op_classifier.py`, `perfbound/model/component_model.py` | Work 单位是 bytes，不是 ops。 |
| Grid floor | Grid-level lower bound | T_grid_floor | Tier 1 分析下界，基于总 work、core 数、occupancy、load balance、binding rate。 | `perfbound/model/grid_model.py`, `perfbound/model/bounds.py` | 与 per-core component floor 是两个不同下界。 |
| Component floor | Component lower bound | T_core_floor | Tier 2 下界，按 component work 和 ideal rate 计算 `max_c(O_c/I_c)`。 | `perfbound/model/component_model.py` | 使用 weighted harmonic mean 处理混合 precision/path。 |
| Serialization split | Serialization split | T_serial | 将 handoff 分为 mandatory 和 avoidable，mandatory 部分进入 bound。 | `perfbound/model/serialization.py`, `perfbound/model/bounds.py` | avoidable serialization 主要用于 attribution。 |
| Bound result | Performance bound result | T_bound | `combine()` 输出的综合性能下界。当前实现为 `max(T_grid_floor, T_core_floor + T_serial_irreducible)`。 | `perfbound/combine/bound_combiner.py` | 代码明确记录它与某些 spec 公式有意不同。 |
| Utilization | Utilization | U | `A/I`，实际平均性能占 ideal performance 的比例。 | `perfbound/analyze/profile_utilization.py` | 与 R/E 不同；U 低需要看 R 和 E 拆因。 |
| Residency | Active-time ratio | R | `active_time_us / elapsed_time_us`，component 在 kernel wall time 中 active 的比例。 | `perfbound/analyze/profile_utilization.py` | R 高不代表效率高。 |
| Efficiency | Active-period efficiency | E | `U/R`，active 期间的效率；R 为 0 时按 0 处理。 | `perfbound/analyze/profile_utilization.py` | 用于区分忙但低效 vs 不够忙。 |
| Actual performance | Actual performance | A | `work_done / elapsed_time_us`。 | `perfbound/analyze/profile_utilization.py` | 分母是真实 profiling elapsed time。 |
| Ideal performance | Ideal performance | I | 对 component 的 operator-aware ideal rate，通常为 work 加权调和平均。 | `perfbound/analyze/profile_utilization.py`, `perfbound/model/component_model.py` | Compute 单位 ops/us；MTE 单位 bytes/us。 |
| ERU | 待确认 | ERU | 未在当前代码、测试和 Markdown 搜索中找到定义或实现。 | 未定位到实现 | 可能与现有 `E/R/U` 指标有关，但映射关系待人工确认。 |
| REU | 待确认 | REU | 未在当前代码、测试和 Markdown 搜索中找到定义或实现。 | 未定位到实现 | 可能与现有 `R/E/U` 指标有关，但映射关系待人工确认。 |
| RSD | 待确认 | RSD | 未在当前代码、测试和 Markdown 搜索中找到定义或实现。 | 未定位到实现 | 需要论文或公式说明确认含义。 |
| Exposed control/sync deficit | Exposed control/sync deficit | - | profile utilization 对论文分类的补充：比较 DES 模型暴露控制比例与实测 scalar 占比的差值。 | `perfbound/analyze/profile_utilization.py` | 诊断指标，不改变 bound。 |
| Gap 1 | Wrong-unit placement | Gap 1 | realized assignment 不在 semantic eligibility 集合内时的 wrong-unit gap。 | `perfbound/extract/eligibility_oracle.py`, `perfbound/combine/bound_combiner.py` | 与 Gap 2/3/4 是不同归因维度。 |
| Gap 2 | Coalescing / transfer efficiency | Gap 2 | MTE 小包、对齐浪费或搬运效率相关 gap。 | `perfbound/combine/bound_combiner.py` | 具体量化逻辑见代码和 tests。 |
| Gap 3 | Avoidable serialization | Gap 3 | 可通过调度/缓冲避免的 handoff serialization。 | `perfbound/model/serialization.py`, `perfbound/combine/bound_combiner.py` | mandatory 部分进入 T_bound，avoidable 部分用于 attribution。 |
| Gap 4 | Intra-unit execution inefficiency | Gap 4 | repeat/mask/SIMD lane 等单元内部执行效率相关 gap。 | `perfbound/combine/bound_combiner.py`, `perfbound/extract/hivm_extractor.py` | C++ emitter 的 repeat/mask 完整性仍见 known issues。 |
| Two-limit | Two-limit computation | A.7 | `T_bound_HIVM` 与 `T_bound_DSL` 比较，区分 compiler headroom。 | `perfbound/combine/two_limit.py` | 不等同于 profile utilization 的 measured diagnosis。 |
| Validation harness | Validation harness | M6 | 硬件验证层，负责 soundness、tightness、counterfactual，不属于模型本身。 | `perfbound/validate/` | 可能依赖 msprof、NPU、远程环境。 |

## Units Used by Fine-Grained Performance Analysis

| Quantity | Unit | Implementation notes |
| --- | --- | --- |
| DES duration / schedule | cycles | `OpRecord.duration_cycles`, `start_cycle`, `end_cycle`; HIVM bottleneck diagnosis reports cycles. |
| Profiling elapsed / active time | microseconds | `op_summary` fields named `*(us)`; used by `profile_utilization.py`. |
| Clock conversion | cycles per microsecond | `CalibrationDB.core.cycles_per_us`; C++ perf report uses Ascend 910B constant `1850 cycles/us`. |
| Compute work | ops or FLOPs | `component_model.py` uses `op.flops` when present, otherwise `op.elements`; `profile_utilization.py` currently uses `op.elements` for compute work. This difference is recorded in `docs/known-issues.md`. |
| MTE work | bytes | MTE components aggregate `bytes_transferred * loop_multiplier`. |
| Compute ideal rate | ops/us or FLOP/us | Cube/Vector calibration TFLOPS are converted to per-microsecond rates by multiplying by `1e6`. |
| Memory bandwidth | bytes/us | Calibration memory bandwidth lookup returns bytes/us; some docs note `GB/s * 1000 = bytes/us`. |
| Utilization/residency/efficiency | ratio | `U`, `R`, and `E` are dimensionless; warnings are emitted when values exceed `1.05`. |
| Sync/barrier overhead ratio | percent | `hivm_bottleneck_diagnosis.py` multiplies sync/barrier cycle ratios by `100.0`. |

## Baseline Versus Actual Comparison

The current measured-vs-theoretical comparison in `profile_utilization.py` is:

1. Theoretical baseline work and component floors come from DES operations plus
   `CalibrationDB`.
2. Actual elapsed and active-time evidence comes from `op_summary`.
3. For each component, actual performance is `A = work_done / elapsed_time_us`.
4. Ideal performance is an operator-aware weighted harmonic mean over precision
   or transfer path when breakdown data is available; otherwise it falls back to
   `component_bound`.
5. `U = A/I`, `R = active_time_us/elapsed_time_us`, and `E = U/R` drive
   diagnosis.
6. If any valid component has `U >= u_threshold`, the report is Compute Bound
   or MTE Bound. Otherwise the code checks insufficient parallelism and then
   high-residency/low-efficiency components.
