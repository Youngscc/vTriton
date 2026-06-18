# profile_utilization 瓶颈分析逻辑

本文档说明 `profile_utilization` 如何从 profiling 统计、DES work 信息和 calibration 峰值推导瓶颈结论。重点是分析逻辑和公式，不展开 Python 类、参数解析或 JSON 序列化等工程细节。

相关代码：

- [profile_utilization.py](../../../perfbound/analyze/profile_utilization.py)
- [component_model.py](../../../perfbound/model/component_model.py)
- [hivm_bottleneck_diagnosis.py](../../../perfbound/analyze/hivm_bottleneck_diagnosis.py)

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

## 基本符号

对每个 component `c`：

| 符号 | 含义 |
| --- | --- |
| $O_c$ | component `c` 的总 work |
| $O_{c,i}$ | component `c` 内第 `i` 类 work |
| $P_{c,i}$ | 第 `i` 类 work 对应的峰值吞吐或带宽 |
| $T$ | kernel 总耗时，也就是 `elapsed_time_us` |
| $T_{\mathrm{active},c}$ | component `c` 的 active time |
| $I_c$ | component `c` 的 operator-aware ideal performance |
| $A_c$ | component `c` 的 actual performance |
| $U_c$ | component `c` 的 utilization |
| $R_c$ | component `c` 的 residency |
| $E_c$ | component `c` 的 active-period efficiency |

component 分两组：

| 组别 | component | work 单位 |
| --- | --- | --- |
| Compute | `cube`、`vector`、`scalar` | ops / FLOPs / elements，需和峰值单位一致 |
| MTE | `mte_gm`、`mte_l1`、`mte_ub` | bytes |

默认阈值：

$$
u_{\mathrm{threshold}} = 0.80,\quad
r_{\mathrm{threshold}} = 0.50,\quad
\mathrm{work\_tolerance} = 0.10
$$

## 理论理想性能 I

同一个 component 可能混合多种 precision 或多条搬运路径。例如 Cube 里可能有 `fp16` 和 `bf16`，MTE 里可能同时有 `gm->ub` 和 `ub->gm`。

这时不能直接对峰值做算术平均，而要用按 work 加权的调和平均：

$$
I_c =
\frac{\sum_i O_{c,i}}
     {\sum_i \frac{O_{c,i}}{P_{c,i}}}
$$

直觉上，$\frac{O_{c,i}}{P_{c,i}}$ 是第 `i` 类 work 在理想硬件上至少需要的时间。所有理想时间加起来，再用总 work 除以总理想时间，就得到这个 component 面对当前算子 work mix 时的理想平均吞吐。

对 Compute：

$$
I_c =
\frac{\sum_i \mathrm{ops}_i}
     {\sum_i \frac{\mathrm{ops}_i}{\mathrm{peak\_ops\_per\_us}_i}}
$$

对 MTE：

$$
I_c =
\frac{\sum_i \mathrm{bytes}_i}
     {\sum_i \frac{\mathrm{bytes}_i}{\mathrm{bandwidth\_bytes\_per\_us}_i}}
$$

如果缺少细粒度 breakdown，代码会退回到 component floor 的结果：

$$
I_c = \frac{\mathrm{bound\_work}_c}{T_{\mathrm{ideal},c}}
$$

其中 $T_{\mathrm{ideal},c}$ 来自 component model：

$$
\begin{aligned}
T_{\mathrm{ideal},c} &= \frac{O_c}{I_c} \\
T_{\mathrm{core\_floor}} &= \max_c T_{\mathrm{ideal},c}
\end{aligned}
$$

$T_{\mathrm{core\_floor}}$ 只是理论吞吐下界，用来说明“最理想情况下至少要多久”。最终的利用率诊断仍然以真实 profiling 的 $T$ 和 $T_{\mathrm{active},c}$ 为分母。

## 实际指标 A / U / R / E

得到 `O_c`、`I_c`、`T`、`T_active,c` 后，每个 component 计算四个核心指标。

### Actual Performance

$$
A_c = \frac{O_c}{T}
$$

含义：把整个 kernel wall time 作为分母时，component `c` 实际交付的平均吞吐。

### Utilization

$$
U_c = \frac{A_c}{I_c}
$$

等价写法：

$$
U_c = \frac{O_c}{T \cdot I_c}
$$

含义：从整个 kernel 视角看，component `c` 达到了自身理想吞吐的多少比例。

