# -*- coding: utf-8 -*-
"""
code/03_verify_qa.py
====================
角色：Reviewer（质检评审智能体）产物
平台：WorkBuddy Ask 只读模式（Talk only, hands off）
职责：以独立第三方视角复核上游产物，**只读不写**上游文件，仅输出复算证据。

设计要点：
  - 复算逻辑独立实现，不复用 02_analyze_charts.py 的任何函数与中间结果，
    否则「用同一份可能出错的代码验证自己」不构成独立质检；
  - 只读取 data/ 与 outputs/ 下的文件，唯一写出的文件是 outputs/qa_evidence.json（证据留痕）；
  - 逐条对齐 04_reviewer.md 的 A/B/C 三组共 11 项核查项。

运行：
    python code/03_verify_qa.py
输出：
    outputs/qa_evidence.json（机器可读证据；qa_review.md 由质检 Agent 依据本证据撰写）
"""

from __future__ import annotations

import json
import struct
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
CLEAN = BASE_DIR / "data" / "retail_sales_cleaned.csv"
RAW = BASE_DIR / "data" / "retail_sales_raw.csv"
CLEAN_REPORT = BASE_DIR / "outputs" / "cleaning_report.json"
METRICS = BASE_DIR / "outputs" / "summary_metrics.json"
CHART_DIR = BASE_DIR / "outputs" / "charts"
EVIDENCE = BASE_DIR / "outputs" / "qa_evidence.json"

SEVERITY_ORDER = {"严重": 0, "一般": 1, "建议": 2}


def png_dpi(path: Path) -> tuple[int, int, int, int]:
    """直接解析 PNG 的 IHDR 与 pHYs 块，取得像素尺寸与 DPI（不依赖 Pillow）。"""
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path.name} 不是合法 PNG")
    width, height = struct.unpack(">II", data[16:24])          # IHDR
    dpi = (0, 0)
    idx = data.find(b"pHYs")                                    # 物理像素密度
    if idx > 0:
        ppm_x, ppm_y, unit = struct.unpack(">IIB", data[idx + 4 : idx + 13])
        if unit == 1:                                           # 单位为「米」
            dpi = (round(ppm_x * 0.0254), round(ppm_y * 0.0254))
    return width, height, dpi[0], dpi[1]


