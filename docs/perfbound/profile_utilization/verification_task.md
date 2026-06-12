# profile_utilization 验证任务说明

本文档用于描述一个外部验证任务：给定 `profile_utilization` 的输入 JSON，请独立计算每个 component 的 `A/I/R/U/E`，并给出最终分析结果。

注意：为了避免提前暴露答案，输入文件中不包含任何中间结果或最终诊断答案。

## 输入文件

请使用以下文件作为唯一输入：

`tests/perfbound/fixtures/profile_utilization/verification_inputs.json`

该文件只包含测试 case 的输入数据，包括：

- `KernelProfileStats`
- `ComponentBound`
- `work_tolerance`
- 对于瓶颈分析 case，还包含 `u_threshold` 和 `r_threshold`

不要从 `tests/perfbound/fixtures/profile_utilization/verification_expected.json` 读取答案。该文件仅供人工对照使用。

## 你的任务

对 `tests/perfbound/fixtures/profile_utilization/verification_inputs.json` 中的每个 case 完成以下工作：

1. 读取 `inputs.profile` 和 `inputs.component_bound`。
2. 对每个 component 计算：
   - `A`
   - `I`
   - `R`
   - `U`
   - `E`
3. 计算每个 component 的主导项：
   - Compute component：主导 precision。
   - MTE component：主导 transfer path。
4. 根据 case 的 `function_under_test` 给出最终结果：
   - 如果是 `compute_realized_utilization`，输出 component 指标和 warning。
   - 如果是 `analyze_operator_bottleneck`，还需要输出 `diagnosis`、`bound_kind`、`dominant_component`、`dominant_item`、`dominant_share`。

## 公式

### Actual Performance

```text
A = work_done / elapsed_time_us
```

### Ideal Performance

如果 `work_breakdown` 非空：

```text
I = sum(work_i) / sum(work_i / peak_rate_i)
```

如果 `work_breakdown` 为空，则回退到 `ComponentBound`：

```text
I = bound_work / per_component_us
```

其中：

- Compute component 的 `bound_work` 来自 `component_bound.total_ops[component]`。
- MTE component 的 `bound_work` 来自 `component_bound.total_bytes[component]`。

### Active Time Ratio

```text
R = active_time_us / elapsed_time_us
```

### Utilization

```text
U = A / I
```

### Execution Efficiency

```text
E = U / R
```

如果 `R` 为 0，则 `E` 记为 0。

## component 类型

Compute component：

- `cube`
- `vector`
- `scalar`

MTE component：

- `mte_gm`
- `mte_l1`
- `mte_ub`

## Bottleneck 分析规则

对于 `function_under_test = analyze_operator_bottleneck` 的 case，需要继续做瓶颈分析。

有效 component 的条件：

```text
work_done > 0 且 I > 0
```

### 1. Roofline ceiling 判断

如果存在有效 component 满足：

```text
U >= u_threshold
```

选择 `U` 最大的 component 作为 dominant component。

如果 dominant component 属于 Compute component：

```text
diagnosis = "Compute Bound"
bound_kind = "Compute Bound"
```

如果 dominant component 属于 MTE component：

```text
diagnosis = "MTE Bound"
bound_kind = "MTE Bound"
```

### 2. Insufficient Parallelism 判断

如果没有 component 达到 roofline ceiling，并且所有有效 component 都满足：

```text
R < r_threshold
```

则：

```text
diagnosis = "Insufficient Parallelism"
bound_kind = null
```

该诊断不是单个 component 主导导致的，因此 `dominant_*` 字段置空：

```text
dominant_component = null
dominant_item = null
dominant_share = 0.0
```

### 3. Inefficient Component 判断

如果没有 component 达到 roofline ceiling，且不是所有 component 的 `R` 都低，则选择高 `R` 且低 `E` 的 component。

候选 component：

```text
R >= r_threshold 的有效 component
```

如果没有这样的 component，则使用所有有效 component。

选择规则：

```text
score = R * max(0, 1 - E)
dominant_component = score 最大的 component
```

如果 dominant component 属于 Compute component：

```text
diagnosis = "Inefficient Compute"
bound_kind = null
```

如果 dominant component 属于 MTE component：

```text
diagnosis = "Inefficient MTE"
bound_kind = null
```

## warning 规则

请按以下规则输出 warning。

如果 `component_bound` 中没有该 component 的理论 work：

```text
profiling 中有该 component，但理论 bound 中没有对应 work
```

如果 `I <= 0`：

```text
该 component 没有正数的 ideal performance
```

如果 `work_breakdown` 为空并回退到 `component_bound`：

```text
未提供 operator-aware work_breakdown，已回退到 component_bound 的 I_c
```

如果 `active_time_us < 0`：

```text
active_time_us 是负数
```

如果 `active_time_us > elapsed_time_us`：

```text
active_time_us 大于 elapsed_time_us
```

如果 `E > 1.05`：

```text
E > 1.05；请检查单位、profiling 统计或校准值
```

如果 `U > 1.05`：

```text
U > 1.05；请检查 A/I 的单位或 ideal performance 来源
```

如果 `R > 1.05`：

```text
R > 1.05；active_time 和 elapsed_time 的统计口径可能不同
```

如果理论 work 大于 0，并且：

```text
abs(work_done - bound_work) / bound_work > work_tolerance
```

则输出：

```text
profiling work 和理论 bound work 相差 XX.X%
```

其中 `XX.X%` 按一位小数百分比格式化。

report 级别的 warning 格式为：

```text
component: warning
```

例如：

```text
cube: active_time_us 大于 elapsed_time_us
```

## 输出格式要求

请输出一个 JSON，顶层结构必须如下：

```json
{
  "schema_version": "1.0",
  "cases": []
}
```

每个 case 的输出格式如下：

```json
{
  "test_name": "case name from input",
  "function_under_test": "compute_realized_utilization",
  "component_metrics": {},
  "analysis_result": {}
}
```

### component_metrics 格式

`component_metrics` 按 component 名称索引：

```json
{
  "cube": {
    "A": 0.0,
    "I": 0.0,
    "R": 0.0,
    "U": 0.0,
    "E": 0.0,
    "dominant_item": "fp16",
    "dominant_share": 0.0,
    "warnings": []
  }
}
```

字段要求：

- `A`、`I`、`R`、`U`、`E` 必须是数值。
- `dominant_item` 是字符串或 `null`。
- `dominant_share` 是数值。
- `warnings` 是字符串数组。

### analysis_result 格式

如果 `function_under_test = compute_realized_utilization`：

```json
{
  "kernel_name": "kernel name",
  "elapsed_time_us": 0.0,
  "t_core_floor_us": 0.0,
  "binding_component": "cube",
  "warnings": []
}
```

如果 `function_under_test = analyze_operator_bottleneck`：

```json
{
  "kernel_name": "kernel name",
  "elapsed_time_us": 0.0,
  "diagnosis": "Compute Bound",
  "bound_kind": "Compute Bound",
  "dominant_component": "cube",
  "dominant_item": "fp16",
  "dominant_share": 0.0,
  "warnings": []
}
```

## 人工对照文件

标准答案单独保存在：

`tests/perfbound/fixtures/profile_utilization/verification_expected.json`

该文件包含：

- `component_metrics`
- `expected_output`

建议人工比较时只关注：

1. 每个 component 的 `A/I/R/U/E` 是否一致。
2. `dominant_item` 和 `dominant_share` 是否一致。
3. `diagnosis`、`bound_kind`、`dominant_component` 是否一致。
4. warning 是否一致。

浮点数比较建议允许 `1e-9` 到 `1e-8` 的误差。
