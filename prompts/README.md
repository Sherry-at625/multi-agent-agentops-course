# Prompt 包使用说明

## 1. 包内文件

| 文件 | 角色 | 建议承载平台 | 环节 |
|---|---|---|---|
| `00_global_rules.md` | 全局规则（项目背景、数据字典、交接协议、质量底线） | Trae 项目规则 / WorkBuddy 知识库 | 全程共享 |
| `01_orchestrator.md` | 编排者：任务拆解、分派、回收、回退、汇总 | Trae Agent 窗口 / WorkBuddy Plan 模式 | 全程调度 |
| `02_data_engineer.md` | 数据工程：清洗、探查、口径复核、清洗报告 | Trae IDE / SOLO + Python 终端 | 环节 1 |
| `03_analyst.md` | 分析可视化：指标、分组、图表、初步洞察 | Trae IDE / SOLO + Python 终端 | 环节 2 |
| `04_reviewer.md` | 质检评审：独立核查、复算、出具通过 / 退回意见 | WorkBuddy Ask 只读模式 | 环节 3 |
| `05_reporter.md` | 报告撰写：汇总质检通过的指标与图表，交付报告 | WorkBuddy（Word / PDF / 网页） | 环节 4 |

## 2. 平台配置要点

### Trae IDE / SOLO

1. 新建项目文件夹，放入本课程 `data/`、`code/` 与 `prompts/`。
2. 把 `00_global_rules.md` 内容写入项目规则（`.trae/rules/global_rules.md`，或项目根目录 `AGENTS.md`），作为所有 Agent 的共享上下文。
3. 在「自定义智能体 / Subagents」中分别创建数据工程、分析可视化、质检三个角色，粘贴对应系统提示词；可配置 MCP Server、工具集与模型。
4. 编排者使用 SOLO Plan 模式：先生成任务计划，人工确认后再逐步执行；多任务可在 Agent 窗口并行发起。
5. 终端沙箱权限遵循课堂设定：清洗与分析脚本默认沙箱运行，高风险命令需手动确认。

### WorkBuddy

1. 新建任务并选择 **Plan 模式**（先规划、确认后执行）；质检环节切换到 **Ask 模式**（只分析不改文件）。
2. 先上传 `00_global_rules.md` 作为项目背景；按环节依次调用数据处理、分析、写作专家 Agent。
3. 报告环节使用 Craft 模式直接交付 Word / PDF / 网页；多 Agent 并行处理图表排版与文字撰写。
4. 全程在结果面板查看文件变更、任务状态与对话记录，作为 AgentOps 回放材料。

## 3. 推荐执行顺序

```
全局规则入库
  → Orchestrator 拆解任务并输出调度计划（人工确认）
  → Data Engineer 清洗数据，交付 cleaned.csv + cleaning_report.json
  → Reviewer 预审数据质量（必要时退回修复）
  → Analyst 计算指标与图表，交付 summary_metrics.json + charts/
  → Reviewer 独立质检，输出 qa_review.md（通过 / 有条件通过 / 退回）
  → 若退回：Orchestrator 定位环节，退回对应 Agent 修复后重新质检
  → 质检通过后 Reporter 撰写并交付报告
  → 填写 AgentOps 运行记录与复盘表
```

## 4. 课堂使用建议

- 教师先完整演示一遍流水线；学生分组按上表复现，重点观察角色交接处的上下文传递与质检回退。
- 每个环节都要求学生在 `templates/agentops_trace_template.csv` 中记录一条轨迹，课后据此复盘成本、耗时与失败点。
- 提示词允许学生按实际平台能力微调，但角色职责边界、产物路径与交接协议不得删除。
