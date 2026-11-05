# 多智能体协作与 AgentOps · 课程实践成果物

> 课程：《多智能体协作与 AgentOps》（本科大数据专业 · 人工智能工具实践）
> 案例：2024—2025 年区域连锁零售销售数据多智能体协作分析流水线
> 提交人：Sherry-at625 ｜ 运行编号：**R001** ｜ 完成时间：2026-11-05
> 依据：`docs/课程实践操作手册.md` 第五章「分步操作指引」步骤 0—5

---

## 一、一句话说明这次做了什么

按操作手册的五个实践步骤，用 **5 个角色**（编排者 / 数据工程 / 分析可视化 / 质检评审 / 报告撰写）协作跑通了一条完整的零售销售数据分析流水线：**3654 行含脏数据 → 3388 行有效订单 → 5 个维度指标 → 4 张图表 → 19 项质检 → 一份 Markdown + Word 中文分析报告**，并按 AgentOps 六大观测维度记录了 11 条执行轨迹与一份复盘报告。

核心业务结论：总销售额 **3,888,210.60 元**、总利润 **1,719,269.64 元**、整体利润率 **44.22%**、客单价 **1,147.64 元**。

---

## 二、步骤与产物对照（对照手册验收标准）

| 手册步骤 | 要求 | 本次产物 | 状态 |
|---|---|---|---|
| **步骤 0** 建立项目与全局规则 | 规则文件加载、原始数据可读、理解五角色与产物路径 | `.trae/rules/global_rules.md`、`AGENTS.md` | ✅ |
| **步骤 1** 编排拆解 + 数据工程清洗 | 任务清单与调度计划；`cleaned.csv` + `cleaning_report.json`；清洗报告含 8 个必填条数 | `agentops/orchestrator_plan.md`、`code/01_clean_data.py`、`data/retail_sales_cleaned.csv`、`outputs/cleaning_report.json` | ✅ |
| **步骤 2** 分析与可视化 | `summary_metrics.json` + 四张 150DPI 中文图表 + 3—5 条带数值洞察 | `code/02_analyze_charts.py`、`outputs/summary_metrics.json`、`outputs/charts/01~04*.png`、`outputs/analyst_insights.md` | ✅ |
| **步骤 3** 质检评审与回退闭环 | 按 A/B/C 清单核查、独立复算、出具分级结论、退回闭环 | `code/03_verify_qa.py`、`outputs/qa_review.md`、`outputs/qa_evidence.json` | ✅（有条件通过，1 次回退闭环） |
| **步骤 4** WorkBuddy 汇总生成报告 | 十节结构、四图嵌入、数字与指标文件一致、导出 Word | `outputs/零售销售数据分析报告.md`、`outputs/零售销售数据分析报告.docx`（13 表 4 图 110 段） | ✅ |
| **步骤 5** AgentOps 记录、回放与复盘 | 轨迹表 21 字段、运行汇总表 16 字段、复盘四问 | `agentops/agentops_trace.csv`（11 条）、`agentops/agentops_run_summary.csv`、`agentops/run_review.md` | ✅ |

---

## 三、关键数字（唯一口径：`outputs/summary_metrics.json`）

| 指标 | 数值 |
|---|---|
| 原始记录 / 清洗后有效订单 | 3,654 → **3,388**（剔除 266 条，比例 **7.28%**） |
| 总销售额 | **3,888,210.60 元**（388.82 万元） |
| 总利润 | **1,719,269.64 元**（171.93 万元） |
| 整体利润率 / 客单价 | **44.22%** / **1,147.64 元** |
| 第一大品类 | 电子产品 159.03 万元，占 **40.90%**，利润率 36.56% |
| 最高利润率品类 | 美妆个护 **54.98%** |
| 地区前三 | 华南 17.49% / 华中 17.16% / 华东 17.13% |
| 客户分层 | 老客 36.77% / 新客 29.05% / 会员 28.50% / 未知 5.67% |
| 月度峰谷 | 峰值 2024-10（227,482.51 元）／低谷 2025-10（125,354.79 元） |
| 年度对比 | 2024 年 195.68 万 / 2025 年 193.14 万，同比 **−1.30%** |

