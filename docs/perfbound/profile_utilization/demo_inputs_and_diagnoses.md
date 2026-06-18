# profile_utilization Demo 输入与诊断类型

## 分析目标

`profile_utilization` 要回答三个问题：

1. 算子是否已经接近某个 component 的理论 ceiling。
2. 如果没有接近 ceiling，是因为硬件不够忙，还是硬件忙了但效率低。
3. 主导问题来自哪个 component，以及该 component 内部是哪种 precision 或 transfer path 占主导。

因此它不是单纯看耗时最大的 pipe，也不是只看理论 roofline。它把两类信息放在一起：

| 信息 | 作用 |
| --- | --- |
| profiling 实测时间 | 给出 kernel 总耗时和每个 component 的 active time |
| DES / HIVM work | 给出每个 component 实际完成了多少 work |
| calibration DB | 给出每类 work 的理想吞吐或带宽 |


## 输出信息的核心逻辑

demo 会把输入信息合成两条证据链：

1. Operator-level profiling 证据：基于 `op_summary` 和 calibration 计算 `A/I/U/R/E`。
2. HIVM structure 证据：基于 DES graph 判断 pipe 压力、pipeline imbalance、sync/barrier 和局部 op 原因。


## 诊断类型总览

| 诊断类型 | 出现位置 | 简单含义 | 典型证据 | 下一步关注 |
| --- | --- | --- | --- | --- |
| `Compute Bound` | Operator-level / HIVM | Compute 侧接近理想上限，主要受 Vector/Cube compute 能力限制 | Compute component 的 `U` 高，或 DES 里 compute pipe weighted cycles 最大 | 减少计算量、调整 precision、优化 tile shape、提高 compute/data 比例 |
| `MTE Bound` | Operator-level | MTE 侧接近理想带宽上限，主要受数据搬运限制 | MTE component 的 `U` 高 | 减少 bytes、增加 tile reuse、优化 transfer path |
| `Inefficient Compute` | Operator-level | Compute component 很忙，但 active 期间效率低 | Compute 的 `R` 高但 `E` 低 | 检查 vector/cube shape、mask、repeat、小 tile、layout、dependency |
| `Inefficient MTE` | Operator-level | MTE component 很忙，但搬运效率低 | MTE 的 `R` 高但 `E` 低 | 检查 GM/UB/L1 路径、alignment、burst size、packet size、reuse |
| `Insufficient Parallelism` | Operator-level | 有效 Compute/MTE component 没有充分工作，整体并行度或 overlap 不足 | 所有有效 component 的 `R` 都低，或有效 component 没有形成主导 | 检查 pipeline depth、overlap、等待暴露、任务切分 |

