# DMFB + LLM 项目 - Claude 记忆文件

> 此文件保存项目关键上下文，供跨会话恢复使用

---

## 项目基本信息

- **项目名称**: dmfb-llm-synthesis
- **GitHub**: https://github.com/ZZY-0813/dmfb-llm-synthesis
- **目标**: 基于LLM Agent的DMFB全流程综合算法研究
- **周期**: 24周 (已优化，原40周)

---

## 当前状态 (2026-02-28)

### 已完成 ✅
- 核心Baseline框架 (problem.py, placement_ga.py, scheduling_list.py, routing_astar.py)
- CS220适配器 + 17个测试用例
- MFSimStatic适配器 (23+算法)
- 问题生成器 + 可视化工具
- GitHub仓库已推送
- 权限模式: Auto (无需确认直接执行)

### 进行中 🚧
- Phase 1 Week 1: 验证器核心实现

### 本周优先任务
1. [ ] 运行 `python demo.py` 验证框架
2. [ ] 实现 Placement 验证器
3. [ ] 申请 OpenAI/Anthropic API Key

---

## 关键决策记录

### 策略调整 (2026-02-28)
- **API优先**: 使用 GPT-4/Claude API，跳过微调阶段
- **Agent架构**: Master + 3个子Agent独立开发 (Placement, Scheduling, Routing)
- **周期压缩**: 从40周缩短到24周 (6个月)
- **单轮生成+后处理**: 减少LLM调用次数

### 权限设置
- Git Credential Manager 已启用
- Auto模式已开启 (操作无需确认)
- 远程URL: https://github.com/ZZY-0813/dmfb-llm-synthesis.git

---

## 文件结构速查

```
dmfb-llm-synthesis/
├── src/
│   ├── baseline/           # 核心算法
│   │   ├── problem.py      # 数据结构
│   │   ├── placement_ga.py # GA布局
│   │   ├── scheduling_list.py
│   │   ├── routing_astar.py
│   │   └── adapters/       # 外部工具适配器
│   │       ├── cs220_adapter.py
│   │       └── mfsim_adapter.py
│   ├── dataset/generator.py
│   └── utils/visualization.py
├── scripts/
│   ├── generate_dataset.py
│   ├── run_baseline.py
│   └── import_cs220_assays.py
├── data/cs220_assays/      # 17个基准测试
└── PROGRESS.md             # 详细进度追踪
```

---

## 常用命令

```bash
# 运行演示
python demo.py

# 生成数据集
python scripts/generate_dataset.py --sizes 20 --num-per-size 10

# 运行baseline
python scripts/run_baseline.py --problem test.json --method python

# 推送代码 (已配置Auto模式，可直接执行)
git add . && git commit -m "message" && git push
```

---

## 注意事项

1. **外部工具位置**:
   - CS220: `C:/claude/CS220-dmfb-synthesis-skeleton` (需编译)
   - MFSimStatic: `C:/claude/MFSimStatic` (需编译)

2. **Git配置**:
   - 用户名: ZZY-0813
   - 凭证管理器已启用
   - Token已配置在Credential Manager中

3. **代码风格**:
   - 使用中文注释和文档
   - 提交信息用中文描述

---

## 下一步计划

### Phase 1 (Week 1-3)
1. 实现验证器 (placement, scheduling, routing)
2. 生成小规模数据集
3. 申请API Key

### Phase 2 (Week 4-8)
1. LLM客户端 + Prompt系统
2. Placement Agent
3. Scheduling Agent
4. Routing Agent
5. Master Agent集成

---

**最后更新**: 2026-02-28
**会话ID**: a4c04d95-f847-4672-a6ba-8f03cb04ca30
