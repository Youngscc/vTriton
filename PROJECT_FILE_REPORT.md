# 项目文件用途报告

范围：仅覆盖主仓库文件。已忽略 `thirdparty/`、`build/`、虚拟环境、IDE 文件、git 元数据，以及硬件/环境配置 JSON 文件。

## 顶层文件

- `README.md`：主使用文档，介绍项目用途、构建步骤、常用命令、Triton/HIVM 工作流和 trace 输出。
- `BUILD.md`：本地构建说明和依赖准备笔记。
- `DEPENDENCIES.md`：外部依赖说明，以及为什么需要这些依赖。
- `PROGRESS.md`：开发进度记录和当前功能状态。
- `AGENTS.md`：给代码代理使用的仓库级说明。
- `CLAUDE.md`：给 Claude 类代理使用的工作说明。
- `CMakeLists.txt`：顶层 CMake 构建入口。负责查找 LLVM/MLIR，启用可选 Triton 和 BiShengIR 集成，并加入库和工具目标。

## 构建与补丁脚本

- `scripts/build_llvm.sh`：构建指定版本的 LLVM/MLIR，并安装到 `thirdparty/llvm-project/build/install`。
- `scripts/validate_shared_llvm.sh`：检查 LLVM/MLIR 安装目录是否包含预期的 CMake 包和共享构建信息。
- `scripts/apply_patches.sh`：把本仓库维护的本地补丁应用到 `thirdparty/triton-ascend` 及其内部 AscendNPU-IR。
- `scripts/hivm_des_sim.py`：用于 HIVM DES 风格调度实验的 Python 模拟/辅助脚本。
- `patches/triton-ascend-compile-only-mock.patch`：让 `triton-ascend` 在 compile-only 模式下绕过真实 NPU runtime 调用。
- `patches/ascendnpu-ir-llvm20-compat.patch`：为 AscendNPU-IR 适配较新 LLVM API 的本地补丁。
- `patches/triton-ascend-llvm20-compat.patch`：历史 Triton LLVM API 兼容补丁；当前 LLVM pin 下不适用。

## 公共头文件

- `include/AscendModel/CMakeLists.txt`：头文件和 TableGen 相关的 CMake 集成。
- `include/AscendModel/Utils.h`：常用 AscendModel 工具头文件的聚合入口。
- `include/AscendModel/HardwareConfig.h`：硬件配置 API 的公共头文件入口。
- `include/AscendModel/HardewareConfig.h`：拼写错误的兼容头文件，可能用于兼容旧 include。
- `include/AscendModel/HardwareParams.h.in`：CMake 生成硬件参数头文件时使用的模板。
- `include/AscendModel/Analysis/HardwareConfig.h`：硬件模型声明，包括计算单元、存储空间、带宽、频率和校准参数。
- `include/AscendModel/Analysis/Utils.h`：共享 MLIR 分析工具，包括 shape、循环 trip count、参数绑定和值追踪。
- `include/AscendModel/Analysis/PipelineAnalysis.h`：Cube/Vector/MTE 并行重叠分析所需的 pipeline 调度器和报告结构。
- `include/AscendModel/Analysis/HIVMAnalysis.h`：HIVM 原生调度、报告和 Perfetto trace 输出接口。
- `include/AscendModel/Analysis/MemoryTilingOptimizer.h`：tiling 搜索和内存代价模型声明。
- `include/AscendModel/Analysis/UnifiedTilingCostModel.h`：统一的单 op / 融合 op tiling 代价抽象。
- `include/AscendModel/IR/AscendModelBase.td`：自定义 AscendModel dialect 的 TableGen 基础定义。
- `include/AscendModel/IR/AscendModelOps.td`：`ascend.matmul`、load、store、vector op 等自定义操作定义。
- `include/AscendModel/IR/AscendModelInterfaces.td`：操作接口的 TableGen 定义。
- `include/AscendModel/IR/AscendModelDialect.h`：AscendModel dialect 的 C++ 声明头文件。
- `include/AscendModel/IR/AscendModelInterfaces.h`：生成接口的 C++ include 包装头。
- `include/AscendModel/Transforms/Passes.td`：pass 的 TableGen 声明及命令行选项定义。
- `include/AscendModel/Transforms/Passes.h`：注册和创建 AscendModel passes 的 C++ 声明。

