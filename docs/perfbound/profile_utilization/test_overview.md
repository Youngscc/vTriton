# profile_utilization 测试说明

本文档对应测试文件：

`tests/perfbound/test_profile_utilization.py`

测试目标是验证 `perfbound.analyze.profile_utilization` 中两类逻辑：

1. `compute_realized_utilization` 是否能根据 profiling 输入和 component bound 正确计算 `A/I/E/R/U`。
2. `analyze_operator_bottleneck` 是否能根据 `U`、`R`、`E` 给出论文第四章后半部分描述的瓶颈诊断结果。

## 指标公式

每个 component 的中间指标如下：

```text
A = work_done / elapsed_time_us
I = sum(work_i) / sum(work_i / peak_rate_i)
U = A / I
R = active_time_us / elapsed_time_us
E = U / R
```

其中：

- Compute component 的 `work_done` 单位是 ops。
- MTE component 的 `work_done` 单位是 bytes。
- Compute 的 `work_breakdown.label` 表示精度类型，例如 `fp16`、`bf16`、`fp32`、`int8`。
- MTE 的 `work_breakdown.label` 表示传输路径，例如 `gm->ub`、`gm->l1`、`ub->gm`、`l1->ub`。
- `peak_rate` 对 Compute 表示该精度的峰值算力，对 MTE 表示该路径的峰值带宽。

## 测试项

### 1. 混合精度 Ideal Performance

测试函数：

`test_operator_aware_ideal_performance_uses_precision_breakdown`

验证内容：

- 输入一个 Cube component。
- `work_breakdown` 中包含 `fp16`、`bf16`、`int8` 三种精度。
- 验证 `I` 是否按 `sum(ops) / sum(ops / peak)` 计算。
- 验证 `dominant_item` 是否为 work 占比最高的精度。
- 验证正常输入下没有 warning。

### 2. Compute 和 MTE 的数值计算

测试函数：

`test_component_metrics_match_hand_calculation_for_compute_and_mte`

验证内容：

- 同一个 operator 中同时包含 Cube 和 MTE-GM。
- Cube breakdown 包含 `fp16`、`bf16`、`fp32`、`int8`。
- MTE breakdown 包含 `gm->ub`、`gm->l1`、`l1->ub`。
- 分别验证两个 component 的 `A/I/E/R/U` 是否和手工公式一致。
- 验证两个 component 共用同一个 `elapsed_time_us`。

### 3. Compute Bound 诊断

测试函数：

`test_compute_bound_when_compute_utilization_reaches_threshold`

验证内容：

- Cube 的 `U` 被构造成 `0.83`。
- 阈值 `u_threshold = 0.80`。
- 因为 Cube 属于 Compute component，最终诊断应为 `Compute Bound`。
- 同时验证主导 component 是 `cube`，主导精度是 `fp16`。

### 4. MTE Bound 诊断

测试函数：

`test_mte_bound_when_mte_utilization_reaches_threshold`

验证内容：

- MTE-GM 的 `U` 被构造成 `0.82`。
- 阈值 `u_threshold = 0.80`。
- 因为 MTE-GM 属于 MTE component，最终诊断应为 `MTE Bound`。
- 同时验证主导 component 是 `mte_gm`，主导传输路径是 `gm->ub`。

### 5. Insufficient Parallelism 诊断

测试函数：

`test_insufficient_parallelism_when_all_active_ratios_are_low`

验证内容：

- 所有有效 component 的 `U` 都低于 `u_threshold`。
- 所有有效 component 的 `R` 都低于 `r_threshold = 0.50`。
- 最终诊断应为 `Insufficient Parallelism`。
- 该诊断不是单个 component 主导导致的，因此最终输出中的 `dominant_component`、`dominant_item` 置空。

### 6. Inefficient Compute 诊断

测试函数：

`test_inefficient_compute_when_compute_has_high_r_and_low_e`

验证内容：

- Vector 的 `U` 低，没有达到 roofline ceiling。
- Vector 的 `R` 高，但 `E` 低。
- 因为 Vector 属于 Compute component，最终诊断应为 `Inefficient Compute`。
- 主导精度应为 work 占比最高的 `fp32`。

### 7. Inefficient MTE 诊断

测试函数：

`test_inefficient_mte_when_mte_has_high_r_and_low_e`

验证内容：

- MTE-UB 的 `U` 低，没有达到 roofline ceiling。
- MTE-UB 的 `R` 高，但 `E` 低。
- 因为 MTE-UB 属于 MTE component，最终诊断应为 `Inefficient MTE`。
- 主导传输路径应为 work 占比最高的 `ub->gm`。

### 8. 缺少 work_breakdown 的 warning

测试函数：

`test_warning_when_work_breakdown_is_missing_and_fallback_is_used`

验证内容：

- 输入中没有提供 `work_breakdown`。
- `I` 会回退为 `component_bound` 中的 `bound_work / per_component_us`。
- 应产生 fallback warning。

### 9. active_time 超过 elapsed_time 的 warning

测试函数：

`test_warning_when_active_time_is_larger_than_elapsed_time`

验证内容：

- 构造 `active_time_us > elapsed_time_us`。
- 应产生 `active_time_us 大于 elapsed_time_us` warning。

### 10. profiling work 和 bound work 不一致的 warning

测试函数：

`test_warning_when_profile_work_mismatches_component_bound_work`

验证内容：

- profiling 中的 `work_done` 和 `component_bound` 中的理论 work 相差超过 `work_tolerance`。
- 应产生 work mismatch warning。

### 11. U 或 E 超过合理范围的 warning

测试函数：

`test_warning_when_u_or_e_is_unphysical`

验证内容：

- 构造实际性能超过理想性能的场景。
- `U > 1.05` 和 `E > 1.05` 都应产生 warning。

## 对应 JSON

为了避免提前暴露答案，测试数据拆成两个 JSON：

`tests/perfbound/fixtures/profile_utilization/verification_inputs.json`

该文件只保存输入值，适合交给其他模型或脚本独立复算。

`tests/perfbound/fixtures/profile_utilization/verification_expected.json`

该文件保存标准答案，包括中间指标 `A/I/R/U/E` 和最终输出结果，仅用于人工对照。

任务描述和输出格式见：

`docs/perfbound/profile_utilization/verification_task.md`
