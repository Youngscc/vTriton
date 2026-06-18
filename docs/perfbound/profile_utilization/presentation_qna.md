# profile_utilization 演示专家问答准备

本文档用于演示或答辩前准备。问题假设来自一个已经了解性能分析、profiling 和调度模型的专家；回答建议保持简洁，但要能说明模型边界和关键公式。

## 1. 这个工具到底在解决什么问题？

**专家可能问：**

`profile_utilization` 和普通 profiling report 有什么区别？为什么不能直接看哪个时间最大？

**推荐回答：**

普通 profiling 主要告诉我们每个硬件单元 active 了多久，但只看 active time 不知道它是“真的达到上限”，还是“忙但效率低”。`profile_utilization` 把三类信息合起来：

- `op_summary` 提供真实 elapsed time 和各 component active time。
- DES graph 提供每个 component 的 work，比如 ops、bytes、precision、transfer path。
- calibration DB 提供理想吞吐或带宽。

然后计算 $A/I/U/R/E$：

- $U$ 判断是否接近 component ceiling。
- $R$ 判断 component 是否真的忙。
- $E$ 判断 active 期间是否有效率。

所以它回答的是：“瓶颈是达到上限、并行不足，还是某个 component 忙但低效。”

## 2. 为什么 `op_summary` 只选一行，而不是每一行都算？

**专家可能问：**

`op_summary.csv` 里面有很多行，为什么代码只取 `Task Duration(us)` 最大的那一行？

**推荐回答：**

目前 `profile_utilization` 是按一个 kernel 的关键执行实例做诊断，不是批量分析所有 op。代码会先读入所有行，如果指定了 `--kernel-name`，就筛选匹配的行；如果没指定，就用所有行作为候选。最后取 `Task Duration(us)` 最大的行。

原因是 profiling 里同一个 grid kernel 可能有多条 shard/core 记录，它们在硬件上并发执行。wall time 不应该把这些行求和，否则会把并发时间重复累加。取最长的一行相当于取 critical shard / critical core，作为这个 kernel 的 elapsed time。

如果未来要分析整张 op_summary，可以在外层循环逐行调用当前分析逻辑，但单次诊断仍然需要先确定目标 kernel 行。

## 3. $U$、$R$、$E$ 分别代表什么？

**专家可能问：**

你怎么解释 $U$、$R$、$E$？这几个指标有什么必要？

**推荐回答：**

对每个 component：

$$
A_c = \frac{O_c}{T}
$$

表示整个 kernel 时间内的实际平均性能。

$$
U_c = \frac{A_c}{I_c}
$$

表示它达到理想性能的比例，也就是 utilization。

$$
R_c = \frac{T_{\mathrm{active},c}}{T}
$$

表示这个 component 在整个 kernel 里有多少时间处于 active 状态，也就是 residency。

$$
E_c = \frac{U_c}{R_c}
$$

表示只看 active 时间时，它执行得是否有效率。

关键关系是：

$$
U_c = R_c \cdot E_c
$$

所以如果 $U$ 低，要继续看是 $R$ 低还是 $E$ 低。$R$ 低更像并行度不足或等待暴露；$R$ 高但 $E$ 低更像 component 内部效率问题。

## 4. 为什么 ideal performance 用调和平均？

**专家可能问：**

一个 component 有多种 precision 或多条 transfer path，为什么不是简单平均 peak？

**推荐回答：**

因为每一类 work 的峰值不同，真正的理想时间是每类 work 各自除以对应 peak 后再求和。

$$
I_c =
\frac{\sum_i O_{c,i}}
     {\sum_i \frac{O_{c,i}}{P_{c,i}}}
$$

分母 $\sum_i O_{c,i}/P_{c,i}$ 是所有 work 在理想硬件上的总耗时，分子是总 work。因此这个公式本质上是 “总 work / 总理想时间”。

如果简单算术平均 peak，会错误高估快 precision 或高带宽路径的作用，不能反映慢路径对总时间的拖累。

## 5. 怎么判断 Compute Bound、Inefficient Compute 和 Insufficient Parallelism？

**专家可能问：**

这几个 diagnosis 的分界线是什么？

**推荐回答：**

判定顺序是：

1. 先看是否达到 ceiling：

$$
U_c \ge u_{\mathrm{threshold}}
$$

如果 compute component 达到阈值，就是 `Compute Bound`；如果 MTE component 达到阈值，就是 `MTE Bound`。

2. 如果没有任何 component 达到 ceiling，就进入 underutilization 分析。