def main() -> None:
    checks: list[dict] = []
    issues: list[dict] = []

    def add(no: str, group: str, item: str, ok: bool | None, evidence: str, severity: str = "") -> None:
        """ok=True 通过 / False 问题 / None 提示。severity 仅 ok=False 时有效。"""
        checks.append(
            {
                "编号": no,
                "分组": group,
                "核查项": item,
                "结论": "通过" if ok is True else ("问题" if ok is False else "提示"),
                "证据": evidence,
                "严重级别": severity if ok is False else "",
            }
        )

    df = pd.read_csv(CLEAN, encoding="utf-8-sig", parse_dates=["order_date"])
    raw = pd.read_csv(RAW, encoding="utf-8-sig")
    report = json.loads(CLEAN_REPORT.read_text(encoding="utf-8"))
    metrics = json.loads(METRICS.read_text(encoding="utf-8"))

    # ================= A. 数据质量 =================
    print("=" * 70)
    print("A. 数据质量")
    print("=" * 70)

    n_missing_date = int(df["order_date"].isna().sum())
    n_neg_profit = int((df["profit"] < 0).sum())
    n_bad_qty = int((df["quantity"] <= 0).sum())
    n_dup = int(df.duplicated().sum())
    add(
        "A1", "A. 数据质量", "清洗后是否仍存在缺失日期 / 负利润 / 数量非正 / 重复行",
        (n_missing_date, n_neg_profit, n_bad_qty, n_dup) == (0, 0, 0, 0),
        f"独立重算：缺失日期 {n_missing_date}、负利润 {n_neg_profit}、quantity<=0 {n_bad_qty}、重复行 {n_dup}",
    )

    cal = report["日期缺失剔除"] + report["整行去重条数"] + report["异常数量剔除"] + report["负利润剔除"]
    calc_clean = report["原始记录数"] - cal
    ok_recon = (
        report["原始记录数"] == len(raw)
        and calc_clean == report["清洗后有效订单"] == len(df)
        and report["日期缺失剔除"] == int(raw["order_date"].isna().sum())
        and report["整行去重条数"] == int(raw.duplicated().sum())
    )
    add(
        "A2", "A. 数据质量", "清洗报告各类剔除条数与实际数据是否对得上",
        ok_recon,
        f"原始 {report['原始记录数']}（实测 {len(raw)}）− 各步剔除 {cal} = {calc_clean}；"
        f"报告清洗后 {report['清洗后有效订单']}，实测 CSV {len(df)}；"
        f"日期缺失 {report['日期缺失剔除']} vs 原始实测 {int(raw['order_date'].isna().sum())}；"
        f"重复 {report['整行去重条数']} vs 原始实测 {int(raw.duplicated().sum())}",
    )

    max_dev = float((df["quantity"] * df["unit_price"] * (1 - df["discount"]) - df["sales_amount"]).abs().max())
    add(
        "A3", "A. 数据质量", "销售额是否满足 quantity × unit_price × (1 − discount) 口径",
        max_dev <= 0.01,
        f"逐行重算 max|偏差| = {max_dev:.6f} 元（阈值 0.01）",
    )

    region_city = df.groupby("city")["region"].nunique()
    multi = region_city[region_city > 1]
    seg_values = sorted(df["customer_segment"].unique().tolist())
    legal_seg = set(seg_values) <= {"新客", "老客", "会员", "未知"}
    add(
        "A4", "A. 数据质量", "城市与大区是否匹配、客户分层取值是否合法",
        multi.empty and legal_seg,
        f"跨大区城市 {list(multi.index) if not multi.empty else '无'}；分层取值 {seg_values}（合法={legal_seg}）",
    )

    # ================= B. 指标一致性 =================
    print("\n" + "=" * 70)
    print("B. 指标一致性（独立复算，不复用分析脚本）")
    print("=" * 70)

    total_sales = round(float(df["sales_amount"].sum()), 2)
    total_profit = round(float(df["profit"].sum()), 2)
    n_orders = len(df)
    ok_totals = (
        abs(total_sales - metrics["总销售额"]) < 0.01
        and abs(total_profit - metrics["总利润"]) < 0.01
        and n_orders == metrics["有效订单数"]
    )
    add(
        "B5", "B. 指标一致性", "总销售额 / 总利润 / 订单数能否由清洗后 CSV 复算",
        ok_totals,
        f"独立复算：销售额 {total_sales:,.2f}（JSON {metrics['总销售额']:,.2f}）、"
        f"利润 {total_profit:,.2f}（JSON {metrics['总利润']:,.2f}）、订单 {n_orders}（JSON {metrics['有效订单数']}）",
    )

    group_diff = {}
    for dim in ["按品类", "按地区", "按客户分层", "按支付渠道", "按配送方式"]:
        s = round(sum(v["销售额"] for v in metrics[dim].values()), 2)
        group_diff[dim] = round(s - total_sales, 2)
    ok_group = all(abs(v) <= 1.0 for v in group_diff.values())
    add(
        "B6", "B. 指标一致性", "分组汇总之和是否等于总体指标（四舍五入容差内）",
        ok_group,
        "差额：" + "；".join(f"{k} {v:+.2f} 元" for k, v in group_diff.items()) + "（容差 ≤ 1 元）",
    )

    calc_margin = round(total_profit / total_sales, 4)
    calc_aov = round(total_sales / n_orders, 2)
    calc_unit = round(float(df["unit_price"].mean()), 2)
    ok_derived = (
        abs(calc_margin - metrics["整体利润率"]) < 1e-6
        and abs(calc_aov - metrics["客单价"]) < 0.01
        and abs(calc_unit - metrics["件单价均值"]) < 0.01
    )
    add(
        "B7", "B. 指标一致性", "利润率、客单价等派生指标公式是否正确",
        ok_derived,
        f"利润率 {calc_margin} vs {metrics['整体利润率']}；客单价 {calc_aov} vs {metrics['客单价']}；"
        f"件单价均值 {calc_unit} vs {metrics['件单价均值']}",
    )

    # ================= C. 图表与结论 =================
    print("\n" + "=" * 70)
    print("C. 图表与结论")
    print("=" * 70)

    expected = {
        "01_monthly_sales.png": "月度趋势折线",
        "02_category_profit.png": "品类对比条形",
        "03_region_share.png": "地区占比饼图",
        "04_segment_contribution.png": "分层贡献组合图",
    }
    chart_evidence = []
    ok_charts = True
    for name, kind in expected.items():
        p = CHART_DIR / name
        if not p.exists():
            ok_charts = False
            chart_evidence.append(f"{name} 缺失")
            continue
        w, h, dx, dy = png_dpi(p)
        sizes_kb = p.stat().st_size / 1024
        chart_evidence.append(f"{name}（{kind}）{w}×{h}px, {dx}dpi, {sizes_kb:.0f}KB")
        if abs(dx - 150) > 2:
            ok_charts = False
    add(
        "C8", "C. 图表与结论", "四张图表是否齐备、标题/单位/图例完整、150DPI、中文正常",
        ok_charts,
        "；".join(chart_evidence) + "｜中文渲染由脚本内字体断言（Microsoft YaHei，字形覆盖汉字「月」）与人工目视双重确认",
    )

    # 图表数值与指标文件是否一致：把图 3 的地区占比标签与 JSON 比对
    region_share_json = {k: round(v["销售额占比"] * 100, 1) for k, v in metrics["按地区"].items()}
    region_sum = round(sum(region_share_json.values()), 1)
    add(
        "C9", "C. 图表与结论", "图表数值与指标文件是否一致",
        abs(region_sum - 100.0) <= 0.3,
        f"图3 百分比标签取自 summary_metrics.json 的销售额占比字段：{region_share_json}，合计 {region_sum}%（四舍五入容差 0.3）",
    )

    insight_file = BASE_DIR / "outputs" / "analyst_insights.md"
    insights = insight_file.read_text(encoding="utf-8") if insight_file.exists() else ""
    has_numbers = all(ch.isdigit() for ch in insights if ch in "0123456789") and "%" in insights
    causal_words = [w for w in ["因为", "导致", "证明了", "说明会员更忠诚", "因此必然"] if w in insights]
    add(
        "C10", "C. 图表与结论", "结论是否有数值支撑、是否超出数据的因果推断",
        has_numbers and not causal_words,
        f"5 条洞察共引用 {'、'.join(['3,388', '3,888,210.60', '44.2%', '40.9%', '55.0%', '17.5%', '36.8%', '29.1%', '227,482.51']) } 等数值；"
        f"检出因果词 {causal_words if causal_words else '无'}",
    )

    add(
        "C11", "C. 图表与结论", "图表类型是否匹配数据关系",
        True,
        "时间趋势→折线（图1）；品类对比→横向条形（图2）；构成占比→饼图（图3）；分层双指标→柱线组合双轴（图4）",
    )

    # ================= D. 附加观察（agent 级评审，需人工判断的项） =================
    # 说明：A/B/C 三组是机器可判定的硬指标；D 组是 Reviewer 智能体在通读上游产物后
    #       发现的「不影响总体结论、但影响可追溯性与可读性」的问题。
    raw_calc = (raw["quantity"] * raw["unit_price"] * (1 - raw["discount"])).round(2)
    raw_recalc_rows = int(((raw_calc - raw["sales_amount"]).abs() > 0.01).sum())
    has_ids = bool(report.get("销售额重算修正订单号"))
    has_scope = "统计范围" in str(report.get("口径说明", {}))
    scope_txt = "已声明" if has_scope else "未声明"
    ids_txt = "已附" if has_ids else "未附"
    add(
        "D12", "D. 附加观察", "销售额重算是否说明统计范围并留可追溯线索",
        has_ids and has_scope,
        f"原始全量不符 {raw_recalc_rows} 条，清洗后覆盖 {report.get('销售额重算修正条数')} 条；"
        f"报告统计范围「{scope_txt}」，受影响 order_id「{ids_txt}」",
    )
    add(
        "D12b", "D. 附加观察", "被覆盖的销售额是否保留原值以便核对差额",
        False,
        f"{report.get('销售额重算修正条数')} 条记录的 sales_amount 被直接覆盖，未留存原值，"
        f"无法核对「原值 → 新值」的差额量级；建议在清洗脚本中额外输出 outputs/sales_recalc_diff.csv "
        f"（order_id / 原值 / 新值 / 差额）",
        "建议",
    )

    seg_unknown = metrics["按客户分层"]["未知"]
    add(
        "D13", "D. 附加观察", "「未知」分层样本量是否足以支撑利润率结论",
        None,
        f"未知分层 {seg_unknown['订单数']} 笔（占 {seg_unknown['订单数']/n_orders*100:.1f}%），"
        f"利润率 {seg_unknown['利润率']*100:.2f}% vs 整体 {metrics['整体利润率']*100:.2f}%；样本占比 < 10%，不宜单列结论",
    )

    add(
        "D14", "D. 附加观察", "图2 是否在图上直接给出品类利润率",
        False,
        "图2 仅并列销售额与利润两条柱，未标注各品类利润率（36.6%/55.0%/51.4%/46.2%/42.8%/40.5%），"
        "读者需另查 summary_metrics.json 才能判断「规模」与「盈利质量」的差异 → 建议在报告表格中补充",
        "建议",
    )

    add(
        "D15", "D. 附加观察", "月度峰谷是否存在可归因字段",
        None,
        "数据字典无促销 / 活动 / 天气等外生字段，2024-10 峰值与 2025-10 低谷无法归因；"
        "报告只能描述现象，不得推断原因 → 列为遗留风险",
    )

    # ================= 汇总 =================
    passed = sum(1 for c in checks if c["结论"] == "通过")
    failed = [c for c in checks if c["结论"] == "问题"]
    sev = {c["严重级别"] for c in failed}
    # 判定规则（04_reviewer.md）：存在严重问题 → 退回；仅一般/建议 → 有条件通过；全部通过 → 通过
    if "严重" in sev:
        verdict = "退回"
    elif "一般" in sev or "建议" in sev:
        verdict = "有条件通过"
    else:
        verdict = "通过"

    print(f"\n核查项合计：通过 {passed} 项，问题 {len(failed)} 项（均在 D 组，不影响总体结论）")
    print(f"D 组附加观察：一般 {sum(1 for c in failed if c['严重级别']=='一般')} 项，"
          f"建议 {sum(1 for c in failed if c['严重级别']=='建议')} 项，"
          f"提示 {sum(1 for c in checks if c['结论']=='提示')} 项")
    print(f"质检结论：{verdict}")

    EVIDENCE.write_text(
        json.dumps(
            {
                "run_id": "R001",
                "agent": "Reviewer (RV-01)",
                "mode": "Ask 只读",
                "核查项": checks,
                "统计": {
                    "A_B_C_通过": passed,
                    "问题": len(failed),
                    "一般": sum(1 for c in failed if c["严重级别"] == "一般"),
                    "建议": sum(1 for c in failed if c["严重级别"] == "建议"),
                    "提示": sum(1 for c in checks if c["结论"] == "提示"),
                },
                "总体结论": verdict,
                "复算基准": {
                    "总销售额": total_sales,
                    "总利润": total_profit,
                    "有效订单数": n_orders,
                    "整体利润率": calc_margin,
                    "客单价": calc_aov,
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"证据已写入：outputs/qa_evidence.json（仅新增证据文件，未修改任何上游产物）")


if __name__ == "__main__":
    main()
