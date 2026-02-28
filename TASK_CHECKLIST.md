# DMFB + LLM 项目任务清单

> 基于已有框架，完成项目所需的全部任务

---

## Phase 1: Baseline 完善与数据准备（第1-4周）

### Week 1: 外部工具调研与接入

#### 任务 1.1: 调研可用外部工具 ✅
- [x] **GitHub搜索**: 找到CS220-dmfb-synthesis-skeleton和MFSimStatic
- [x] **克隆仓库**: 已获取两个工具的完整代码
- [x] **调研报告**: 记录在EXTERNAL_TOOLS_INTEGRATION.md

**状态**: 已获取CS220和MFSimStatic源代码

#### 任务 1.2: 接入MFSim ✅
- [x] 下载MFSim (已克隆到C:/claude/MFSimStatic)
- [x] 理解MFSim输入格式 (Assay/Arch txt文件)
- [x] 理解MFSim输出格式 (多阶段接口文件)
- [x] 完成`src/baseline/adapters/mfsim_adapter.py`的具体实现
- [x] 测试MFSim适配器 (4/4测试通过)

**交付物**:
- `src/baseline/adapters/mfsim_adapter.py` (570行)
- `scripts/test_mfsim_adapter.py` 测试脚本
- 支持10+调度器, 4+布局器, 9+路由器

#### 任务 1.2b: 接入CS220 ✅
- [x] 下载CS220 (已克隆到C:/claude/CS220-dmfb-synthesis-skeleton)
- [x] 理解CS220输入格式 (CFG/DAG/Arch文件)
- [x] 完成`src/baseline/adapters/cs220_adapter.py`的具体实现
- [x] 导入17个基准测试用例到data/cs220_assays/
- [x] 验证PCR用例 (makespan=35, CPL=35, 100%最优)

**交付物**:
- `src/baseline/adapters/cs220_adapter.py` (500行)
- `scripts/import_cs220_assays.py` 导入脚本
- `scripts/benchmark_cs220.py` 基准测试脚本
- 17个标准测试用例已导入

#### 任务 1.3: 接入Splash-2（如果获得）
- [ ] 下载并编译Splash-2
- [ ] 理解BioCoder协议描述语言
- [ ] 完成`src/baseline/adapters/splash_adapter.py`的具体实现
- [ ] 测试完整编译流程

**交付物**: 可用的Splash-2适配器

**状态**: 低优先级 (CS220和MFSim已提供足够baseline)

#### 任务 1.4: 备选方案（如果无法获得外部工具）
- [ ] 实现Simulated Annealing (SA) placement作为对比
- [ ] 实现OR-Tools ILP scheduling（使用Google OR-Tools）
- [ ] 研究并参考开源的MAPF（多智能体路径规划）算法

**交付物**: 至少2种不同的baseline算法

---

### Week 2: 数据生成与验证

#### 任务 2.1: 生成训练数据集
- [ ] 小规模测试集：20 ops × 100个，50 ops × 100个
- [ ] 中规模训练集：100 ops × 200个，200 ops × 100个
- [ ] 大规模挑战集：500 ops × 50个（测试扩展性）
- [ ] 多样化模式：linear, parallel, fork_join, pcr, random各20%

**命令**:
```bash
python scripts/generate_dataset.py \
    --output data/training \
    --sizes 20 50 100 200 \
    --num-per-size 100 \
    --patterns linear parallel fork_join pcr random
```

**交付物**: `data/training/`目录下1000+个问题文件

#### 任务 2.2: 运行Baseline生成标签
- [ ] 在小规模数据集上测试完整pipeline
- [ ] 修复发现的bug
- [ ] 在全量数据上运行（可能需要数小时）
- [ ] 保存每个问题的最优解（可能运行多次取最好）

**交付物**: `data/training/problem_XXXX.json`（包含problem + baseline_solution）

#### 任务 2.3: 数据分析与统计
- [ ] 分析不同规模问题的平均makespan
- [ ] 分析不同pattern的难度差异
- [ ] 计算关键路径长度 vs 实际makespan的比值
- [ ] 生成数据分布图表

**交付物**: `docs/dataset_statistics.md` + 图表

---

### Week 3: 可视化与验证工具

#### 任务 3.1: 完善可视化工具
- [ ] 改进placement可视化（添加模块名称、依赖箭头）
- [ ] 实现schedule动画（时间推进显示）
- [ ] 实现routing动画（液滴移动轨迹）
- [ ] 添加3D可视化（x, y, time）

**交付物**: 可用的可视化函数，示例图片

