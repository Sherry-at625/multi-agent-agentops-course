# -*- coding: utf-8 -*-
"""
code/02_analyze_charts.py
=========================
角色：Analyst（分析可视化智能体）产物
平台：Trae IDE / SOLO + Python 终端
输入：data/retail_sales_cleaned.csv（Data Engineer 交付）
输出：outputs/summary_metrics.json、outputs/charts/01~04*.png（150 DPI）

职责边界（对应 03_analyst.md）：
  - 只做指标计算与可视化，不写最终经营报告（由 Reporter 负责）；
  - 接手先核对清洗后数据质量，存在脏数据则退回编排者，不带脏数据分析；
  - 分组之和必须与总体一致；结论只描述数据表现，不做因果归因。

运行：
    python code/02_analyze_charts.py
"""

from __future__ import annotations

import json
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 无显示环境出图
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
CLEAN_PATH = BASE_DIR / "data" / "retail_sales_cleaned.csv"
OUT_DIR = BASE_DIR / "outputs"
CHART_DIR = OUT_DIR / "charts"

# ----------------------------------------------------------------------
# 中文字体：跨平台回退链 + 运行时断言
# 修复记录（T003 退回项）：首版仅写 Noto Sans CJK SC（参考资料为 Linux 环境），
# 在 Windows 上该字体不存在，matplotlib 回落到 DejaVu Sans 并抛
# "Glyph 26376 missing from font(s) DejaVu Sans"，四张图所有中文均渲染为方框。
# 修复方式：按 Windows → macOS → Linux 顺序探测可用中文字体，取第一个存在的作为首选，
# 并在出图前断言「字体文件能够渲染汉字」，避免再次静默失败。
# ----------------------------------------------------------------------
CJK_CANDIDATES = [
    "Microsoft YaHei",   # Windows 简体中文首选
    "SimHei",            # Windows 黑体（YaHei 缺失时兜底）
    "PingFang SC",       # macOS
    "Noto Sans CJK SC",  # Linux / 课程参考资料环境
    "Source Han Sans SC",
    "WenQuanYi Zen Hei",
]


def setup_cjk_font() -> str:
    """选择第一个真实可用的中文字体，并断言其支持汉字渲染。"""
    import matplotlib.font_manager as fm

    available = {f.name for f in fm.fontManager.ttflist}
    for name in CJK_CANDIDATES:
        if name in available:
            plt.rcParams["font.sans-serif"] = [name]
            plt.rcParams["font.family"] = "sans-serif"
            plt.rcParams["axes.unicode_minus"] = False
            # 断言：字体文件确实能渲染汉字（避免「名字存在但字形缺失」的隐性失败）
            path = fm.findfont(fm.FontProperties(family=name), fallback_to_default=False)
            from matplotlib.ft2font import FT2Font

            face = FT2Font(path)
            if face.get_char_index(ord("月")) == 0:
                continue
            print(f"[字体] 使用中文字体：{name}（{Path(path).name}）")
            return name
    raise SystemExit(
        "未找到可用的中文字体，请安装 Microsoft YaHei / Noto Sans CJK SC 后重跑；"
        "不得在中文渲染为方框的情况下交付图表"
    )


CJK_FONT = setup_cjk_font()

# 统一配色（蓝色单色系 + 深色强调，避免 3D 与多余装饰）
C_MAIN = "#2563EB"
C_DARK = "#0D1326"
C_LIGHT = "#60A5FA"
C_PALE = "#BFDBFE"
C_MID = "#1E3A8A"
C_GRID = "#D9E2F1"


def pct(x: float, digits: int = 1) -> str:
    """百分比展示：小数 → 百分数，标准四舍五入（half-up）。

    修复记录（T003 退回项之二）：直接 f"{0.2905*100:.1f}" 会因二进制浮点
    把 0.2905 表示为 0.29049999… 而输出 29.0%，与参考答案的 29.1% 不符。
    改用 Decimal 的 ROUND_HALF_UP 保证展示口径与人工核算一致。
    """
    q = Decimal(1).scaleb(-digits)  # 0.1 / 0.01
    return str((Decimal(str(x)) * 100).quantize(q, rounding=ROUND_HALF_UP))