$U_c$ 高说明这个 component 已经接近 ceiling。$U_c$ 低只说明没有接近 ceiling，但还不能判断原因，因为可能是这个 component 大部分时间都不活跃，也可能是活跃时效率很差。

### Residency

$$
R_c = \frac{T_{\mathrm{active},c}}{T}
$$

含义：component `c` 在 kernel 总时间中有多少比例处于 active 状态。

$R_c$ 低通常表示该 component 没有被充分喂满，或者它的工作被依赖、同步、调度间隙切碎。$R_c$ 高表示它确实占用了很多时间。

### Efficiency

$$
E_c = \frac{U_c}{R_c}
$$

等价写法：

$$
E_c = \frac{O_c}{T_{\mathrm{active},c} \cdot I_c}
$$

含义：只看 active 的那段时间，component `c` 的有效执行效率是多少。

这三个量的关系是：

$$
U_c = R_c \cdot E_c
$$

所以 $U$ 是最终结果，$R$ 和 $E$ 用来解释 $U$ 为什么高或低：

| 现象 | 解释 |
| --- | --- |
| $U$ 高 | 已接近 component ceiling |
| $U$ 低，$R$ 低 | 硬件没怎么忙，更像并行度不足或等待暴露 |
| $U$ 低，$R$ 高，$E$ 低 | 硬件忙了，但单位 active time 产出低 |

## 主导 item

每个 component 内部还会找一个主导 item：

$$
\begin{aligned}
\mathrm{dominant\_item}
  &= \arg\max_i O_{c,i} \\
\mathrm{dominant\_share}
  &= \frac{\max_i O_{c,i}}{\sum_i O_{c,i}}
\end{aligned}
$$

对 Compute，`dominant_item` 通常是 precision，例如 `bf16`、`fp16`、`fp32`、`int8`。

对 MTE，`dominant_item` 通常是 transfer path，例如 `gm->ub`、`gm->l1`、`l1->l0a`、`ub->gm`。

这个字段不直接决定大类诊断，但它告诉你优化应该优先看哪类 work。

## 瓶颈判定树

`profile_utilization` 只把满足下面条件的 component 当作有效 component：

$$
\mathrm{work\_done}_c > 0 \land I_c > 0
$$

没有有效 component 时，结论是：

```text
diagnosis = "Insufficient Data"
```

### 1. 先判断是否达到 ceiling

先找所有满足下面条件的 component：

$$
U_c \ge u_{\mathrm{threshold}}
$$

如果存在候选，选择 $U_c$ 最大的 component 作为主导 component。

如果主导 component 属于 Compute：

```text
diagnosis = "Compute Bound"
bound_kind = "Compute Bound"
```

如果主导 component 属于 MTE：

```text
diagnosis = "MTE Bound"
bound_kind = "MTE Bound"
```

这个分支的含义是：从实测 wall time 看，某个 component 已经接近它对当前 work mix 的理想吞吐，继续优化其他 component 不是第一优先级。

### 2. 再判断是否并行度不足

如果没有 component 达到 ceiling，就进入 underutilization 分析。

最基础的判断是：所有有效 component 的 residency 都低。

$$
\forall c \in C_{\mathrm{valid}},\quad R_c < r_{\mathrm{threshold}}
$$

这说明没有任何有实际 work 的 component 长时间占住硬件，因此诊断为：

```text
diagnosis = "Insufficient Parallelism"
bound_kind = null
```

这类结论通常指向：

- tile 数量或 pipeline depth 不足。
- compute 和 MTE 没有充分 overlap。
- 依赖链太串行。
- 同步、控制或调度间隙暴露在关键路径上。

### 3. 处理暴露的控制/同步

代码对 Ascend 场景做了一个补充判断：如果某个 component 有很高 $R$，但几乎没有算术或搬运 work，它可能不是“低效率计算”，而是暴露的控制或同步开销。

判断形式：

$$
R_c \ge r_{\mathrm{threshold}} \land \mathrm{work\_done}_c \le 0
$$

如果这种 exposed control/sync 的 residency 不低于有效 work component 的最高 residency，也归为：

```text
diagnosis = "Insufficient Parallelism"
```

这里的逻辑是：控制或同步本身不产生 ops/bytes，把它归为 Inefficient Compute 会误导优化方向。真正的问题是控制路径没有被 compute/memory overlap 掩盖。