#### 任务 3.2: 验证工具
- [ ] 实现placement验证器（检查重叠、越界）
- [ ] 实现schedule验证器（检查依赖、资源冲突）
- [ ] 实现routing验证器（检查碰撞、流体约束）
- [ ] 集成到Verifier Agent框架

**交付物**: `src/agents/verifier/verification_tools.py`

#### 任务 3.3: 基准测试结果
- [ ] 在不同规模问题上测试baseline性能
- [ ] 记录运行时间、成功率、解质量
- [ ] 与文献中的结果对比（如果有）

**交付物**: `docs/baseline_benchmarks.md`

---

### Week 4: Phase 1 总结与准备

#### 任务 4.1: 代码整理
- [ ] 添加完整的docstring
- [ ] 运行代码格式化（black）
- [ ] 添加类型注解
- [ ] 编写单元测试（pytest）

**交付物**: 干净的代码库，测试覆盖率>80%

#### 任务 4.2: 文档编写
- [ ] 更新README，添加使用示例
- [ ] 编写API文档
- [ ] 记录算法参数调优经验

**交付物**: 完善的文档

#### 任务 4.3: Checkpoint Review
- [ ] 确保可以一键生成数据集
- [ ] 确保可以一键运行baseline
- [ ] 准备向导师汇报Phase 1成果

---

## Phase 2: Agent 框架开发（第5-12周）

### Week 5-6: Master Agent 设计

#### 任务 5.1: 系统架构设计
- [ ] 设计Agent通信协议（消息格式、状态机）
- [ ] 设计迭代优化流程图
- [ ] 确定LLM选型（GPT-4 API vs 本地模型）

**交付物**: `docs/agent_architecture.md`，包含架构图

#### 任务 5.2: Master Agent 实现
- [ ] 实现任务分解功能
- [ ] 实现子Agent调度器
- [ ] 实现结果汇总器
- [ ] 实现冲突检测器

**代码**: `src/agents/master/master_agent.py`

#### 任务 5.3: 迭代优化框架
- [ ] 实现反馈循环机制
- [ ] 实现重新规划触发器
- [ ] 实现收敛判断（何时停止迭代）

**交付物**: 可用的迭代优化器

---

### Week 7-8: Placement Agent

#### 任务 7.1: Prompt 工程设计
- [ ] 设计placement任务的prompt模板
- [ ] 添加Chain-of-Thought提示
- [ ] 添加Few-shot示例
- [ ] 测试不同prompt的效果

**交付物**: `src/agents/placement/prompts.py`

#### 任务 7.2: 代码生成策略
- [ ] 实现Python代码生成（Code-as-Policy）
- [ ] 实现JSON直接输出
- [ ] 添加约束检查（后处理修复）
- [ ] 实现从错误中学习

**代码**: `src/agents/placement/placement_agent.py`

#### 任务 7.3: 微调数据准备
- [ ] 将baseline结果转换为指令格式
- [ ] 划分训练/验证集
- [ ] 实现数据加载器

**交付物**: `data/finetune/placement/train.jsonl`

---

### Week 9-10: Scheduling Agent

#### 任务 9.1: Prompt 工程设计
- [ ] 设计scheduling任务的prompt模板
- [ ] 将DAG转换为文本描述
- [ ] 添加优先级策略说明

**交付物**: `src/agents/scheduling/prompts.py`

#### 任务 9.2: Agent 实现
- [ ] 实现序列生成策略
- [ ] 或使用List Scheduling + LLM优化决策
- [ ] 添加约束满足保证

**代码**: `src/agents/scheduling/scheduling_agent.py`

#### 任务 9.3: 微调数据准备
- [ ] 提取调度序列作为训练目标
- [ ] 准备instruction-response对

**交付物**: `data/finetune/scheduling/train.jsonl`

---

### Week 11-12: Routing Agent

#### 任务 11.1: Prompt 工程设计
- [ ] 设计routing任务的prompt模板
- [ ] 描述时空约束
- [ ] 添加冲突消解策略

**交付物**: `src/agents/routing/prompts.py`

#### 任务 11.2: Agent 实现
- [ ] 实现路径生成
- [ ] 或使用A* + LLM冲突消解
- [ ] 多液滴协同路由

**代码**: `src/agents/routing/routing_agent.py`

#### 任务 11.3: Verifier Agent
- [ ] 集成验证工具
- [ ] 实现冲突报告生成
- [ ] 实现修复建议生成

**代码**: `src/agents/verifier/verifier_agent.py`

---

## Phase 3: LLM 集成与训练（第13-24周）

### Week 13-16: 模型微调