def load_and_check() -> pd.DataFrame:
    """第 1 步：核对清洗后数据质量。不达标直接退出，不带着脏数据往下做。"""
    if not CLEAN_PATH.exists():
        raise SystemExit(f"缺少输入文件：{CLEAN_PATH}，请先运行 code/01_clean_data.py")
    df = pd.read_csv(CLEAN_PATH, encoding="utf-8-sig", parse_dates=["order_date"])

    checks = {
        "文件存在": True,
        "行数 > 0": len(df) > 0,
        "无重复行": df.duplicated().sum() == 0,
        "无负利润": (df["profit"] < 0).sum() == 0,
        "数量全部为正": (df["quantity"] > 0).all(),
        "日期无缺失": df["order_date"].isna().sum() == 0,
        "分层无缺失": df["customer_segment"].isna().sum() == 0,
        "销售额口径一致": (
            (df["quantity"] * df["unit_price"] * (1 - df["discount"])).round(2)
            - df["sales_amount"]
        ).abs().max()
        < 0.011,
    }
    print("【接手核对：data/retail_sales_cleaned.csv】")
    for name, ok in checks.items():
        print(f"  {'✅' if ok else '❌'} {name}")
    if not all(checks.values()):
        raise SystemExit("清洗后数据仍存在质量问题，按要求退回编排者，不继续分析")
    print(f"  有效订单 {len(df)} 行，时间范围 {df['order_date'].min().date()} ~ {df['order_date'].max().date()}\n")
    return df


def group_metrics(df: pd.DataFrame, by: str) -> dict:
    """通用分组：订单数 / 销售额 / 利润 / 利润率 / 销售额占比，统一保留 2 位与 4 位。"""
    g = (
        df.groupby(by)
        .agg(订单数=("order_id", "count"), 销售额=("sales_amount", "sum"), 利润=("profit", "sum"))
        .round(2)
        .sort_values("销售额", ascending=False)
    )
    total_sales = float(df["sales_amount"].sum())
    g["利润率"] = (g["利润"] / g["销售额"]).round(4)
    g["销售额占比"] = (g["销售额"] / total_sales).round(4)
    out: dict[str, dict] = {}
    for k, v in g.to_dict("index").items():
        out[str(k)] = {
            "订单数": int(v["订单数"]),                       # 计数必须是整数，不能带小数
            "销售额": round(float(v["销售额"]), 2),
            "利润": round(float(v["利润"]), 2),
            "利润率": round(float(v["利润率"]), 4),
            "销售额占比": round(float(v["销售额占比"]), 4),
        }
    return out


def compute_metrics(df: pd.DataFrame) -> dict:
    """第 2 步：总体指标 + 四维分组指标 + 月度趋势。"""
    total_sales = round(float(df["sales_amount"].sum()), 2)
    total_profit = round(float(df["profit"].sum()), 2)
    n_orders = int(len(df))

    monthly = df.set_index("order_date").resample("ME")["sales_amount"].sum().round(2)
    monthly_map = {d.strftime("%Y-%m"): round(float(v), 2) for d, v in monthly.items()}

    yearly = df.groupby(df["order_date"].dt.year)["sales_amount"].sum().round(2)
    yearly_map = {str(k): round(float(v), 2) for k, v in yearly.items()}

    metrics = {
        "run_id": "R001",
        "agent": "Analyst (AN-01)",
        "source_file": "data/retail_sales_cleaned.csv",
        "时间范围": f"{df['order_date'].min().date()} ~ {df['order_date'].max().date()}",
        "有效订单数": n_orders,
        "总销售额": total_sales,
        "总利润": total_profit,
        "整体利润率": round(total_profit / total_sales, 4),
        "客单价": round(total_sales / n_orders, 2),
        "件单价均值": round(float(df["unit_price"].mean()), 2),
        "平均购买件数": round(float(df["quantity"].mean()), 2),
        "平均折扣率": round(float(df["discount"].mean()), 4),
        "口径说明": {
            "金额单位": "元，保留 2 位小数",
            "百分比": "以小数形式存储，展示时乘 100 保留 1 位（如 0.4422 → 44.2%）",
            "销售额": "sales_amount = quantity × unit_price × (1 − discount)，四舍五入 2 位",
            "利润": "profit 原始成本口径",
            "整体利润率": "总利润 / 总销售额",
            "客单价": "总销售额 / 有效订单数",
            "件单价均值": "unit_price 的算术平均（非加权）",
            "销售额占比": "分组销售额 / 总销售额，同一维度之和为 1（四舍五入误差 ≤ 0.0002）",
            "月度": "按 order_date 的月末（ME）重采样求和",
        },
        "按品类": group_metrics(df, "category"),
        "按地区": group_metrics(df, "region"),
        "按客户分层": group_metrics(df, "customer_segment"),
        "按支付渠道": group_metrics(df, "payment_channel"),
        "按配送方式": group_metrics(df, "delivery_mode"),
        "按月": monthly_map,
        "按年": yearly_map,
    }
    return metrics


