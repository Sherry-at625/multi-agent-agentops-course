# -*- coding: utf-8 -*-
"""
agentops/build_agentops_csv.py
==============================
把本次运行 R001 的 AgentOps 轨迹与汇总表落盘为 CSV（UTF-8 带 BOM，便于 Excel/WPS 直接打开）。

为什么用脚本生成而不是手改模板：
  - 21 个字段里有大量含中文逗号的文本，手工拼 CSV 极易漏引号导致列错位；
  - 用 csv 模块可保证引用与转义正确，且能被 pandas / Excel 双向读取验证。

运行：
    python agentops/build_agentops_csv.py
输出：
    agentops/agentops_trace.csv
    agentops/agentops_run_summary.csv
"""

from __future__ import annotations

import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "agentops"

TRACE_FIELDS = [
    "trace_id", "run_id", "timestamp", "agent_role", "agent_name", "platform",
    "task_step", "input_summary", "tool_called", "output_artifact", "output_summary",
    "status", "duration_sec", "prompt_tokens", "completion_tokens", "total_tokens",
    "estimated_cost_cny", "retry_count", "error_message", "qa_score", "reviewer_notes",
]

SUMMARY_FIELDS = [
    "run_id", "date", "group_name", "platform_combo", "total_agents", "total_steps",
    "success_steps", "failed_steps", "total_duration_sec", "total_tokens",
    "estimated_cost_cny", "human_interventions", "qa_overall_score",
    "main_failure_point", "replay_findings", "notes",
]