## C++ 库实现

- `lib/CMakeLists.txt`：加入 `AscendModel` 库子目录。
- `lib/AscendModel/CMakeLists.txt`：组织 IR、analysis 和 transforms 三类库目标。
- `lib/AscendModel/IR/CMakeLists.txt`：构建 AscendModel dialect IR 库。
- `lib/AscendModel/IR/AscendModelDialect.cpp`：向 MLIR 注册 AscendModel dialect。
- `lib/AscendModel/IR/AscendModelOps.cpp`：实现自定义 `ascend.*` 操作的解析、打印、验证或辅助逻辑。
- `lib/AscendModel/Analysis/CMakeLists.txt`：构建 analysis 相关库对象。
- `lib/AscendModel/Analysis/HardwareConfig.cpp`：从 JSON 或默认值加载硬件参数，并提供硬件单元/存储空间属性查询。
- `lib/AscendModel/Analysis/PipelineAnalysis.cpp`：把 op 调度到不同硬件单元，计算重叠、利用率和 timeline。
- `lib/AscendModel/Analysis/HIVMAnalysis.cpp`：解析/分析 HIVM IR 文本或原生 op，建模同步、pipe 和调度，并输出报告/trace。
- `lib/AscendModel/Analysis/RooflineAnalysis.cpp`：计算 roofline 指标、利用率总结和 JSON 风格性能数据。
- `lib/AscendModel/Analysis/MemoryTilingOptimizer.cpp`：搜索 tiling 方案并估算内存搬运代价。
- `lib/AscendModel/Analysis/UnifiedTilingCostModel.cpp`：实现可复用的 tiling 代价和融合代价计算。

## Transform Passes

- `lib/AscendModel/Transforms/CMakeLists.txt`：构建 transform pass 库。
- `lib/AscendModel/Transforms/PassRegistration.cpp`：注册单个 pass 和 `-ascend-perf-model` 组合 pipeline。
- `lib/AscendModel/Transforms/AssignOpIDs.cpp`：给操作添加稳定的 `op_id`，用于报告和 timeline 对齐。
- `lib/AscendModel/Transforms/EstimateCycles.cpp`：基于硬件配置估算每个操作的 cycles、FLOPs 和 bytes。
- `lib/AscendModel/Transforms/PipelineAnalysisPass.cpp`：运行 pipeline 调度分析，并写出 `pipeline_trace.json` / `pipeline_dep_graph.json`。
- `lib/AscendModel/Transforms/PerfReportPass.cpp`：输出面向人的时间、roofline、内存和瓶颈总结。
- `lib/AscendModel/Transforms/ConvertTritonToAscend.cpp`：把支持的 Triton dialect op 转换为自定义 `ascend.*` 建模 op。
- `lib/AscendModel/Transforms/InsertDataTransfers.cpp`：在计算路径周围插入显式数据搬运 op。
- `lib/AscendModel/Transforms/TilingOptimizationPass.cpp`：执行 tiling 优化搜索，并标注/报告选择的 tiling。
- `lib/AscendModel/Transforms/ExtractTTIRInfo.cpp`：从 TTIR 中提取结构化元数据，以 JSON 输出给 Python/perfbound 流程使用。
- `lib/AscendModel/Transforms/HIVMAnalysisPass.cpp`：HIVM 调度分析的 MLIR pass 包装器，支持可选 trace/report 文件。

## 命令行工具

