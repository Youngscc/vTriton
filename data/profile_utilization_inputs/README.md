# profile_utilization 输入样例

这个目录用于端到端调试 `perfbound.analyze.profile_utilization` 的文件输入路径。

## 文件说明

| 文件 | 真实性 | 用途 |
| --- | --- | --- |
| `des_fake.json` | 假数据 | 按 `tritonsim-hivm --des-graph-file` 格式构造的 DES graph，用于 `extract_hivm()` |
| `op_summary_fake.csv` | 假数据 | 按 `data/op_summary_20260610082013.csv` 的 op_summary 格式构造，只保证字段格式正确 |
| `calib_fake_full.json` | 假数据 | 按 `CalibrationDB` schema 构造的硬件 calibration，占位用 |
| `calib_fake_full.csv` | 假数据 | `calib_fake_full.json` 的 companion bandwidth CSV，占位用 |

本目录里的所有文件都是假数据，只用于验证文件格式和端到端读取链路，不能用于性能结论。真实 DES 样例仍保留在 `data/prefill_des.json`。

## 示例命令

```bash
python3 -m perfbound.analyze.profile_utilization \
  --op-summary data/profile_utilization_inputs/op_summary_fake.csv \
  --des-graph data/profile_utilization_inputs/des_fake.json \
  --calibration data/profile_utilization_inputs/calib_fake_full.json
```

默认输出到 `data/profile_utilization_inputs/profile_utilization_report.json`。
