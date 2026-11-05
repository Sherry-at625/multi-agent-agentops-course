# AGENTS.md — 项目级 Agent 入口

> 本文件是《多智能体协作与 AgentOps》课程实践的**项目级规则入口**。
> 任何进入本项目的 Agent（Trae 自定义智能体 / SOLO / WorkBuddy）在开始工作前必须先读本节，再读 `.trae/rules/global_rules.md`。

## 0. 权威规则文件

| 文件 | 作用 | 是否必须阅读 |
|---|---|---|
| `.trae/rules/global_rules.md` | 全局规则：项目背景、数据字典、输出规范、交接协议、质量底线 | 必须，全文 |
| `prompts/0X_*.md` | 五个角色的系统提示词（**只读**，属于任务定义，不得被产物覆盖） | 各角色读自己那一份 |
| `agentops/orchestrator_plan.md` | 编排者的任务拆解清单与调度计划（含运行状态表） | 必须，用于确认自己处在哪个节点 |
| `agentops/handoffs.md` | 各环节的结构化交接摘要（含口径与遗留问题） | 接手前必须读上游那一段 |

## 1. 五个角色与产物边界（不得越界）

| 角色 | 允许写入 | 禁止写入 |
|---|---|---|
| Orchestrator 编排者 | `agentops/orchestrator_plan.md`、`agentops/handoffs.md` | 任何 `data/` `code/` `outputs/` 产物 |
| Data Engineer 数据工程 | `code/01_clean_data.py`、`data/retail_sales_cleaned.csv`、`outputs/cleaning_report.json` | 分析指标、图表、报告 |
| Analyst 分析可视化 | `code/02_analyze_charts.py`、`outputs/summary_metrics.json`、`outputs/charts/` | 清洗数据、报告 |
| Reviewer 质检评审 | `code/03_verify_qa.py`（只读复算脚本）、`outputs/qa_review.md` | 上游任何数据与指标文件 |
| Reporter 报告撰写 | `outputs/零售销售数据分析报告.md`、`outputs/零售销售数据分析报告.docx` | 指标、图表、清洗数据 |

## 2. 目录约定

```
multi-agent-agentops-course/
├── AGENTS.md                       # 本文件（项目规则入口）
├── .trae/rules/global_rules.md     # 全局规则（所有 Agent 共享上下文）
├── data/                           # raw 只读；cleaned 为数据工程产物
├── code/                           # 各 Agent 生成的脚本，编号即执行顺序
├── prompts/                        # 五角色系统提示词（只读）
├── templates/                      # AgentOps 观测模板（原始空白版，只读）
├── outputs/                        # 本次运行的交付产物
│   ├── cleaning_report.json
│   ├── summary_metrics.json
│   ├── charts/01~04.png
│   ├── qa_review.md
│   └── 零售销售数据分析报告.md / .docx
├── agentops/                       # 编排计划、交接摘要、已填写的轨迹与复盘表
├── reference_outputs/              # 课程参考答案，仅供质检对照，不参与本次交付
└── docs/                           # 课程手册与作业说明
```

## 3. 执行顺序（硬约束）

`01_clean_data.py` → `02_analyze_charts.py` → `03_verify_qa.py` → 报告撰写。
下游脚本的输入必须是上游已落盘的文件；**禁止**跳过中间产物直接在内存里串起来，否则 AgentOps 轨迹无法回放。

## 4. 统一复跑命令

```bash
python code/01_clean_data.py        # 清洗 → data/retail_sales_cleaned.csv + outputs/cleaning_report.json
python code/02_analyze_charts.py    # 指标 + 图表 → outputs/summary_metrics.json + outputs/charts/*.png
python code/03_verify_qa.py         # 只读复算 → 控制台输出核查证据 + outputs/qa_evidence.json
```

依赖：`pandas`、`matplotlib`、`numpy`。中文字体在脚本内按 `Microsoft YaHei → SimHei → Noto Sans CJK SC` 顺序回退。

## 5. 交接纪律

上游交付 = **产物路径 + 结构化摘要（关键指标 / 口径 / 遗留问题）**；
下游接手 = 先核对产物存在与行数，再动手；发现上游错误**不擅自改**，记录后交回编排者决定回退。