### 4. 最后判断低效率 component

如果没有达到 ceiling，也不是整体并行度不足，就说明至少有一个有效 component 驻留较高，但最终 $U$ 仍然低。

候选 component：

$$
R_c \ge r_{\mathrm{threshold}}
$$

每个候选的低效率得分：

$$
\mathrm{score}_c = R_c \cdot \max(0, 1 - E_c)
$$

这个分数可以理解为“暴露出来的低效活跃时间”。$R_c$ 越高，说明占用总时间越多；$1 - E_c$ 越高，说明 active 期间浪费越多。

选择 $\mathrm{score}_c$ 最大的 component。

如果它属于 Compute：

```text
diagnosis = "Inefficient Compute"
```

如果它属于 MTE：

```text
diagnosis = "Inefficient MTE"
```

这类结论的含义不是“这个 component 时间最长”，而是“这个 component 驻留足够高，但 active 期间没有把峰值能力转化成有效 work”。

## 暴露控制/同步赤字

当最终结论是 `Insufficient Parallelism`，且主导 locus 是 Scalar 控制路径时，代码会额外量化“模型认为可暴露的控制比例”和“硬件实测 scalar 占比”之间的差距。

首先用 DES 时间线计算模型暴露比例：

$$
\begin{aligned}
\mathrm{critical\_path\_cycles}
  &= \max_j(\mathrm{end\_cycle}_j) \\
\mathrm{model\_exposed\_frac}
  &= \frac{
       \operatorname{cycles}(\text{control\_sync active}
       \land \neg \text{compute active}
       \land \neg \text{memory active})
     }{\mathrm{critical\_path\_cycles}}
\end{aligned}
$$

然后从 profiling 里计算实测比例：

$$
\mathrm{measured\_frac}
  = \frac{\mathrm{aiv\_scalar\_time}}{\mathrm{aiv\_time}}
$$

赤字：

$$
\mathrm{deficit\_pts}
  = \mathrm{measured\_frac} - \mathrm{model\_exposed\_frac}
$$

如果调用方提供了更可信的 tight bound `t_bound_us`，还可以把赤字估成时间，并封顶到可解释的 headroom：

$$
\begin{aligned}
\mathrm{author\_headroom\_us}
  &= \mathrm{elapsed\_time\_us} - \mathrm{t\_bound\_us} \\
\mathrm{raw\_deficit\_us}
  &= \max(0, \mathrm{deficit\_pts}) \cdot \mathrm{elapsed\_time\_us} \\
\mathrm{deficit\_us}
  &= \min(\mathrm{raw\_deficit\_us}, \mathrm{author\_headroom\_us})
\end{aligned}
$$

这些字段只用于诊断解释，不会反过来改变 `U/R/E` 或最终 bound。

## HIVM 结构诊断如何补充解释

`profile_utilization` 的顶层 `diagnosis` 是 profiling 驱动的算子级结论。报告里的 `hivm_bottleneck` 则是 DES 时间线驱动的结构级解释。

两者关注点不同：

| 层次 | 主要分母 | 回答的问题 |
| --- | --- | --- |
| profile utilization | 实测 `elapsed_time_us` 和 active time | 真实执行中是否达到 ceiling，低利用率来自低驻留还是低效率 |
| HIVM bottleneck | DES cycle timeline | 模型时间线里哪个 pipe、sync 或 op 最像结构瓶颈 |

HIVM 结构诊断先从 DES graph 里的 op 时间线做汇总。下面用 $j$ 表示一个 DES op，用 $p$ 表示一条 pipe。

每个 op 需要理解这些基础量：

| 变量 | 含义 |
| --- | --- |
| $\mathrm{duration}_j$ | op $j$ 在 DES 模型里的执行时长，单位是 cycle，对应 JSON 里的 `duration` |
| $\mathrm{start\_cycle}_j$ | op $j$ 的调度开始 cycle |
| $\mathrm{end\_cycle}_j$ | op $j$ 的调度结束 cycle |
| $\mathrm{pipe}_j$ | op $j$ 所属 pipe，例如 `Cube`、`Vector`、`MTE3`、`All` |
| $\mathrm{loop\_multiplier}_j$ | op $j$ 的循环放大倍数；代码里会取至少 1 |
| $\mathrm{is\_sync}_j$ | op $j$ 是否同步/控制类 op |
| $\mathrm{is\_barrier}_j$ | op $j$ 是否 barrier |
| $\mathcal{P}_{\mathrm{valid}}$ | 正常硬件 pipe 集合，不包含 `All`、`PIPE_ALL`、`Unknown`、`PIPE_UNKNOWN` |
| $\mathcal{G}$ | 全局 barrier op 集合，也就是 `is_barrier=true` 且 pipe 是 `All` 或 `PIPE_ALL` 的 op |

