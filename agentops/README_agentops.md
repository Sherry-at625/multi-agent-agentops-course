# AgentOps 记录说明与折算假设

> 本目录存放运行 R001 的观测数据与复盘结论。所有字段定义遵循 `templates/agentops_checklist.md`。

## 一、文件清单

| 文件 | 内容 | 生成方式 |
|---|---|---|
| `orchestrator_plan.md` | 任务拆解、调度计划、运行状态表、风险台账 | Orchestrator 手写 |
| `handoffs.md` | 4 个交接点的结构化摘要原文留痕 | Orchestrator 手写 |
| `agentops_trace.csv` | 11 条单步轨迹，21 字段（对齐模板 `agentops_trace_template.csv`） | `build_agentops_csv.py` 生成 |
| `agentops_run_summary.csv` | 1 条运行汇总，16 字段（对齐模板 `agentops_run_summary.csv`） | 同上 |
| `run_review.md` | 六大维度读数、失败点拆解、成本结构、复盘四问 | Orchestrator 手写 |
| `build_agentops_csv.py` | 轨迹表生成脚本（保证中文逗号的 CSV 引号正确） | — |

重新生成轨迹表：

```bash
python agentops/build_agentops_csv.py
```

## 二、字段取值约定

| 字段 | 取值约定 |
|---|---|
| `trace_id` | `T000`—`T010`，按执行顺序编号；重试不新增编号，而是记录在 `retry_count`（同一次尝试的失败与修复分别成行，便于回放对比） |
| `status` | `success` / `retry` / `failed` / `skipped`。本次仅用前三个中的 `success` 与 `failed`（失败行 `retry_count=1` 表示该次失败后触发了 1 次重试） |
| `qa_score` | 1—5：5 一次通过；4 经一次修改通过；3 需多次修改；1 严重退回。由 Reviewer 或编排者评定 |
| `duration_sec` | 该环节墙钟耗时（起止时间差），非 CPU 时间 |
| `retry_count` | 该环节累计重试次数（含本次） |

## 三、Token 与成本的折算假设（必读）

**这些数字不是平台精确计量值**，而是为了让成本维度可被讨论而做的近似折算。折算假设如下，任何引用本表的人都应同时引用这一段：

1. **计量方式**：本次运行在同一 Agent 会话中完成 5 个角色的工作，平台未按角色切分 token 计量。轨迹中的 `prompt_tokens` / `completion_tokens` 按**该环节实际读入的文件体量 + 提示词长度 + 产出文本长度**近似折算。
2. **折算系数**：中文按 **1 字 ≈ 1.5 token**（含标点与空白）；英文与代码按 **1 字符 ≈ 0.25 token**；CSV 输入按「表头 + 抽样行」计入，不按 3654 行全量计入。
3. **成本**：按本地运行（无外部 API 计费）折算为 **0.00 元**。**不引用任何平台的官方价格**，也不把积分折算为货币——因为不同平台、不同模型的积分单价差异极大，编造汇率会误导成本判断。
4. **可信度**：`duration_sec` 与 `retry_count`、`status`、`error_message` 为**真实记录**；`*_tokens` 与 `estimated_cost_cny` 为**近似估算**。分析成本结构时请以此区分。

## 四、如何用这套数据做回放

1. 打开 `orchestrator_plan.md` 的运行状态表，找到标 ⚠️ 的节点（本次为 T3 图表、T4 质检）。
2. 在 `agentops_trace.csv` 中筛 `status=failed` 或 `retry_count>0`，取出相同 `task_step` 的失败行与成功行。
3. 对比两行的 `input_summary` / `tool_called` / `output_summary`——差异点即修复动作。
4. 在 `run_review.md` 的第二节看根因拆解，第六节看结论。
5. 若需复现修复结果，按 `outputs/零售销售数据分析报告.md` 第 9.5 节的三条命令重跑全链路。
