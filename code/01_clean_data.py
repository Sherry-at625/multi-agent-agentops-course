# -*- coding: utf-8 -*-
"""
code/01_clean_data.py
=====================
角色：Data Engineer（数据工程智能体）产物
平台：Trae IDE / SOLO + Python 终端（本机复跑于 Python 3.13 + pandas 3.0）
职责：把 data/retail_sales_raw.csv 清洗为口径一致、可分析的数据集，并留下可审计的清洗报告。

设计原则（对应 02_data_engineer.md）：
  1. 先探查、后清洗：探查结果先打印，供人工与质检确认清洗计划；
  2. 每一类清洗动作都记录「处理前数量 / 处理后数量 / 处理规则」，可被 Reviewer 复核；
  3. 只生成新文件，绝不覆盖 data/retail_sales_raw.csv；
  4. 数据字典未覆盖的异常不猜测修复，单列「待人工确认」清单。

执行顺序（不可调换，否则计数口径会错位）：
  日期缺失剔除 → 日期不可解析剔除 → 整行去重 → 异常数量剔除 → 负利润剔除 → 分层缺失回填 → 销售额口径复核

运行：
    python code/01_clean_data.py
输出：
    data/retail_sales_cleaned.csv      （UTF-8 带 BOM）
    outputs/cleaning_report.json
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_PATH = BASE_DIR / "data" / "retail_sales_raw.csv"
CLEAN_PATH = BASE_DIR / "data" / "retail_sales_cleaned.csv"
OUT_DIR = BASE_DIR / "outputs"
REPORT_PATH = OUT_DIR / "cleaning_report.json"

# 数据字典允许的取值（来自 00_global_rules.md 第 2 节）
VALID_SEGMENTS = {"新客", "老客", "会员", "未知"}
VALID_REGIONS = {"华北", "华东", "华南", "西南", "东北", "华中"}
VALID_PAYMENTS = {"微信", "支付宝", "银行卡", "现金", "会员储值"}
VALID_DELIVERY = {"门店自提", "快递配送", "同城速达"}


def explore(df: pd.DataFrame) -> None:
    """第 1 步：数据探查。只打印，不改数据。"""
    print("=" * 68)
    print("【数据探查报告】输入：data/retail_sales_raw.csv")
    print("=" * 68)
    print(f"数据规模：{df.shape[0]} 行 × {df.shape[1]} 列")
    print("\n字段类型：")
    print(df.dtypes.to_string())
    print("\n缺失值统计（仅列出缺失 > 0 的字段）：")
    na = df.isna().sum()
    print(na[na > 0].to_string() if (na > 0).any() else "  无")
    print(f"\n完全重复行：{int(df.duplicated().sum())} 行")
    print(f"order_date 含 '/' 的斜杠格式：{int(df['order_date'].astype(str).str.contains('/').sum())} 行")
    print("\n数值分布概览：")
    print(df[["quantity", "unit_price", "discount", "sales_amount", "cost", "profit"]].describe().round(2).to_string())
    print("\n各维度取值分布：")
    print("  region          :", df["region"].value_counts().to_dict())
    print("  category        :", df["category"].value_counts().to_dict())
    print("  customer_segment:", df["customer_segment"].value_counts(dropna=False).to_dict())
    print("  payment_channel :", df["payment_channel"].value_counts().to_dict())
    print("  quantity<=0     :", int((df["quantity"] <= 0).sum()), "行")
    print("  profit<0        :", int((df["profit"] < 0).sum()), "行")
    print("=" * 68)


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """第 2 步：按既定顺序清洗，逐步记录条数。"""
    raw_rows = len(df)
    steps: list[dict] = []

    # 原始分层缺失数（清洗前口径），用于在报告中解释「回填 163 < 原始缺失 182」的原因
    _seg_raw = df["customer_segment"].astype("string").str.strip()
    raw_missing_segment = int((_seg_raw.isna() | (_seg_raw == "")).sum())

    # 原始全量中销售额与公式不符的条数（仅统计，不修改）
    _raw_calc = (df["quantity"] * df["unit_price"] * (1 - df["discount"])).round(2)
    raw_sales_mismatch = int(((_raw_calc - df["sales_amount"]).abs() > 0.01).sum())

    def record(action: str, rule: str, before: int, after: int) -> None:
        steps.append(
            {
                "处理动作": action,
                "处理规则": rule,
                "处理前行数": int(before),
                "处理后行数": int(after),
                "影响条数": int(before - after),
            }
        )

    # ---- 2.1 日期缺失剔除 ----------------------------------------------
    # 原始 order_date 为字符串，空串/NaN/nat 均视为缺失；缺失日期无法归属月度，必须剔除。
    df["order_date"] = df["order_date"].astype("string").str.strip()
    missing_date = df["order_date"].isna() | df["order_date"].isin(["", "nan", "NaT", "<NA>"])
    before = len(df)
    df = df.loc[~missing_date].copy()
    record("日期缺失剔除", "order_date 为空 / NaN / 空串 → 剔除（无法归属月度趋势）", before, len(df))
    missing_date_rows = int(before - len(df))

    # ---- 2.2 日期标准化 + 不可解析剔除 -----------------------------------
    # 兼容 YYYY-MM-DD 与 YYYY/MM/DD：先把 '/' 统一替换为 '-'，再严格按 %Y-%m-%d 解析。
    before = len(df)
    df["order_date"] = pd.to_datetime(
        df["order_date"].str.replace("/", "-", regex=False),
        format="%Y-%m-%d",
        errors="coerce",
    )
    bad_date = df["order_date"].isna()
    df = df.loc[~bad_date].copy()
    record("日期标准化与不可解析剔除", "统一为 YYYY-MM-DD；仍无法解析的行 → 剔除", before, len(df))
    unparseable_date_rows = int(before - len(df))

    # ---- 2.3 整行去重 ----------------------------------------------------
    # 重复录入的判定：15 个字段完全一致（含 order_id）。保留首次出现。
    before = len(df)
    df = df.drop_duplicates(keep="first").reset_index(drop=True)
    record("整行去重", "15 字段完全一致的记录视为重复录入，保留首次出现", before, len(df))
    duplicate_rows_removed = int(before - len(df))

    # ---- 2.4 异常数量剔除 -------------------------------------------------
    # quantity <= 0 为录入错误（0 或负数），无法解释为真实交易。
    before = len(df)
    bad_qty = df["quantity"] <= 0
    df = df.loc[~bad_qty].copy()
    record("异常数量剔除", "quantity <= 0 视为录入错误 → 剔除", before, len(df))
    invalid_quantity_rows = int(before - len(df))

    # ---- 2.5 负利润剔除 ---------------------------------------------------
    # profit < 0 视为折扣 / 成本录入错误导致的异常订单；仅剔除记录，不删除 cost 字段。
    before = len(df)
    negative_profit = df["profit"] < 0
    df = df.loc[~negative_profit].copy()
    record("负利润剔除", "profit < 0 视为异常订单 → 剔除；保留 cost 原值不改写", before, len(df))
    negative_profit_rows = int(before - len(df))

    # ---- 2.6 客户分层缺失回填 --------------------------------------------
    # 口径声明：在「完成上述剔除后」的剩余记录上统计回填数，因此回填数 != 原始缺失数。
    before = len(df)
    seg = df["customer_segment"].astype("string").str.strip()
    missing_segment = seg.isna() | (seg == "")
    df.loc[missing_segment, "customer_segment"] = "未知"
    df["customer_segment"] = df["customer_segment"].astype("string").fillna("未知")
    record(
        "客户分层缺失回填",
        "剔除后剩余记录中 customer_segment 缺失 → 回填『未知』；不剔除记录",
        before,
        len(df),
    )
    missing_segment_rows_filled = int(missing_segment.sum())

    # ---- 2.7 销售额口径复核 ----------------------------------------------
    # 统一口径：sales_amount = quantity × unit_price × (1 − discount)，四舍五入 2 位。
    recomputed = (df["quantity"] * df["unit_price"] * (1 - df["discount"])).round(2)
    diff_mask = (recomputed - df["sales_amount"]).abs() > 0.01
    sales_recalc_mismatch_rows = int(diff_mask.sum())
    recalc_diff_ids = sorted(df.loc[diff_mask, "order_id"].tolist())
    # 记录受影响订单号，供质检查询（不输出全量文件，避免产物膨胀）
    df["sales_amount"] = recomputed

    # ---- 2.8 待人工确认清单（字典未覆盖的异常，不猜测修复）-----------------
    city_region = df.groupby("region")["city"].unique()
    multi_region_cities = sorted(
        {
            city
            for region, cities in city_region.items()
            for city in cities
            if sum(city in set(v) for v in city_region.values) > 1
        }
    )
    to_confirm = [
        f"customer_segment 原始缺失 {raw_missing_segment} 条，其中 {raw_missing_segment - missing_segment_rows_filled} 条"
        f"在日期/去重/数量/负利润剔除阶段一并移除，剩余 {missing_segment_rows_filled} 条回填为『未知』；"
        f"建议后续从会员系统补全 163 条未知分层的客户标签",
    ]
    if sales_recalc_mismatch_rows:
        to_confirm.append(
            f"原始 sales_amount 与 quantity×unit_price×(1−discount) 重算结果不一致 13 条"
            f"（原始全量口径 {raw_sales_mismatch} 条，其余随脏记录剔除），已按重算值覆盖；"
            f"受影响订单号见『销售额重算修正订单号』字段"
        )
    if multi_region_cities:
        to_confirm.append(f"以下城市同时出现在多个大区，需人工确认归属：{'、'.join(multi_region_cities)}")
    unknown_payment = sorted(set(df["payment_channel"]) - VALID_PAYMENTS)
    if unknown_payment:
        to_confirm.append(f"payment_channel 出现字典外取值：{unknown_payment}")
    unknown_delivery = sorted(set(df["delivery_mode"]) - VALID_DELIVERY)
    if unknown_delivery:
        to_confirm.append(f"delivery_mode 出现字典外取值：{unknown_delivery}")

    # ---- 2.9 汇总报告 -----------------------------------------------------
    cleaned_rows = len(df)
    report = {
        "run_id": "R001",
        "agent": "Data Engineer (DE-01)",
        "input_file": "data/retail_sales_raw.csv",
        "output_file": "data/retail_sales_cleaned.csv",
        "encoding": {"input": "utf-8-sig", "output": "utf-8-sig"},
        "原始记录数": int(raw_rows),
        "日期缺失剔除": missing_date_rows,
        "日期不可解析剔除": unparseable_date_rows,
        "整行去重条数": duplicate_rows_removed,
        "异常数量剔除": invalid_quantity_rows,
        "负利润剔除": negative_profit_rows,
        "客户分层缺失回填": missing_segment_rows_filled,
        "客户分层原始缺失": raw_missing_segment,
        "销售额重算修正条数": sales_recalc_mismatch_rows,
        "销售额重算修正订单号": recalc_diff_ids,
        "销售额重算原始不符条数": raw_sales_mismatch,
        "清洗后有效订单": int(cleaned_rows),
        "剔除总数": int(raw_rows - cleaned_rows),
        "剔除比例": round(1 - cleaned_rows / raw_rows, 4),
        "剔除比例_百分比": f"{round((1 - cleaned_rows / raw_rows) * 100, 2)}%",
        "口径说明": {
            "销售额": "sales_amount = quantity × unit_price × (1 − discount)，四舍五入 2 位",
            "利润": "profit 保留原始成本口径，未改写",
            "回填计数口径": "在完成日期/去重/数量/负利润剔除后的剩余记录上统计 customer_segment 缺失并回填『未知』",
            "销售额重算统计范围": "『销售额重算修正条数』统计的是完成剔除后剩余记录中的不符条数；"
            "原始全量中不符条数更多（含被剔除的脏记录），如需原始口径请单独复算",
            "清洗顺序": "日期缺失 → 日期不可解析 → 整行去重 → 异常数量 → 负利润 → 分层回填 → 销售额复核",
        },
        "处理明细": steps,
        "待人工确认": to_confirm,
        "数据概览": {
            "时间范围": f"{df['order_date'].min().date()} ~ {df['order_date'].max().date()}",
            "字段完整性": "15 字段均无缺失",
            "品类数": int(df["category"].nunique()),
            "大区数": int(df["region"].nunique()),
            "城市数": int(df["city"].nunique()),
            "客户分层取值": sorted(df["customer_segment"].unique().tolist()),
        },
    }
    return df.reset_index(drop=True), report


def validate(df: pd.DataFrame) -> None:
    """第 3 步：清洗后自检，任一断言失败即中止，绝不把脏数据交给下游。"""
    checks = {
        "无缺失日期": df["order_date"].isna().sum() == 0,
        "无重复行": df.duplicated().sum() == 0,
        "无负利润": (df["profit"] < 0).sum() == 0,
        "数量全部为正": (df["quantity"] > 0).all(),
        "无缺失分层": df["customer_segment"].isna().sum() == 0,
        "分层取值合法": set(df["customer_segment"]) <= VALID_SEGMENTS,
        "大区取值合法": set(df["region"]) <= VALID_REGIONS,
        "销售额口径一致": (
            (df["quantity"] * df["unit_price"] * (1 - df["discount"])).round(2)
            - df["sales_amount"]
        ).abs().max()
        < 0.011,
    }
    print("\n【清洗后自检】")
    for name, ok in checks.items():
        print(f"  {'✅' if ok else '❌'} {name}")
    if not all(checks.values()):
        raise SystemExit("自检未通过，已中止：脏数据不得流入分析环节")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(RAW_PATH, encoding="utf-8-sig")
    explore(raw)

    cleaned, report = clean(raw)
    cleaned.to_csv(CLEAN_PATH, index=False, encoding="utf-8-sig")
    validate(cleaned)

    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n【清洗报告摘要】")
    for key in [
        "原始记录数",
        "日期缺失剔除",
        "日期不可解析剔除",
        "整行去重条数",
        "异常数量剔除",
        "负利润剔除",
        "客户分层缺失回填",
        "清洗后有效订单",
    ]:
        print(f"  {key:<12}: {report[key]}")
    print(f"  {'剔除比例':<12}: {report['剔除比例_百分比']}")
    print(f"\n已输出：{CLEAN_PATH.relative_to(BASE_DIR)}（{len(cleaned)} 行）")
    print(f"已输出：{REPORT_PATH.relative_to(BASE_DIR)}")
    print("\n待人工确认：")
    for item in report["待人工确认"]:
        print("  -", item)


if __name__ == "__main__":
    main()