def _style_axes(ax) -> None:
    """统一坐标轴风格：浅色网格、无上右边框。"""
    ax.grid(axis="y", linestyle="--", alpha=0.5, color=C_GRID)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def make_charts(df: pd.DataFrame, metrics: dict) -> list[Path]:
    """第 3 步：生成四张规范图表，PNG / 150 DPI。"""
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    produced: list[Path] = []

    # ---- 图 1：月度销售额趋势（折线 + 峰值标注）-------------------------
    monthly = df.set_index("order_date").resample("ME")["sales_amount"].sum()
    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax.plot(monthly.index, monthly.values, color=C_MAIN, linewidth=2.2, marker="o", markersize=4, label="月度销售额")
    ax.fill_between(monthly.index, monthly.values, color=C_LIGHT, alpha=0.22)
    peak_idx = monthly.idxmax()
    low_idx = monthly.idxmin()
    ax.annotate(
        f"峰值 {peak_idx.strftime('%Y-%m')}\n{monthly.max():,.0f} 元",
        xy=(peak_idx, monthly.max()),
        xytext=(-70, -34),
        textcoords="offset points",
        fontsize=9,
        color=C_DARK,
        arrowprops=dict(arrowstyle="->", color=C_DARK, lw=1),
    )
    ax.annotate(
        f"低谷 {low_idx.strftime('%Y-%m')}\n{monthly.min():,.0f} 元",
        xy=(low_idx, monthly.min()),
        xytext=(-96, 26),
        textcoords="offset points",
        fontsize=9,
        color=C_DARK,
        arrowprops=dict(arrowstyle="->", color=C_DARK, lw=1),
    )
    ax.set_title("图1  月度销售额趋势（2024-01 ~ 2025-12）", fontsize=13, color=C_DARK, pad=12)
    ax.set_xlabel("月份")
    ax.set_ylabel("销售额（元）")
    # 轴范围严格限定在数据区间内，避免 matplotlib 自动延伸到 2026-01 的空刻度
    ax.set_xlim(monthly.index.min() - pd.Timedelta(days=20), monthly.index.max())
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.legend(loc="upper left", frameon=False)
    _style_axes(ax)
    fig.tight_layout()
    p = CHART_DIR / "01_monthly_sales.png"
    fig.savefig(p, dpi=150, facecolor="white")
    plt.close(fig)
    produced.append(p)

    # ---- 图 2：品类销售额与利润对比（横向条形）---------------------------
    cat = (
        df.groupby("category")[["sales_amount", "profit"]]
        .sum()
        .sort_values("sales_amount")
    )
    fig, ax = plt.subplots(figsize=(10, 4.8))
    y = np.arange(len(cat))
    h = 0.36
    b1 = ax.barh(y + h / 2, cat["sales_amount"], height=h, label="销售额", color=C_MAIN)
    b2 = ax.barh(y - h / 2, cat["profit"], height=h, label="利润", color=C_PALE)
    for bars in (b1, b2):
        for bar in bars:
            w = bar.get_width()
            ax.text(w + 12000, bar.get_y() + bar.get_height() / 2, f"{w/10000:,.1f}万", va="center", fontsize=8, color=C_DARK)
    ax.set_yticks(y)
    ax.set_yticklabels(cat.index)
    ax.set_title("图2  各品类销售额与利润对比", fontsize=13, color=C_DARK, pad=12)
    ax.set_xlabel("金额（元）")
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v/10000:,.0f}万"))
    ax.set_xlim(0, cat["sales_amount"].max() * 1.18)
    ax.legend(frameon=False, loc="lower right")
    _style_axes(ax)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", linestyle="--", alpha=0.5, color=C_GRID)
    fig.tight_layout()
    p = CHART_DIR / "02_category_profit.png"
    fig.savefig(p, dpi=150, facecolor="white")
    plt.close(fig)
    produced.append(p)

    # ---- 图 3：地区销售额占比（饼图）------------------------------------
    region = df.groupby("region")["sales_amount"].sum().sort_values(ascending=False)
    colors = [C_MAIN, C_MID, C_LIGHT, C_PALE, "#93C5FD", "#DBEAFE"]
    fig, ax = plt.subplots(figsize=(7.6, 5.4))
    wedges, texts, autotexts = ax.pie(
        region.values,
        labels=region.index,
        autopct="%1.1f%%",
        colors=colors,
        startangle=90,
        counterclock=False,
        wedgeprops={"edgecolor": "white", "linewidth": 1.6},
        textprops={"fontsize": 11, "color": C_DARK},
        pctdistance=0.75,
    )
    for at, w in zip(autotexts, wedges):
        # 浅色扇区（如华北 #DBEAFE）用白字对比度不足，按扇区亮度切换文字颜色
        r, g_, b, _ = w.get_facecolor()
        luminance = 0.2126 * r + 0.7152 * g_ + 0.0722 * b
        at.set_color("white" if luminance < 0.62 else C_DARK)
        at.set_fontsize(10)
        at.set_fontweight("bold")
    ax.set_title("图3  各地区销售额占比", fontsize=13, color=C_DARK, pad=14)
    ax.legend(
        [f"{k}  {v/10000:,.1f} 万元" for k, v in region.items()],
        loc="center left",
        bbox_to_anchor=(1.0, 0.5),
        frameon=False,
        fontsize=10,
    )
    ax.axis("equal")
    fig.tight_layout()
    p = CHART_DIR / "03_region_share.png"
    fig.savefig(p, dpi=150, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    produced.append(p)

    # ---- 图 4：客户分层贡献（柱 + 折线组合）------------------------------
    seg = df.groupby("customer_segment")[["sales_amount", "profit"]].sum()
    seg = seg.reindex(["老客", "新客", "会员", "未知"])
    fig, ax = plt.subplots(figsize=(9, 4.8))
    x = np.arange(len(seg))
    bars = ax.bar(x, seg["sales_amount"], width=0.5, color=C_MAIN, label="销售额（左轴，万元）")
    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h * 1.015, f"{h/10000:,.1f}万",
                ha="center", va="bottom", fontsize=9, color=C_DARK)
    ax.set_ylabel("销售额（万元）")
    ax.set_ylim(0, seg["sales_amount"].max() * 1.22)
    ax.set_xticks(x)
    ax.set_xticklabels(seg.index)
    # 修复：纵轴改用「万元」刻度，避免 matplotlib 自动输出 1e6 科学计数偏移量
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v/10000:,.0f}"))

    ax2 = ax.twinx()
    ax2.plot(x, seg["profit"], color=C_DARK, marker="o", markersize=6, linewidth=2.2, label="利润（右轴，万元）", zorder=5)
    for i, (xi, v) in enumerate(zip(x, seg["profit"])):
        # 末位「未知」样本量小、柱体矮，利润标签改为下移，避免与柱顶数值标签重叠
        off = (0, 14) if v / seg["profit"].max() > 0.35 else (0, -26)
        ax2.annotate(f"{v/10000:,.1f}万", (xi, v), textcoords="offset points", xytext=off,
                     ha="center", fontsize=9, color=C_DARK,
                     bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.9))
    ax2.set_ylabel("利润（万元）")
    ax2.set_ylim(0, seg["profit"].max() * 1.35)
    ax2.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v/10000:,.0f}"))
    for side in ("top",):
        ax2.spines[side].set_visible(False)

    ax.set_title("图4  客户分层销售额与利润贡献", fontsize=13, color=C_DARK, pad=12)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, frameon=False, loc="upper right")
    _style_axes(ax)
    fig.tight_layout()
    p = CHART_DIR / "04_segment_contribution.png"
    fig.savefig(p, dpi=150, facecolor="white")
    plt.close(fig)
    produced.append(p)

    return produced