### 时间线长度

$$
\mathrm{one\_iteration\_cycles}
  = \max_j(\mathrm{end\_cycle}_j)
$$

`one_iteration_cycles` 表示 DES 时间线里一轮调度的关键路径长度。它不是所有 op duration 的求和，而是最后结束的 op 的 `end_cycle`。

如果多个 pipe 并行工作，所有 op 的 duration 加起来可能大于 `one_iteration_cycles`。所以这个量更像“模型里一轮 kernel 经过了多少 cycle”，后面的同步比例和 pipe 利用率都用它做分母。

### Pipe busy cycles

$$
\mathrm{pipe\_busy\_cycles}_p
  = \sum_{j:\ \mathrm{pipe}_j=p} \mathrm{duration}_j,
  \quad p \in \mathcal{P}_{\mathrm{valid}}
$$

`pipe_busy_cycles[p]` 表示 pipe $p$ 在这一轮 DES 时间线里累计忙了多少 cycle。这里排除了 `All` 和 `Unknown`，因为它们不是具体执行 pipe。

这个量用于回答：

- 哪条 pipe 在单轮时间线里最忙。
- 某条 pipe 的忙碌时间占关键路径比例是多少。
- pipe 间是否出现“一条 pipe 很忙，另一条 pipe 几乎空闲”的不均衡。

对应的 pipe 利用率是：

$$
\mathrm{pipe\_utilization}_p
  = \frac{\mathrm{pipe\_busy\_cycles}_p}
         {\mathrm{one\_iteration\_cycles}}
    \cdot 100\%
$$

这里的 utilization 是 DES 模型时间线里的 pipe busy ratio，不是前面 profiling 利用率里的 $U_c$。前者用 cycle timeline 解释结构瓶颈，后者用实测 elapsed time 和理想吞吐解释真实性能。

### Weighted pipe cycles

$$
\mathrm{weighted\_pipe\_cycles}_p
  = \sum_{j:\ \mathrm{pipe}_j=p}
     \mathrm{duration}_j \cdot \mathrm{loop\_multiplier}_j,
  \quad p \in \mathcal{P}_{\mathrm{valid}}
$$

`weighted_pipe_cycles[p]` 在 `pipe_busy_cycles[p]` 的基础上乘了 `loop_multiplier`。它不是一轮真实时间线长度，而是把循环内重复执行的工作量放大后，用来比较各 pipe 的累计负载。

直觉上：

- `pipe_busy_cycles[p]` 更像“一轮调度里 pipe $p$ 忙了多久”。
- `weighted_pipe_cycles[p]` 更像“考虑循环次数后，pipe $p$ 承担了多少总工作”。

HIVM 结构诊断用 `weighted_pipe_cycles` 来找主导 pipe，因为循环体内重复的小 op 如果只看单轮 duration，可能低估它对总执行的影响。

### Sync 和 barrier ratio

先定义同步和 barrier 的累计 cycle：

$$
\begin{aligned}
\mathrm{sync\_cycles}
  &= \sum_{j:\ \mathrm{is\_sync}_j} \mathrm{duration}_j \\
\mathrm{barrier\_cycles}
  &= \sum_{j:\ \mathrm{is\_barrier}_j} \mathrm{duration}_j
\end{aligned}
$$

然后归一化到一轮关键路径：

$$
\begin{aligned}
\mathrm{sync\_ratio}
  &= \frac{\mathrm{sync\_cycles}}{\mathrm{one\_iteration\_cycles}} \cdot 100\% \\
\mathrm{barrier\_ratio}
  &= \frac{\mathrm{barrier\_cycles}}{\mathrm{one\_iteration\_cycles}} \cdot 100\%
\end{aligned}
$$

`sync_ratio` 表示同步/控制类 op 的累计 duration 相对 DES 关键路径的比例。`barrier_ratio` 是其中 barrier 的累计 duration 比例。这里的分子是 duration 求和，不是对时间线做去重后的 wall-time 区间；如果多个 sync op 在不同 pipe 上重叠，比例可能会偏向“累计忙碌量”的解释。二者越高，说明模型认为等待、barrier 或控制调度在时间线上暴露得越明显。

