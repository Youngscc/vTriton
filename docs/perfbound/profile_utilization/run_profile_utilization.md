# profile_utilization.py 执行说明

本文档说明 `perfbound/analyze/profile_utilization.py` 的当前使用方式。

`profile_utilization.py` 现在只负责分析并返回诊断对象，不再提供命令行 `main()`，也不直接向屏幕打印 UI 文本。对象转 JSON 和屏幕展示逻辑集中在 `scripts/demo_profile_utilization.py`。

## 分析对象生成

分析模块推荐调用：

```python
from perfbound.analyze.profile_utilization import run_from_files

report = run_from_files(
    "path/to/op_summary.csv",
    "path/to/des.json",
    "path/to/calib.json",
    kernel_name="kernel_name",
    ignore_scalar=False,
)
```

这会：

1. 从 `op_summary.csv`、`des.json` 和 calibration 中运行 profile utilization 分析。
2. 返回 `OperatorBottleneckReport` 诊断对象。
3. 不负责 JSON 序列化或文件写出。

如果需要 JSON report，使用 demo 层的转换函数：

```python
from scripts.demo_profile_utilization import run_profile_utilization_to_json

report_json = run_profile_utilization_to_json(
    "path/to/op_summary.csv",
    "path/to/des.json",
    "path/to/calib.json",
    output_path="path/to/profile_utilization_report.json",
    kernel_name="kernel_name",
)
```

其中 `report_json` 是可以直接 `json.dumps()` 的 `dict`。对象到 JSON 的字段映射逻辑在
`scripts/demo_profile_utilization.py` 中，方便和屏幕 UI 一起维护。

## 主要参数

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `op_summary_path` | 必填 | 输入的 op_summary CSV 文件路径 |
| `desgraph_path` | 必填 | 输入的 DES graph JSON 文件路径 |
| `calibration_path` | 默认 calibration | calibration JSON 文件路径 |
| `output_path` | 不指定 | 可选 JSON report 输出路径，仅 demo 层转换函数使用 |
| `kernel_name` | 不指定 | 从 `op_summary` 中选择要分析的算子名 |
| `u_threshold` | `0.80` | utilization 判断阈值 |
| `r_threshold` | `0.50` | residency 判断阈值 |
| `work_tolerance` | `0.10` | work mismatch warning 的相对误差阈值 |
| `t_bound_us` | 不指定 | 外部传入的 tight bound，单位 us |
| `ignore_scalar` | `False` | 过滤 DES 中的 Scalar component，只使用 Cube、Vector、MTE 做 component/HIVM 诊断；真实 elapsed time 不变 |

### 忽略 Scalar

需要暂时排除 Scalar 控制路径时：

```python
report = run_from_files(
    "path/to/op_summary.csv",
    "path/to/des.json",
    "path/to/calib.json",
    ignore_scalar=True,
)
```

该选项会过滤映射为 `Component.SCALAR` 的 DES operation，包括 `PIPE_S` 和
`PIPE_ALL`，并且不生成 Scalar component 指标。Cube、Vector、MTE 上的操作仍
参与分析。`Task Duration(us)` 继续作为 A/U/R 的真实墙钟时间分母；由于各 pipe
可能重叠，代码不会用 Scalar active time 直接减去 elapsed time。暴露控制/同步
赤字也不会在此模式下计算。该选项不会重新运行或压缩 DES 调度，剩余 Compute/MTE
operation 继续使用原始 `start_cycle/end_cycle`；Scalar 依赖造成的时间线间隙可能
仍然存在。

## 屏幕 UI 输出

如果需要面向人阅读的屏幕输出，运行 demo 脚本：

```bash
python3 scripts/demo_profile_utilization.py
```

这个脚本会：

1. 调用 `run_from_files()` 得到诊断对象。
2. 在 demo 中把对象转换为 JSON dict，并通过 `output_path` 写出 JSON report。
3. 在屏幕上打印 demo 专用的摘要、表格和建议。

## 批量样例

如果只想批量刷新样例 JSON report：

```bash
scripts/run_profile_utilization_cases.sh
```

这个脚本只写 report 文件并打印很少的进度信息，不负责详细 UI 展示。