#### 任务 13.1: 环境准备
- [ ] 申请GPU资源（实验室服务器/云计算）
- [ ] 安装vLLM / TGI用于推理
- [ ] 安装PEFT用于微调
- [ ] 下载基础模型（CodeLlama-7B/13B）

**交付物**: 可用的训练环境

#### 任务 13.2: Placement Agent 微调
- [ ] 使用LoRA配置（r=16, alpha=32）
- [ ] 训练3-5个epoch
- [ ] 验证集上评估
- [ ] 保存最佳模型权重

**命令**:
```bash
python src/agents/placement/finetune.py \
    --data data/finetune/placement \
    --output models/placement-agent \
    --base_model codellama/CodeLlama-7b-Instruct-hf
```

**交付物**: `models/placement-agent/`目录

#### 任务 14.1: Scheduling Agent 微调
- [ ] 类似placement的训练流程
- [ ] 优化序列生成质量

**交付物**: `models/scheduling-agent/`

#### 任务 15.1: Routing Agent 微调
- [ ] 训练路径生成模型
- [ ] 或使用较小的模型（可能不需要微调）

**交付物**: `models/routing-agent/`

#### 任务 16.1: Master Agent 微调（可选）
- [ ] 收集迭代优化轨迹
- [ ] 训练冲突分析能力

---

### Week 17-20: RAG 与增强

#### 任务 17.1: 向量数据库设置
- [ ] 安装ChromaDB或FAISS
- [ ] 将baseline结果编码为向量
- [ ] 实现相似问题检索

**交付物**: `src/agents/rag/retriever.py`

#### 任务 17.2: Few-shot 示例选择
- [ ] 基于问题相似度选择示例
- [ ] 动态添加到prompt中
- [ ] 测试效果提升

#### 任务 18.1: 反馈学习
- [ ] 收集"错误->修复"的训练对
- [ ] 实现在线学习（可选）
- [ ] 更新模型以改进错误

#### 任务 19.1: 迭代优化改进
- [ ] 分析常见失败模式
- [ ] 设计针对性的修复策略
- [ ] 实现早期终止策略（避免无限迭代）

#### 任务 20.1: 系统集成测试
- [ ] 完整pipeline端到端测试
- [ ] 性能 profiling
- [ ] 优化瓶颈

---

### Week 21-24: 对比实验

#### 任务 21.1: 实验设计
- [ ] 设计对比表格（vs GA, vs SA, vs 分层方法）
- [ ] 设计消融实验（各组件贡献）
- [ ] 选择测试集（留出验证集）

**交付物**: `experiments/experiment_plan.md`

#### 任务 21.2: 运行对比实验
- [ ] 在测试集上运行所有方法
- [ ] 记录makespan, runtime, success rate
- [ ] 多次运行取平均（减少随机性影响）

#### 任务 22.1: 消融实验
- [ ] 无LLM（纯启发式）
- [ ] 单Agent vs 多Agent
- [ ] 不同模型大小（7B vs 13B）
- [ ] 有无迭代优化
- [ ] 有无RAG

#### 任务 23.1: 鲁棒性测试
- [ ] 不同问题规模（20/50/100/200/500 ops）
- [ ] 不同约束严格程度
- [ ] 容错能力测试（故意制造不可行问题）

#### 任务 24.1: 结果分析
- [ ] 统计分析（t-test等）
- [ ] 生成对比图表
- [ ] 分析失败案例

**交付物**: `experiments/results/`目录，包含所有结果和图表

---

## Phase 4: 论文撰写与答辩（第25-40周）

### Week 25-28: 论文初稿

#### 任务 25.1: 大纲与框架
- [ ] 确定投稿目标（DAC/ICCAD/TCAD）
- [ ] 制定论文大纲
- [ ] 分配写作任务（如果有多人合作）

**交付物**: `paper/outline.md`

#### 任务 26.1: Introduction
- [ ] DMFB背景介绍
- [ ] 问题重要性和挑战
- [ ] 现有方法局限性
- [ ] 本文贡献（3-4点）

#### 任务 27.1: Related Work
- [ ] DMFB综合算法综述
- [ ] LLM for EDA相关工作
- [ ] 多Agent系统相关工作
- [ ] 对比分析

#### 任务 28.1: Methodology
- [ ] 系统架构图
- [ ] 每个Agent的详细设计
- [ ] 迭代优化算法
- [ ] 复杂度分析

---

### Week 29-32: 实验与结果章节

#### 任务 29.1: 实验设置
- [ ] 硬件环境描述
- [ ] 软件配置
- [ ] 数据集描述
- [ ] 评估指标定义