清洗条数（与手册参考答案逐项一致）：原始 3654 / 日期缺失 72 / 日期不可解析 0 / 去重 54 / 异常数量 35 / 负利润 105 / 分层回填 163 / 清洗后 3388 / 剔除比例 7.28%。

---

## 四、目录结构

```
multi-agent-agentops-course/
├── README.md                          # 本文件（成果说明与复跑指引）
├── AGENTS.md                          # 项目级 Agent 规则入口（角色边界、执行顺序）
├── .trae/rules/global_rules.md        # 步骤 0：全局规则（所有 Agent 共享上下文）
│
├── data/
│   ├── retail_sales_raw.csv           # 原始数据（只读，3654 行，UTF-8 BOM）
│   └── retail_sales_cleaned.csv       # 【产物】清洗后 3388 行
│
├── code/                              # 各环节由 Agent 生成并实际执行的脚本
│   ├── 01_clean_data.py               # 数据工程：探查 → 清洗 → 自检 → 清洗报告
│   ├── 02_analyze_charts.py           # 分析可视化：指标 → 分组 → 四图
│   ├── 03_verify_qa.py                # 质检：独立复算 + 19 项核查（只读）
│   └── 04_export_docx.py              # 报告：Markdown → Word 版式
│
├── outputs/                           # 【产物】本次运行的全部交付物
│   ├── cleaning_report.json           # 清洗报告（含处理明细、口径说明、待人工确认）
│   ├── summary_metrics.json           # 指标（唯一数字口径）
│   ├── charts/01_monthly_sales.png    # 图1 月度趋势折线
│   ├── charts/02_category_profit.png  # 图2 品类对比条形
│   ├── charts/03_region_share.png     # 图3 地区占比饼图
│   ├── charts/04_segment_contribution.png  # 图4 分层贡献组合图
│   ├── analyst_insights.md            # 5 条带数值初版洞察
│   ├── qa_review.md                   # 质检报告（有条件通过）
│   ├── qa_evidence.json               # 质检机器证据（19 项逐条留痕）
│   ├── 零售销售数据分析报告.md         # 【主交付】九章中文分析报告
│   └── 零售销售数据分析报告.docx       # 【主交付】Word 版
│
├── agentops/                          # AgentOps 观测与复盘
│   ├── orchestrator_plan.md           # 任务拆解、调度计划、状态表、风险台账
│   ├── handoffs.md                    # 4 个交接点的结构化摘要留痕
│   ├── agentops_trace.csv             # 11 条轨迹 × 21 字段
│   ├── agentops_run_summary.csv       # 1 条运行汇总 × 16 字段
│   ├── run_review.md                  # 六大维度读数、失败拆解、复盘四问
│   ├── README_agentops.md             # 字段约定与 Token 折算假设
│   └── build_agentops_csv.py          # 轨迹表生成脚本
│
├── prompts/                           # 课程提供的五角色提示词（只读）
├── templates/                         # 课程提供的 AgentOps 模板（只读）
├── docs/                              # 课程手册与作业说明
└── reference_outputs/                 # 课程参考答案，仅供质检对照，不属本次交付
```

---

## 五、一键复跑

环境：Python 3.13 + `pandas` / `matplotlib` / `numpy` / `python-docx`

```bash
pip install pandas matplotlib numpy python-docx

python code/01_clean_data.py        # → data/retail_sales_cleaned.csv + outputs/cleaning_report.json
python code/02_analyze_charts.py    # → outputs/summary_metrics.json + outputs/charts/*.png
python code/03_verify_qa.py         # → outputs/qa_evidence.json（独立复算）
python code/04_export_docx.py       # → outputs/零售销售数据分析报告.docx
python agentops/build_agentops_csv.py   # → agentops/agentops_trace.csv 等
```