代码里的全局 root cause 会优先检查这两个比例：

$$
\mathrm{sync\_ratio} > 20\%
\quad \lor \quad
\mathrm{barrier\_ratio} > 15\%
$$

满足时直接诊断为 `SyncOverhead`。也就是说，只要同步或 barrier 已经占了足够高比例，就先认为它是全局结构瓶颈，而不是再去比较 compute/memory pipe。

### Weighted cycles

$$
\mathrm{weighted\_cycles}
  = \max_p(\mathrm{weighted\_pipe\_cycles}_p)
    + \mathrm{weighted\_global\_barrier\_cycles}
$$

其中：

$$
\mathrm{weighted\_global\_barrier\_cycles}
  = \sum_{j \in \mathcal{G}}
    \mathrm{duration}_j \cdot \mathrm{loop\_multiplier}_j
$$

`weighted_cycles` 是一个近似的“主导结构成本”：

- 第一项 $\max_p(\mathrm{weighted\_pipe\_cycles}_p)$ 代表正常 pipe 中最重的那条 pipe。
- 第二项 $\mathrm{weighted\_global\_barrier\_cycles}$ 代表全局 barrier 成本，因为全局 barrier 不属于某一条普通 pipe，但会影响所有 pipe 的推进。

如果没有任何有效 pipe 的 weighted cycle，代码会退回用 `one_iteration_cycles` 作为 `weighted_cycles`，避免输出完全为 0 的结构诊断。

### Pipeline imbalance ratio

pipeline imbalance 用最大和最小正数 weighted pipe cycles 比较：

$$
\mathrm{imbalance\_ratio}
  = \frac{
      \max_p(\mathrm{weighted\_pipe\_cycles}_p)
    }{
      \min_{p:\ \mathrm{weighted\_pipe\_cycles}_p>0}
      (\mathrm{weighted\_pipe\_cycles}_p)
    }
$$

这里分子是最重 pipe 的 loop-scaled 工作量，分母是最轻但非零 pipe 的 loop-scaled 工作量。

例如：

```text
weighted_pipe_cycles = {
  "Cube": 240,
  "MTE1": 30,
  "Vector": 40
}
```

则：

$$
\mathrm{imbalance\_ratio}
  = \frac{240}{30} = 8.0
$$

含义是：最重的 `Cube` pipe 比最轻的有效 pipe `MTE1` 多承担了 8 倍 loop-scaled 工作。代码中如果：

$$
\mathrm{imbalance\_ratio} > 3.0
$$

就诊断为 `PipelineImbalance`。这表示 DES 模型看到某条 pipe 明显主导，其他 pipe 没有被均衡利用。

还有一个辅助的不均衡判断，它不看 loop multiplier，而是看单轮 pipe busy ratio：

$$
\max_p(\mathrm{pipe\_utilization}_p) > 60\%
\quad \land \quad
0 < \min_p(\mathrm{pipe\_utilization}_p) < 20\%
$$

它表达的是：有一条 pipe 在单轮时间线里很忙，同时另一条有效 pipe 很空。即使 weighted ratio 没超过 3，也可以认为 pipeline 没有被均衡填满。

主要规则：

| 条件 | HIVM root cause |
| --- | --- |
| $\mathrm{sync\_ratio} > 20\%$ 或 $\mathrm{barrier\_ratio} > 15\%$ | `SyncOverhead` |
| $\mathrm{imbalance\_ratio} > 3.0$ | `PipelineImbalance` |
| $\max_p(\mathrm{pipe\_utilization}_p) > 60\%$ 且 $\min_{p:\ \mathrm{pipe\_utilization}_p>0}(\mathrm{pipe\_utilization}_p) < 20\%$ | `PipelineImbalance` |
| 最大 weighted pipe 是 memory pipe | `BandwidthBound` |
| 最大 weighted pipe 是 compute pipe | `ComputeBound` |

这些规则有优先级：

1. 先看 sync/barrier 是否过高，过高就是 `SyncOverhead`。
2. 再看 pipeline 是否明显不均衡，明显不均衡就是 `PipelineImbalance`。
3. 如果没有同步瓶颈和严重不均衡，再看 weighted cycles 最大的 pipe 属于 memory 还是 compute。