- `tools/CMakeLists.txt`：定义命令行工具目标。
- `tools/tritonsim-opt/tritonsim-opt.cpp`：类似 MLIR opt 的驱动程序，用于运行 AscendModel passes 和 Triton-to-Ascend 分析。
- `tools/tritonsim-hivm/tritonsim-hivm.cpp`：独立 HIVM/NPU-IR 分析器，支持报告、DES 调度器和 Perfetto trace。
- `tools/common/triton_dsl_dump_launcher.py`：以 compile-only 模式运行 Triton Python 脚本，捕获导出的 HIVM/IR 和元数据。

## 测试与样例输入

- `test/ascend_ops.mlir`：基础 AscendModel dialect 样例，包含 matmul、vector 和 softmax。
- `test/softmax_ascend.mlir`：专门的 softmax 风格 AscendModel MLIR 样例。
- `test/layernorm_ascend.mlir`：LayerNorm 风格 AscendModel MLIR 样例，用于 pipeline/perf 报告。
- `test/hivm_add_kernel.npuir.mlir`：最小 HIVM 风格 vector add 样例。
- `test/hivm_mixed_cv_kernel.npuir.mlir`：合成的 Cube/Vector 混合 HIVM 样例。
- `test/flash_attention.ttir`：flash-attention 风格的 Triton TTIR 样例。
- `test/persistent_1.ttir`：persistent kernel TTIR 样例。
- `test/persistent_21.ttir`：更大或不同形态的 persistent kernel TTIR 样例。
- `test/triton_smoke.py`：Triton DSL ingestion / dump 路径的 smoke test。
- `test/triton_hivm_launch_smoke.py`：运行 Triton DSL 并捕获 HIVM 输出的 smoke test。
- `tests/perfbound/conftest.py`：`perfbound` pytest 的共享 fixture。
- `tests/perfbound/test_mlir_parser.py`：测试通用 MLIR 解析和提取逻辑。
- `tests/perfbound/test_dsl_extractor.py`：测试 Triton DSL 元数据提取。
- `tests/perfbound/test_grid_idioms.py`：测试 grid / program_id 惯用模式识别。
- `tests/perfbound/test_component_model.py`：测试组件级性能模型行为。
- `tests/perfbound/test_calibration_load.py`：测试校准数据加载。
- `tests/perfbound/test_calibration_wiring.py`：测试校准数据接入模型代码的路径。
- `tests/perfbound/test_calibration_extraction.py`：测试校准常量提取。
- `tests/perfbound/test_microbench_sources.py`：检查 microbenchmark 源文件是否存在以及结构是否符合预期。

## Perfbound Python 包

- `perfbound/__init__.py`：Python 包标记。
- `perfbound/calibration/__init__.py`：calibration 子包标记。
- `perfbound/calibration/constants.py`：定义 Python 模型使用的校准常量和默认值。
- `perfbound/calibration/calib_loader.py`：从打包的 CSV/JSON 文件加载带宽和 cycle 校准数据。
- `perfbound/data/bandwidth_910b3.csv`：910B3 建模使用的打包带宽参考数据。
- `perfbound/calibration/data/bandwidth_910b3.csv`：带宽校准测量数据。
- `perfbound/calibration/data/vec_cycle_910b3.csv`：vector cycle 校准测量数据。
- `perfbound/calibration/bench_output/*.csv`：Cube、Vector、MTE 和 handoff microbenchmark 的原始或处理后结果表。
- `perfbound/extract/__init__.py`：extract 子包标记。
- `perfbound/extract/mlir_parser.py`：Python 模型使用的轻量 MLIR 文本解析器。
- `perfbound/extract/dsl_extractor.py`：从 Triton DSL/TTIR 流程中提取建模所需信息。
- `perfbound/extract/hivm_extractor.py`：从 HIVM 文本中提取操作、内存和同步信息。
- `perfbound/extract/grid_idioms.py`：识别 program_id / grid 映射惯用模式。
- `perfbound/extract/op_classifier.py`：把操作分类为计算、内存或控制类。
- `perfbound/extract/eligibility_oracle.py`：判断输入是否适合某个 perfbound 模型。
- `perfbound/model/__init__.py`：model 子包标记。
- `perfbound/model/bandwidth.py`：带宽模型辅助函数。
- `perfbound/model/component_model.py`：组合计算、内存和同步组件的性能模型。
- `perfbound/model/grid_model.py`：grid/block 级别扩展和 launch shape 模型。
- `perfbound/model/serialization.py`：模型输入/输出的序列化辅助函数。
- `perfbound/combine/__init__.py`：combine 子包标记。
- `perfbound/combine/two_limit.py`：把两个限制资源合成为整体 bound。
- `perfbound/combine/bound_combiner.py`：通用 bound 组合逻辑。
- `perfbound/combine/report.py`：把 Python perfbound 模型结果格式化为报告。
- `perfbound/validate/__init__.py`：validate 子包标记。
- `perfbound/validate/harness.py`：用于比较模型预测和测量结果的验证框架。
- `perfbound/validate/counterfactual.py`：基于模型参数或 kernel 特征做反事实实验。