三条硬约束：脚本可重复运行（无随机过程）；`data/retail_sales_raw.csv` 全程只读；下游只消费上游已落盘的文件，不跳过中间产物。

---

## 六、这次运行中值得一提的三件事

### 1. 真实翻车了一次：图表中文全是方框

首版分析脚本照搬参考资料的 `Noto Sans CJK SC`，但这台机器是 Windows，该字体不存在，matplotlib 静默回落到 DejaVu Sans，**四张图的中文全部渲染成豆腐块**，而且不报错、文件照常生成。错误信息：`Glyph 26376 missing from font(s) DejaVu Sans`。

修复不是简单换个字体名，而是加了**字形级断言**——用 `FT2Font.get_char_index(ord("月"))` 确认字体文件真的包含汉字，找不到可读字体就 `raise SystemExit` 中断，宁可失败也不静默降级。这条修复记在 `agentops/run_review.md` 第二节。

### 2. 主动回退了一次：为了「可追溯」而不是「改错数」

质检发现清洗报告里「销售额重算修正 13 条」，但原始数据里明显有 49 条不符——读者无法判断这个 13 是原始口径还是清洗后口径。数值本身没错，但**口径不可解释**。编排者仍退回数据工程补了一次留痕（`销售额重算统计范围` + `原始不符条数: 49` + 13 个受影响 `order_id`），耗时 98 秒。

### 3. 质检是「用独立代码复算」，不是「再看一遍」

`code/03_verify_qa.py` 的复算逻辑**没有复用** `02_analyze_charts.py` 的任何函数，PNG 的 DPI 是直接解析文件的 `pHYs` 块拿到的（不依赖 Pillow）。最终 A/B/C 三组 12 项硬性核查全部通过，五个维度的分组合计与总体差额**全部为 0.00 元**，报告正文 64 项数字一致性断言全部通过。

质检结论为「**有条件通过**」：0 严重、0 一般、2 建议（销售额覆盖未留原值、图 2 未标注利润率）、2 提示（未知分层样本仅 4.81% 不足以单列结论、月度峰谷缺归因字段不得推断原因）。

---

## 七、说明与边界

1. 本案例数据为课程合成教学数据，不含真实个人信息，数值不代表任何真实企业经营状况。
2. `reference_outputs/` 是课程提供的教师参考答案（含参考清洗结果、参考指标、样例行报告），本次仅用于质检对照，**不作为交付物**；本次运行的清洗条数与参考答案逐项一致，指标三位以上有效数字完全一致。
3. `agentops/*.csv` 中的 `duration_sec` / `status` / `retry_count` / `error_message` 为**真实记录**；`*_tokens` 与 `estimated_cost_cny` 为**近似估算**（平台未按角色切分计量），折算假设见 `agentops/README_agentops.md` 第三节。
4. Word 版式已做结构校验（表格数 / 图片数 / 中文字体 / 语法残留），未做 PDF 目视预览（当前环境的 Word COM 接口被占用），建议提交前在 Word 中人工确认一次排版。
5. 除下述改进项外，未做与任务无关的文件删除或系统命令操作。

### 下一版改进项（来自质检建议）

- 清洗脚本增加输出 `outputs/sales_recalc_diff.csv`（order_id / 原值 / 新值 / 差额），让被覆盖的销售额可逐单核对；
- 图表交付前增加「豆腐块像素检测」，用机器替代人眼做第一道筛；
- 把「图表验收标准」从定性描述改为可执行检查清单（DPI 数值、字体名、轴标签非空、图例存在），供 Analyst 自检与 Reviewer 复核共用。

---

## 八、参考来源

课程资料包 `README.md` 与 `docs/课程实践操作手册.md`；Trae 官方文档、WorkBuddy 官网、CrewAI / AutoGen / LangGraph 文档、Langfuse、LangSmith、AgentOps（arXiv:2507.11277）——均见课件 P39。