memory pipe 包括 `MTE2`、`MTE3` 这类数据搬运 pipe；compute pipe 包括 `Cube` 和 `Vector`。因此：

- 最大 weighted pipe 是 memory pipe 时，结构诊断为 `BandwidthBound`。
- 最大 weighted pipe 是 compute pipe 时，结构诊断为 `ComputeBound`。

### Op 级诊断

除了全局 root cause，`hivm_bottleneck` 还会对每个耗时 op 给一个局部诊断。op 级诊断首先会估一个 `theoretical_min_cycles`，再和 DES 里的实际 duration 做对比。

先定义几个校准量：

| 变量 | 含义 |
| --- | --- |
| $S_p$ | pipe $p$ 的 startup latency，单位 cycle，来自 calibration，缺失时使用 fallback |
| $B_{\mathrm{path}}^{\mathrm{cycle}}$ | 某条内存路径的带宽，单位 bytes/cycle |
| $R_{\mathrm{compute}}^{\mathrm{cycle}}$ | 某个 compute pipe 和 precision 的吞吐，单位 ops/cycle 或 FLOPs/cycle |
| $W_{\mathrm{vec}}$ | vector 每条指令能覆盖的元素数，代码中近似为 `vec_width_bytes / 4` |
| $W_{\mathrm{bytes}}$ | vector/fixpipe 一次处理的字节宽度，代码中使用 `vec_width_bytes` |

如果 calibration 中带宽或吞吐是按 microsecond 给出的，代码会除以 `cycles_per_us` 转成 cycle 口径：

$$
\begin{aligned}
B_{\mathrm{path}}^{\mathrm{cycle}}
  &= \frac{B_{\mathrm{path}}^{\mathrm{us}}}{\mathrm{cycles\_per\_us}} \\
R_{\mathrm{compute}}^{\mathrm{cycle}}
  &= \frac{R_{\mathrm{compute}}^{\mathrm{us}}}{\mathrm{cycles\_per\_us}}
\end{aligned}
$$

不同 pipe 的理论最小 cycle 估计方式不同：

| op 类型 | 理论最小 cycle |
| --- | --- |
| MTE transfer pipe，例如 `MTE2` / `MTE3` | $\left\lceil \frac{\mathrm{bytes}_j}{B_{\mathrm{path}}^{\mathrm{cycle}}} \right\rceil$ |
| Vector compute | $S_{\mathrm{Vector}} + \left\lceil \frac{\mathrm{elements}_j}{W_{\mathrm{vec}}} \right\rceil$ |
| Cube compute | $S_{\mathrm{Cube}} + \left\lceil \frac{\mathrm{flops}_j}{R_{\mathrm{compute}}^{\mathrm{cycle}}} \right\rceil$ |
| FixPipe | $S_{\mathrm{FixPipe}} + \left\lceil \frac{\mathrm{bytes}_j}{W_{\mathrm{bytes}}} \right\rceil$ |
| MTE1 或未知 pipe | 直接回退为 $\mathrm{duration}_j$ |
| 没有 bytes/elements work 的 op | 记为 $0$ |

这里的 `theoretical_min_cycles` 是一个诊断用下界，不是重新调度结果。它只回答：“如果只看这个 op 的数据量/计算量和校准峰值，至少应该需要多少 cycle？”

然后用下面的公式计算 op 的相对开销：

$$
\mathrm{overhead\_ratio}
  = \frac{
      \mathrm{actual\_cycles} - \mathrm{theoretical\_min\_cycles}
    }{
      \mathrm{actual\_cycles}
    }
$$

其中：

| 变量 | 含义 |
| --- | --- |
| $\mathrm{actual\_cycles}$ | DES graph 中该 op 的 `duration` |
| $\mathrm{theoretical\_min\_cycles}$ | 根据 calibration、bytes、elements、flops 等估算的理论最小 cycle |
| $\mathrm{overhead\_ratio}$ | 实际 duration 中有多少比例不能被理论最小成本解释 |

如果 $\mathrm{overhead\_ratio} > 0$，说明 DES duration 比理论最小 cycle 更大，多出来的部分可理解为启动、等待、控制或低效开销。如果它接近 0，说明该 op 的 modeled duration 基本被理论最小 work 解释。如果它是负数，通常表示 demo/fake 数据或校准口径不一致，因为“理论最小值”反而比 DES duration 更大。