如果所有有效 component 都低 residency：

$$
\forall c,\ R_c < r_{\mathrm{threshold}}
$$

就判断为 `Insufficient Parallelism`。

3. 如果有 component residency 高，但 efficiency 低，就按 component 类型判断：

$$
\mathrm{score}_c = R_c \cdot \max(0, 1 - E_c)
$$

score 最大的是 Compute component，就输出 `Inefficient Compute`；如果是 MTE component，就输出 `Inefficient MTE`。

## 6. DES cycle 和 profiling elapsed time 是不是一回事？

**专家可能问：**

既然 DES 里有 `clock_ghz`，cycle 能换成 us，那和 `elapsed_time_us` 等价吗？

**推荐回答：**

不等价。

DES cycle 是模型时间线里的调度单位，可以通过 `clock_ghz` 换成模型时间：

$$
\mathrm{time\_us}
=
\frac{\mathrm{cycles}}{\mathrm{clock\_ghz} \times 1000}
$$

但 `elapsed_time_us` 来自 profiling，是真实硬件执行时间。DES 模型主要用于解释结构，比如 pipe busy、sync、barrier、loop-scaled weighted cycles。profiling elapsed time 用于真实利用率计算。

所以两者可以互相参考，但不能直接当成同一个量。

## 7. `loop_multiplier` 为什么要进入 `weighted_pipe_cycles`？

**专家可能问：**

如果 loop 会在时间线不同位置执行，为什么还要乘 `loop_multiplier`？

**推荐回答：**

`duration` 表示 op 单次执行的 cycle。`loop_multiplier` 表示这个 op 因外层 loop 会执行多少次。

如果 DES graph 是压缩表示，时间线里可能只保留一个代表性 op：

```text
load duration=10 loop_multiplier=1000
```

这时如果不乘 `loop_multiplier`，会严重低估它对 pipe 的总压力。

所以：

$$
\mathrm{weighted\_pipe\_cycles}_p
=
\sum_{j:\ \mathrm{pipe}_j=p}
\mathrm{duration}_j \cdot \mathrm{loop\_multiplier}_j
$$

它不是 wall-clock elapsed cycles，而是 loop-scaled pipe workload。它回答的是“这条 pipe 总共承担了多少工作压力”，不是“kernel 绝对运行了多久”。

如果时间线已经完全展开成 1000 个 op，那理论上不需要再乘 1000；但当前字段的语义就是保留压缩表示下的总工作量信息。

## 8. `pipe_busy_cycles` 和 `weighted_pipe_cycles` 有什么区别？

**专家可能问：**

为什么既要看 busy cycles，又要看 weighted cycles？

**推荐回答：**

`pipe_busy_cycles` 是一轮 DES 时间线里某条 pipe 累计 active 的 cycle：

$$
\mathrm{pipe\_busy\_cycles}_p
=
\sum_{j:\ \mathrm{pipe}_j=p}
\mathrm{duration}_j
$$

它更接近“单轮时间线中这条 pipe 忙了多久”。

`weighted_pipe_cycles` 额外乘上 `loop_multiplier`：

$$
\mathrm{weighted\_pipe\_cycles}_p
=
\sum_{j:\ \mathrm{pipe}_j=p}
\mathrm{duration}_j \cdot \mathrm{loop\_multiplier}_j
$$

它更接近“考虑循环重复后，这条 pipe 的累计工作压力”。因此 global bottleneck 里用 weighted cycles 找主导 pipe。

## 9. Sync 和 barrier 在这里是什么意思？

**专家可能问：**

`sync_ratio` 和 `barrier_ratio` 为什么能触发 `SyncOverhead`？

**推荐回答：**

sync 是同步/控制类 op，包括 `set_flag`、`wait_flag`、`sync_block_set`、`sync_block_wait`、`pipe_barrier` 等。barrier 是 sync 里面更强、更粗粒度的一类。

代码计算：

$$
\mathrm{sync\_ratio}
=
\frac{\mathrm{sync\_cycles}}{\mathrm{one\_iteration\_cycles}}
\cdot 100\%
$$

$$
\mathrm{barrier\_ratio}
=
\frac{\mathrm{barrier\_cycles}}{\mathrm{one\_iteration\_cycles}}
\cdot 100\%
$$

如果 sync 或 barrier 占比过高，说明模型时间线里控制等待已经明显暴露，所以优先诊断为 `SyncOverhead`。

需要说明的是，这里的分子是 duration 求和，不是对重叠区间去重后的 wall time。因此它更像同步类 op 的累计压力。

