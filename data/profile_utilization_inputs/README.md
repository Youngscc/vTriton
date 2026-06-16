# profile_utilization 输入样例

这个目录用于端到端调试 `perfbound.analyze.profile_utilization` 的文件输入路径。

## 文件说明

| 文件 | 真实性 | 用途 |
| --- | --- | --- |
| `des_fake.json` | 假数据 | 按 `tritonsim-hivm --des-graph-file` 格式构造的 DES graph，用于 `extract_hivm()` |
| `op_summary_fake.csv` | 假数据 | 按 `data/op_summary_20260610082013.csv` 的 op_summary 格式构造，只保证字段格式正确 |
| `calib_fake_full.json` | 假数据 | 按 `CalibrationDB` schema 构造的硬件 calibration，占位用 |
| `calib_fake_full.csv` | 假数据 | `calib_fake_full.json` 的 companion bandwidth CSV，占位用 |
| `cases/*/op_summary.csv` | 假数据 | 为 demo 定制的 op_summary 输入，用于覆盖不同诊断分支 |
| `cases/*/des.json` | 假数据 | 为 demo 定制的 DES 输入，用于覆盖不同诊断分支 |
| `cases/*/perfetto_trace.json` | 假数据派生输出 | Python 从对应 DES timeline 导出的 Perfetto trace |

本目录里的所有文件都是假数据，只用于验证文件格式和端到端读取链路，不能用于性能结论。真实 DES 样例仍保留在 `data/prefill_des.json`。

## Demo cases

`scripts/demo_profile_utilization.py` 会通过同一个 `run_from_files()` 入口批量运行这些 case，并把每个完整 JSON 报告写回对应 case 目录：

| case | 目标输出 |
| --- | --- |
| `default_fake` | 默认端到端 fake 样例 |
| `compute_bound` | operator `Compute Bound`，HIVM `ComputeBound` |
| `inefficient_compute` | operator `Inefficient Compute`，HIVM `ComputeBound` |
| `inefficient_mte` | operator `Inefficient MTE`，HIVM `BandwidthBound` |
| `insufficient_parallelism` | operator `Insufficient Parallelism`，HIVM `PipelineImbalance` |
| `sync_overhead` | operator `Insufficient Parallelism`，HIVM `SyncOverhead` |

## 示例命令

```bash
python3 -m perfbound.analyze.profile_utilization \
  --op-summary data/profile_utilization_inputs/op_summary_fake.csv \
  --des-graph data/profile_utilization_inputs/des_fake.json \
  --calibration data/profile_utilization_inputs/calib_fake_full.json \
  --perfetto-trace-file data/profile_utilization_inputs/perfetto_trace.json
```

默认输出到 `data/profile_utilization_inputs/profile_utilization_report.json`。