局部诊断还会用到 startup latency：

$$
\mathrm{work\_cycles}_j
  = \mathrm{duration}_j - \mathrm{startup\_latency}_{\mathrm{pipe}_j}
$$

这个式子不是新的耗时估计，而是把 DES duration 粗略拆成：

$$
\mathrm{duration}_j
  \approx \mathrm{startup\_latency}_{\mathrm{pipe}_j}
  + \mathrm{work\_cycles}_j
$$

于是不同 op 的判断方式是：

常见 op 级 root cause：

| 条件 | op root cause |
| --- | --- |
| sync 或 barrier op | `SyncOverhead` |
| MTE op 满足 $\mathrm{startup\_latency} > \mathrm{work\_cycles}$，或 $\mathrm{work\_cycles} \le 0$ | `StartupOverhead` |
| MTE op 不满足 startup 主导，且有正数 bytes | `BandwidthBound` |
| Compute op 满足 $\mathrm{startup\_latency} > \mathrm{work\_cycles}$ 且 $\mathrm{work\_cycles} > 0$ | `StartupOverhead` |
| Compute op 不满足 startup 主导 | `ComputeBound` |

对 MTE 来说，`StartupOverhead` 通常意味着单次搬运太小，启动成本摊不薄；`BandwidthBound` 则表示数据搬运本身主导 duration。对 Compute 来说，`StartupOverhead` 通常意味着 tile 太小或指令启动成本占比高；`ComputeBound` 表示计算 work 本身主导 duration。

因此，当顶层 `diagnosis` 和 `hivm_bottleneck.global_root_cause` 不完全一致时，不一定矛盾。前者来自实测利用率，后者来自模型结构。通常可以这样读：

- 顶层 `Compute Bound`，HIVM 也是 `ComputeBound`：实测和模型都指向计算 ceiling。
- 顶层 `Inefficient MTE`，HIVM 是 `BandwidthBound`：MTE 确实是结构主导，但实测带宽没有达到理想值，需看对齐、burst、packet size、tile 粒度。
- 顶层 `Insufficient Parallelism`，HIVM 是 `PipelineImbalance`：实测上没有 component 被持续喂满，模型结构上也看到 pipe 负载不均。
- 顶层利用率不高，但 HIVM 是 `SyncOverhead`：同步或 barrier 在 DES 关键路径上占比高，优先看 wait/barrier 是否能被 overlap 或替换为更细粒度同步。

## 诊断结论速查

| 结论 | 公式特征 | 优先排查方向 |
| --- | --- | --- |
| `Compute Bound` | 某个 Compute component 的 $U_c \ge u_{\mathrm{threshold}}$ | 减少计算量、调整精度、提升 arithmetic intensity、优化 tile 形状 |
| `MTE Bound` | 某个 MTE component 的 $U_c \ge u_{\mathrm{threshold}}$ | 减少 bytes、增加片上复用、改善搬运与计算 overlap |
| `Insufficient Parallelism` | 没有达到 ceiling，且有效 component 的 $R_c$ 普遍低，或控制/同步高驻留无 work | 增加 pipeline depth、多 buffer、并行 tile 数，减少暴露同步 |
| `Inefficient Compute` | 没有达到 ceiling，Compute component 高 $R_c$ 低 $E_c$ | 检查指令形态、mask/repeat、tile 是否过小、startup 是否被摊薄 |
| `Inefficient MTE` | 没有达到 ceiling，MTE component 高 $R_c$ 低 $E_c$ | 检查传输路径、对齐、burst/packet size、合并小搬运 |
| `Insufficient Data` | 没有有效 component | 补齐 work、active time、calibration 或检查单位 |

## 读数时的注意点

- $U$ 和 $E$ 大于 $1.05$ 通常不物理，优先检查单位、work 口径或 calibration。
- `active_time_us > elapsed_time_us` 通常表示 profiling 字段口径不一致，或错误地累加了并发 core 的时间。
- `work_done` 和 `bound_work` 相差超过 `work_tolerance` 时，说明 DES work 和 component model work 口径不一致。
- `schedule_truncated = true` 的 DES graph 不适合做可靠 bound 或结构诊断。
- Compute 的 work 必须和峰值单位对齐。如果峰值是 FLOP/us，work 最好也是 FLOPs；如果暂时用 elements，需要明确这是近似口径。
