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
| `cases/real_data/op_summary_*.csv` | 真数据 | 从真实 profiling 结果整理出的 op_summary 输入 |
| `cases/real_data/des_graph.json` | 真数据 | 与真实 profiling 对应的 DES graph 输入 |

除 `cases/real_data/` 外，本目录里的样例文件都是假数据，只用于验证文件格式和端到端读取链路，不能用于性能结论。真实 DES 样例仍保留在 `data/prefill_des.json`。

## Demo cases

`scripts/demo_profile_utilization.py` 会调用 `profile_utilization.run_from_files()` 完成分析，再在 demo 中把结果对象转换成 JSON，并把完整 JSON 报告写回当前 case 的输出路径。

demo 一次只执行一个数据源。切换数据源时，修改 `scripts/demo_profile_utilization.py` 顶部的：

```python
ACTIVE_CASE = "real_data"
```

| case | 目标输出 |
| --- | --- |
| `default_fake` | 默认端到端 fake 样例 |
| `compute_bound` | operator `Compute Bound`，HIVM `ComputeBound` |
| `inefficient_compute` | operator `Inefficient Compute`，HIVM `ComputeBound` |
| `inefficient_mte` | operator `Inefficient MTE`，HIVM `BandwidthBound` |
| `insufficient_parallelism` | operator `Insufficient Parallelism`，HIVM `PipelineImbalance` |
| `sync_overhead` | operator `Insufficient Parallelism`，HIVM `SyncOverhead` |
| `real_data` | 真实 profiling/DES 输入，用于当前主要分析 |

## 示例命令

```bash
python3 scripts/demo_profile_utilization.py
```

如需只刷新样例 JSON report，可以运行：

```bash
scripts/run_profile_utilization_cases.sh
```

这个批量脚本刷新 fake/demo cases，不包含 `real_data`。真实数据建议通过 `ACTIVE_CASE = "real_data"` 单独运行，避免误覆盖或和假数据结论混在一起。