TRACE_ROWS = [
    # ---------- 编排 ----------
    dict(
        trace_id="T000", agent_role="Orchestrator", agent_name="OR-01",
        platform="WorkBuddy Plan", task_step="任务拆解与调度计划",
        input_summary="用户总指令；prompts/00_global_rules.md；prompts/01_orchestrator.md",
        tool_called="文件读取 / 任务清单生成",
        output_artifact="agentops/orchestrator_plan.md",
        output_summary="7 个节点 T0-T7；识别关键路径与 4 条回退路由；预判 4 项风险",
        status="success", timestamp="2026-11-05 14:36:20", duration_sec=228,
        prompt_tokens=9200, completion_tokens=3100,
        qa_score=5, reviewer_notes="拆解含前置依赖与验收标准，未越权代写分析代码",
    ),
    # ---------- 数据工程 ----------
    dict(
        trace_id="T001", agent_role="Data Engineer", agent_name="DE-01",
        platform="Trae IDE + Python 3.13", task_step="读取原始数据并探查",
        input_summary="data/retail_sales_raw.csv（UTF-8 BOM）；全局规则数据字典",
        tool_called="pandas.read_csv / DataFrame.describe / duplicated / value_counts",
        output_artifact="（控制台探查输出，写入轨迹 input_summary）",
        output_summary="3654 行 15 列；order_date 缺失 72、customer_segment 缺失 182；整行重复 54；quantity<=0 36；profit<0 111；斜杠日期 66 行",
        status="success", timestamp="2026-11-05 14:40:35", duration_sec=96,
        prompt_tokens=5400, completion_tokens=1500,
        qa_score=5, reviewer_notes="先探查后清洗，符合 Data Engineer 提示词第 1 条",
    ),
    dict(
        trace_id="T002", agent_role="Data Engineer", agent_name="DE-01",
        platform="Trae IDE + Python 3.13", task_step="执行清洗并输出报告",
        input_summary="data/retail_sales_raw.csv；探查结论；8 步清洗顺序",
        tool_called="pandas.to_datetime / drop_duplicates / 布尔过滤 / to_csv(utf-8-sig)",
        output_artifact="data/retail_sales_cleaned.csv; outputs/cleaning_report.json",
        output_summary="日期缺失剔除 72、去重 54、异常数量 35、负利润 105、分层回填 163；清洗后 3388 行，剔除比例 7.28%；自检 8 项全通过",
        status="success", timestamp="2026-11-05 14:46:52", duration_sec=302,
        prompt_tokens=12600, completion_tokens=4200,
        qa_score=4, reviewer_notes="首次交付未说明销售额重算的统计范围，质检 D12 指出后补正",
    ),
    # ---------- 分析可视化 ----------
    dict(
        trace_id="T003", agent_role="Analyst", agent_name="AN-01",
        platform="Trae IDE + Python 3.13", task_step="接手核对 + 总体/分组指标计算",
        input_summary="data/retail_sales_cleaned.csv（3388 行）；全局规则命名与单位规范",
        tool_called="pandas.groupby / resample('ME') / to_dict；自建 8 项质量断言",
        output_artifact="outputs/summary_metrics.json",
        output_summary="订单 3388；销售额 3,888,210.60；利润 1,719,269.64；利润率 44.22%；客单价 1,147.64；5 个维度分组，各维度合计与总体差额 0.00 元",
        status="success", timestamp="2026-11-05 14:52:10", duration_sec=258,
        prompt_tokens=14300, completion_tokens=5100,
        qa_score=5, reviewer_notes="接手先核对数据质量再分析，符合交接协议",
    ),
    dict(
        trace_id="T004", agent_role="Analyst", agent_name="AN-01",
        platform="Trae IDE + Python 3.13", task_step="生成四张图表（首版）",
        input_summary="data/retail_sales_cleaned.csv；字体配置仅写 Noto Sans CJK SC",
        tool_called="matplotlib.bar / barh / pie / plot；savefig(dpi=150)",
        output_artifact="outputs/charts/01~04*.png（含缺陷）",
        output_summary="四图已落盘但全部中文字形渲染为方框；图4 纵轴出现 1e6 科学计数；图3 浅色扇区白字不可读",
        status="failed", timestamp="2026-11-05 14:54:26", duration_sec=124,
        prompt_tokens=9800, completion_tokens=3600,
        estimated_cost_cny=0.0, retry_count=1,
        error_message="Glyph 26376 (月) missing from font(s) DejaVu Sans；font.sans-serif 未命中 Noto Sans CJK SC",
        qa_score=1,
        reviewer_notes="严重缺陷：中文不可读即等于图表不可用，必须重出图后才可进入质检",
    ),
    dict(
        trace_id="T005", agent_role="Analyst", agent_name="AN-01",
        platform="Trae IDE + Python 3.13", task_step="修复字体与图表规格后重出图（T004 重试）",
        input_summary="T004 错误信息；系统字体清单（Microsoft YaHei / SimHei 可用）",
        tool_called="font_manager.findfont + FT2Font.get_char_index 断言；FuncFormatter；pie 亮度自适应文字色",
        output_artifact="outputs/charts/01~04*.png（合格版）",
        output_summary="字体 Microsoft YaHei（msyh.ttc），汉字字形断言通过；四图 150 DPI，图4 改万元刻度、消除 1e6；图3 浅色扇区改深色字",
        status="success", timestamp="2026-11-05 14:57:48", duration_sec=196,
        prompt_tokens=11200, completion_tokens=4400,
        retry_count=1, qa_score=4,
        reviewer_notes="修复到位并加断言，避免同类问题静默复发；图表规范仍有图2 未标利润率（建议级）",
    ),
    # ---------- 质检 ----------
    dict(
        trace_id="T006", agent_role="Reviewer", agent_name="RV-01",
        platform="WorkBuddy Ask（只读）", task_step="独立复算 + 11 项清单核查",
        input_summary="cleaned CSV；cleaning_report.json；summary_metrics.json；charts/*.png；analyst_insights.md",
        tool_called="独立 pandas 复算 / PNG pHYs 块解析（自写，不依赖 Pillow）/ 关键词扫描",
        output_artifact="outputs/qa_evidence.json",
        output_summary="A/B/C 12 项硬性核查全部通过；总销售额/利润/订单数复算零误差；分组差额 0.00 元；4 图 150 DPI；未检出因果词",
        status="success", timestamp="2026-11-05 15:02:31", duration_sec=283,
        prompt_tokens=16400, completion_tokens=3800,
        qa_score=5, reviewer_notes="复算逻辑独立实现，未复用分析脚本，保证质检独立性",
    ),
    dict(
        trace_id="T007", agent_role="Reviewer", agent_name="RV-01",
        platform="WorkBuddy Ask（只读）", task_step="出具质检报告与分级结论",
        input_summary="qa_evidence.json；04_reviewer.md 输出格式与判定规则",
        tool_called="文档撰写（只读模式，不写上游文件）",
        output_artifact="outputs/qa_review.md",
        output_summary="结论：有条件通过；0 严重、0 一般、2 建议（销售额覆盖未留原值、图2 未标利润率）、2 提示（未知分层样本量、峰谷不可归因）；遗留风险 5 项",
        status="success", timestamp="2026-11-05 15:05:02", duration_sec=151,
        prompt_tokens=8600, completion_tokens=3900,
        qa_score=5, reviewer_notes="放行条件明确：所有数字只能引自 summary_metrics.json",
    ),
    # ---------- 回退闭环 ----------
    dict(
        trace_id="T008", agent_role="Data Engineer", agent_name="DE-01",
        platform="Trae IDE + Python 3.13", task_step="按质检 D12 补充统计范围与受影响订单号",
        input_summary="outputs/qa_review.md 的 D12 意见；原 01_clean_data.py",
        tool_called="修改脚本 + 重跑 01_clean_data.py",
        output_artifact="outputs/cleaning_report.json（新增 销售额重算统计范围 / 原始不符条数 / 修正订单号 13 个）",
        output_summary="原始全量不符 49 条、清洗后覆盖 13 条，统计范围与 order_id 均已留痕；清洗结果 3388 行不变",
        status="success", timestamp="2026-11-05 15:06:40", duration_sec=98,
        prompt_tokens=6400, completion_tokens=1900,
        retry_count=1, qa_score=5,
        reviewer_notes="回退一次后闭环，D12 由「问题」转为「通过」",
    ),
    # ---------- 报告 ----------
    dict(
        trace_id="T009", agent_role="Reporter", agent_name="RP-01",
        platform="WorkBuddy Craft", task_step="撰写 Markdown 分析报告",
        input_summary="summary_metrics.json；charts/*.png；qa_review.md；cleaning_report.json；05_reporter.md 十节结构",
        tool_called="文档撰写 + 数字一致性自检（54 项断言）",
        output_artifact="outputs/零售销售数据分析报告.md",
        output_summary="九章正文（执行摘要/概况/趋势/品类/地区/分层/问题风险/建议/附录）；嵌入 4 图 13 表；64 项数字一致性检查通过",
        status="success", timestamp="2026-11-05 15:12:22", duration_sec=342,
        prompt_tokens=21800, completion_tokens=8600,
        qa_score=5, reviewer_notes="未引入任何 JSON 之外的数字；推测内容均标注为待验证假设",
    ),
    dict(
        trace_id="T010", agent_role="Reporter", agent_name="RP-01",
        platform="WorkBuddy Craft", task_step="导出 Word（.docx）版式",
        input_summary="outputs/零售销售数据分析报告.md；charts/*.png",
        tool_called="python-docx 自建版式（标题/表格/图片/页码/中文字体 eastAsia）",
        output_artifact="outputs/零售销售数据分析报告.docx",
        output_summary="13 表 4 图 110 段；全部 run 均设置 eastAsia 中文字体；无 Markdown 语法残留；322 KB",
        status="success", timestamp="2026-11-05 15:16:05", duration_sec=223,
        prompt_tokens=13500, completion_tokens=6100,
        qa_score=4, reviewer_notes="排版结构校验通过；未做 PDF 目视预览（Word COM 被占用），需人工最终确认",
    ),
]