#### 任务 30.1: 主要结果
- [ ] 与baseline的对比表格
- [ ] 不同规模问题的扩展性图表
- [ ] 运行时间对比
- [ ] 成功率统计

#### 任务 31.1: 消融研究
- [ ] 各组件贡献分析
- [ ] 参数敏感性分析
- [ ] Case study（具体案例分析）

#### 任务 32.1: 讨论
- [ ] 结果解释
- [ ] 局限性分析
- [ ] 未来工作

---

### Week 33-36: 论文完善

#### 任务 33.1: 完整初稿
- [ ] 整合所有章节
- [ ] 检查逻辑连贯性
- [ ] 补充引用文献

**交付物**: `paper/draft_v1.pdf`

#### 任务 34.1: 导师审阅
- [ ] 提交给导师审阅
- [ ] 根据反馈修改
- [ ] 可能需要多轮修改

#### 任务 35.1: 图表优化
- [ ] 使用专业绘图工具（tikz/ illustrator）
- [ ] 统一图表风格
- [ ] 确保清晰度（矢量图）

#### 任务 36.1: 格式调整
- [ ] 根据投稿会议要求调整格式
- [ ] 检查页数限制
- [ ] 准备补充材料（如有）

---

### Week 37-40: 投稿与答辩

#### 任务 37.1: 论文投稿
- [ ] 检查投稿要求（匿名/非匿名）
- [ ] 提交论文和补充材料
- [ ] 准备rebuttal（如果需要）

#### 任务 38.1: 答辩准备
- [ ] 制作答辩PPT
- [ ] 准备演讲稿
- [ ] 模拟答辩（预演）

#### 任务 39.1: 代码开源准备
- [ ] 整理代码（去除硬编码路径等）
- [ ] 编写详细的README
- [ ] 准备示例notebook
- [ ] 脱敏处理（如果需要）

**交付物**: GitHub开源仓库

#### 任务 40.1: 最终答辩
- [ ] 正式答辩
- [ ] 回答评审问题
- [ ] 根据反馈修改论文

---

## 持续进行的任务（贯穿整个项目）

### 代码管理
- [ ] 每周git commit（良好的commit message）
- [ ] 定期备份到云端
- [ ] 重要节点打tag

### 实验记录
- [ ] 维护实验日志（每次实验的参数和结果）
- [ ] 保存所有中间结果
- [ ] 记录失败尝试（同样有价值）

### 文献跟踪
- [ ] 每周阅读2-3篇相关论文
- [ ] 更新文献综述
- [ ] 跟踪arXiv最新工作

### 与导师沟通
- [ ] 每周组会汇报进度
- [ ] 及时汇报遇到的问题
- [ ] 定期展示可视化结果

---

## 关键检查点（Checkpoint）

| 时间点 | 检查点 | 验收标准 |
|-------|-------|---------|
| 第4周末 | Phase 1完成 | 有1000+训练样本，baseline可一键运行 |
| 第8周末 | Agent原型 | Master+3个子Agent可通信 |
| 第12周末 | Agent框架完成 | 端到端pipeline可跑通 |
| 第16周末 | 微调完成 | 有训练好的模型权重 |
| 第24周末 | 实验完成 | 所有对比实验数据就绪 |
| 第32周末 | 论文初稿 | 完整论文，导师认可 |
| 第40周末 | 项目完成 | 论文投稿/答辩通过 |

---

## 风险与应对

| 风险 | 可能性 | 应对措施 |
|-----|-------|---------|
| 无法获得MFSim | 中 | 使用纯Python实现 + OR-Tools |
| LLM效果不佳 | 中 | 增大训练数据量，调整prompt，fallback到传统算法 |
| GPU资源不足 | 低 | 使用API减少本地计算，申请云计算资源 |
| 时间不够 | 中 | 优先完成核心功能，简化非关键部分 |
| 论文被拒 | 中 | 准备多个档次期刊/会议，持续改进 |

---

## 今日下一步

### 今天就做：
1. [ ] 运行 `python demo.py` 验证框架
2. [ ] 询问导师关于MFSim/Splash-2的获取方式
3. [ ] 生成第一批10个测试问题：`python scripts/generate_dataset.py --sizes 20 --num-per-size 10`
4. [ ] 阅读 `PROJECT_SUMMARY.md` 熟悉代码结构

### 本周完成：
1. [ ] 完成小规模数据集生成（100个问题）
2. [ ] 运行baseline获取初始结果
3. [ ] 检查所有代码是否可以正常运行
4. [ ] 准备向导师汇报Phase 1计划

---

**最后更新**: 2024年
**项目总时长**: 40周（10个月）
**当前阶段**: Phase 1 Week 1