## 校准 Microbenchmarks

- `perfbound/calibration/microbench/README.md`：说明校准 microbenchmark 的目的和用法。
- `perfbound/calibration/microbench/CMakeLists.txt`：构建 CCE microbenchmark launcher 相关目标。
- `perfbound/calibration/microbench/bench_launcher.cpp`：CCE microbenchmark 的 host 侧 launcher。
- `perfbound/calibration/microbench/vt_microbench_common.h`：CCE microbenchmark 共用辅助定义。
- `perfbound/calibration/microbench/cube_peak_fp16.cce`：测量 Cube FP16 峰值吞吐。
- `perfbound/calibration/microbench/cube_peak_bf16.cce`：测量 Cube BF16 峰值吞吐。
- `perfbound/calibration/microbench/cube_peak_int8.cce`：测量 Cube INT8 峰值吞吐。
- `perfbound/calibration/microbench/vector_peak_elemwise_add.cce`：测量 vector add 吞吐。
- `perfbound/calibration/microbench/vector_peak_elemwise_mul.cce`：测量 vector multiply 吞吐。
- `perfbound/calibration/microbench/vector_peak_elemwise_min.cce`：测量 vector min 吞吐。
- `perfbound/calibration/microbench/vector_peak_elemwise_max.cce`：测量 vector max 吞吐。
- `perfbound/calibration/microbench/vector_peak_transcendental.cce`：测量 vector 超越函数类操作吞吐。
- `perfbound/calibration/microbench/mte_gm_to_l1.cce`：测量 GM 到 L1 的搬运带宽。
- `perfbound/calibration/microbench/mte_gm_to_ub.cce`：测量 GM 到 UB 的搬运带宽。
- `perfbound/calibration/microbench/mte_l1_to_l0a.cce`：测量 L1 到 L0A 的搬运带宽。
- `perfbound/calibration/microbench/mte_ub_to_gm.cce`：测量 UB 到 GM 的搬运带宽。
- `perfbound/calibration/microbench/mandatory_handoff.cce`：测量 pipeline 阶段间同步/handoff 开销。
- `perfbound/calibration/scripts/__init__.py`：calibration scripts 包标记。
- `perfbound/calibration/scripts/run_benchmarks.sh`：运行校准 microbenchmark 的 shell 包装脚本。
- `perfbound/calibration/scripts/cce_remote_bench.py`：远程编译/运行 CCE kernel 的 benchmark 驱动。
- `perfbound/calibration/scripts/fit_constants.py`：从 benchmark 结果拟合校准常量。
- `perfbound/calibration/scripts/validate_vs_tilesim.py`：把校准模型结果和 TileSim/测量基线对比。

## 配置文档

- `configs/README.md`：说明硬件配置 JSON 的 schema 和可用硬件配置文件。实际 JSON 配置属于环境/模型数据，此处不展开。