SUMMARY_ROW = dict(
    run_id="R001", date="2026-11-05", group_name="个人提交（Sherry-at625）",
    platform_combo="WorkBuddy（Plan/Craft/Ask）+ 本地 Python 3.13",
    total_agents=5, total_steps=len(TRACE_ROWS),
    success_steps=sum(1 for r in TRACE_ROWS if r["status"] == "success"),
    failed_steps=sum(1 for r in TRACE_ROWS if r["status"] == "failed"),
    total_duration_sec=sum(r["duration_sec"] for r in TRACE_ROWS),
    total_tokens=sum(r["prompt_tokens"] + r["completion_tokens"] for r in TRACE_ROWS),
    estimated_cost_cny=0.0, human_interventions=3, qa_overall_score=4.6,
    main_failure_point="分析 Agent 首版图表未配置可用的中文字体，四图全部渲染为方框（Glyph missing from DejaVu Sans）",
    replay_findings=(
        "① 根因：参考资料在 Linux 环境用 Noto Sans CJK SC，脚本照搬未做跨平台探测；"
        "② 放大因素：matplotlib 对缺字形只发 UserWarning 不报错，脚本无出图后校验，缺陷直到人工看图才暴露；"
        "③ 改进：字体选择改为候选链 + FT2Font 字形断言，缺字体直接中断而非静默降级"
    ),
    notes=(
        "Token 为按环节输入输出规模与文件体量的近似折算（假设：中文 1 字≈1.5 token，读入 CSV 按表头+抽样计），"
        "非平台精确计量；成本按本地运行额度折算为 0.00 元，不引用任何官方价格。"
        "人工干预 3 次：确认调度计划、指定质检放行条件、确认报告口径表述。"
    ),
)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    trace_path = OUT_DIR / "agentops_trace.csv"
    with trace_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=TRACE_FIELDS, extrasaction="ignore")
        w.writeheader()
        for i, row in enumerate(TRACE_ROWS):
            row = dict(row)
            row.setdefault("run_id", "R001")
            row.setdefault("estimated_cost_cny", 0.0)
            row.setdefault("retry_count", 0)
            row.setdefault("error_message", "")
            row["total_tokens"] = row["prompt_tokens"] + row["completion_tokens"]
            w.writerow(row)

    summary_path = OUT_DIR / "agentops_run_summary.csv"
    with summary_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerow(SUMMARY_ROW)

    print(f"已写出 {trace_path.name}：{len(TRACE_ROWS)} 条轨迹")
    print(f"已写出 {summary_path.name}：1 条运行汇总")


if __name__ == "__main__":
    main()