def insights(df: pd.DataFrame, m: dict) -> list[str]:
    """第 4 步：3—5 条带数值的初步洞察，每条标注口径。"""
    cat = m["按品类"]
    reg = m["按地区"]
    seg = m["按客户分层"]
    top_cat = max(cat.items(), key=lambda kv: kv[1]["销售额"])
    best_margin = max(cat.items(), key=lambda kv: kv[1]["利润率"])
    small_cat = min(cat.items(), key=lambda kv: kv[1]["销售额"])
    top3_reg = sorted(reg.items(), key=lambda kv: kv[1]["销售额"], reverse=True)[:3]
    month = m["按月"]
    peak_m = max(month.items(), key=lambda kv: kv[1])
    low_m = min(month.items(), key=lambda kv: kv[1])
    year = m["按年"]

    return [
        f"整体经营：有效订单 {m['有效订单数']:,} 笔，总销售额 {m['总销售额']:,.2f} 元"
        f"（{m['总销售额']/10000:,.1f} 万元），总利润 {m['总利润']:,.2f} 元"
        f"（{m['总利润']/10000:,.1f} 万元），整体利润率 {pct(m['整体利润率'])}%，"
        f"客单价 {m['客单价']:,.2f} 元〔口径：销售额取清洗后 CSV 求和〕",
        f"品类结构：{top_cat[0]}销售额 {top_cat[1]['销售额']/10000:,.1f} 万元、占比 {pct(top_cat[1]['销售额占比'])}%，"
        f"规模第一；{best_margin[0]}利润率 {pct(best_margin[1]['利润率'])}% 为六品类最高；"
        f"{small_cat[0]}规模最小（{pct(small_cat[1]['销售额占比'])}%）",
        f"地区分布：{'、'.join(k for k, _ in top3_reg)}位列前三，"
        f"分别占 {pct(top3_reg[0][1]['销售额占比'])}% / {pct(top3_reg[1][1]['销售额占比'])}% / {pct(top3_reg[2][1]['销售额占比'])}%；"
        f"六大区利润率区间 {pct(min(v['利润率'] for v in reg.values()))}%–{pct(max(v['利润率'] for v in reg.values()))}%，差异有限",
        f"客户分层：老客贡献销售额 {pct(seg['老客']['销售额占比'])}%、新客 {pct(seg['新客']['销售额占比'])}%、"
        f"会员 {pct(seg['会员']['销售额占比'])}%；未知分层 {seg['未知']['订单数']} 笔"
        f"（占 {pct(seg['未知']['订单数']/m['有效订单数'])}%），建议补全客户标签",
        f"时间趋势：月度峰值 {peak_m[0]}（{peak_m[1]:,.2f} 元），低谷 {low_m[0]}（{low_m[1]:,.2f} 元）；"
        f"2024 年 {year['2024']/10000:,.1f} 万元、2025 年 {year['2025']/10000:,.1f} 万元，两年基本持平"
        f"（差异 {(year['2025']-year['2024'])/year['2024']*100:+.1f}%）",
    ]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_and_check()
    metrics = compute_metrics(df)
    metrics["中文字体"] = CJK_FONT
    metrics["图表规格"] = "PNG / 150 DPI / 白底 / 标题+轴单位+图例齐全"
    charts = make_charts(df, metrics)

    (OUT_DIR / "summary_metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("【总体指标】")
    for k in ["时间范围", "有效订单数", "总销售额", "总利润", "整体利润率", "客单价", "件单价均值"]:
        v = metrics[k]
        print(f"  {k:<8}: {v}")
    print("\n【分组校验：同一维度之和应等于总体】")
    for dim in ["按品类", "按地区", "按客户分层"]:
        s = sum(v["销售额"] for v in metrics[dim].values())
        print(f"  {dim}: 分组合计 {s:,.2f} vs 总体 {metrics['总销售额']:,.2f} | 差额 {s - metrics['总销售额']:+.2f}")
    print("\n【图表产出】")
    for p in charts:
        print(f"  - {p.relative_to(BASE_DIR)}")
    print("\n【初步洞察】")
    lines = insights(df, metrics)
    for i, line in enumerate(lines, 1):
        print(f"  {i}. {line}")

    (OUT_DIR / "analyst_insights.md").write_text(
        "# Analyst 初步洞察（交付给质检 / 报告 Agent）\n\n"
        + "\n".join(f"{i}. {line}\n" for i, line in enumerate(lines, 1)),
        encoding="utf-8",
    )
    print(f"\n已输出：outputs/summary_metrics.json")
    print(f"已输出：outputs/analyst_insights.md")


if __name__ == "__main__":
    main()