## 10. op 局部诊断是怎么来的？

**专家可能问：**

`op_diagnoses` 里为什么一个 op 会被判成 `StartupOverhead` 或 `BandwidthBound`？

**推荐回答：**

op 级诊断先看这个 op 是不是 sync/barrier。如果是，就直接判 `SyncOverhead`。

如果是 MTE transfer op，会用：

$$
\mathrm{transfer\_only}
=
\mathrm{duration}
-
\mathrm{startup\_latency}
$$

如果 startup 比 transfer work 更大，就判 `StartupOverhead`；否则判 `BandwidthBound`。

如果是 Compute op，会用类似逻辑：

$$
\mathrm{compute\_only}
=
\mathrm{duration}
-
\mathrm{startup\_latency}
$$

如果 startup 主导，判 `StartupOverhead`；否则判 `ComputeBound`。

另外会估一个 `theoretical_min_cycles`，再算：

$$
\mathrm{overhead\_ratio}
=
\frac{
  \mathrm{actual\_cycles} - \mathrm{theoretical\_min\_cycles}
}{
  \mathrm{actual\_cycles}
}
$$

这个比例用于解释这个 op 的 duration 是否有明显不能被理论最小成本解释的部分。

## 11. 如果 op 的 overhead ratio 是负数，怎么解释？

**专家可能问：**

demo 里有些 op 的 `theoretical_min_cycles` 比 `actual_cycles` 还大，这是不是模型错了？

**推荐回答：**

负数说明当前 demo/fake 数据或 calibration 口径不完全物理一致。它不是最终 diagnosis 的核心证据，而是提示 theoretical_min 和 DES duration 的口径需要对齐。

真实数据里我们更关注趋势：

- overhead ratio 大于 0：DES duration 超过理论最小值，可能有 startup、等待或低效开销。
- 接近 0：duration 基本能被理论最小 work 解释。
- 小于 0：说明输入数据、单位、calibration 或 fake case 构造存在口径不一致。

演示时可以明确说：fake case 是为了触发分类逻辑，不用于证明理论最小 cycle 的数值准确性。

## 12. 当前 demo 输出里 “先看哪里” 是怎么来的？

**专家可能问：**

输出里的 “先看: vector compute path (bf16)” 是模型原始结论吗？

**推荐回答：**

这是 demo 打印层对报告字段的摘要，不是新的模型计算。

它综合了：

- operator diagnosis，例如 `Inefficient Compute`
- dominant component，例如 `vector`
- dominant item，例如 `bf16`
- HIVM global root cause 和 bottleneck pipe

目的是把 report 里多个字段压缩成一个可操作的排查入口。真正的证据仍然是下面的 $U/R/E$、HIVM root cause 和 op-level diagnosis。

## 13. 这个方法的主要局限是什么？

**专家可能问：**

这个诊断方法有哪些边界？什么时候不能过度相信？

**推荐回答：**

主要局限有四点：

1. `op_summary` 只选一行作为 critical row，不是自动分析整张 profiling 表。
2. DES cycle 是模型时间，不等于真实 elapsed time。
3. `loop_multiplier` 和 weighted cycles 是 loop-scaled workload，不是 wall-clock 时间。
4. 结果依赖 DES graph 和 calibration 的口径一致性。如果 bytes、flops、elements、bandwidth 或 peak rate 口径不一致，$U/E$ 和 theoretical_min 都会受影响。

所以这个工具适合做“定位方向”和“解释证据链”，最终优化仍要结合真实 profiling、trace 和具体 kernel 代码验证。

## 14. 如果专家追问：为什么最终 diagnosis 和 HIVM root cause 不一致？

**专家可能问：**

比如 operator diagnosis 是 `Inefficient Compute`，但 HIVM root cause 是 `ComputeBound`，这是不是冲突？

**推荐回答：**

不冲突，因为两者回答的问题不同。

operator diagnosis 基于 profiling 的 $U/R/E$，回答真实执行里 component 是否达到 ideal performance。

HIVM root cause 基于 DES 结构时间线，回答模型里哪条 pipe 或哪类结构最主导。

所以可能出现：

- HIVM 看到 Vector 是主导 pipe，因此是 `ComputeBound`。
- 但 profiling 看到 Vector residency 高、efficiency 低，因此 operator diagnosis 是 `Inefficient Compute`。

这说明方向不是“换到 MTE 优化”，而是“Vector 确实是主导结构，但它没有高效执行”。这正是两个诊断层结合起来的价值。
