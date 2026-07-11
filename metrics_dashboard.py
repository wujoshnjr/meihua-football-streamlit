from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from evaluation import evaluate_predictions, score_tuple


def _triplet(row: pd.Series, prefix: str) -> list[tuple[int, int]]:
    names = [f"{prefix}首選比分", f"{prefix}第二選比分", f"{prefix}第三選比分"]
    values: list[tuple[int, int]] = []
    for name in names:
        parsed = score_tuple(str(row.get(name, "")))
        if parsed is not None:
            values.append(parsed)
    return values


def build_metrics_table(casebook: pd.DataFrame) -> pd.DataFrame:
    if casebook is None or casebook.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for _, row in casebook.iterrows():
        actual = str(row.get("實際比分", "")).strip()
        if not actual:
            continue
        rule_scores = _triplet(row, "規則")
        ai_scores = _triplet(row, "AI")
        final_scores = _triplet(row, "最終") or ai_scores or rule_scores
        rule = evaluate_predictions(rule_scores, actual)
        ai = evaluate_predictions(ai_scores, actual)
        final = evaluate_predictions(final_scores, actual)
        rows.append(
            {
                "案例ID": row.get("案例ID", ""),
                "比賽": row.get("比賽", ""),
                "實際比分": actual,
                "校準狀態": row.get("校準狀態", ""),
                "案例品質": row.get("案例品質", ""),
                "規則首選命中": rule["first_hit"],
                "規則三選一命中": rule["any_hit"],
                "規則勝平負命中": rule["outcome_hit"],
                "規則比分距離": rule["first_score_distance"],
                "AI首選命中": ai["first_hit"],
                "AI三選一命中": ai["any_hit"],
                "AI勝平負命中": ai["outcome_hit"],
                "AI比分距離": ai["first_score_distance"],
                "最終首選命中": final["first_hit"],
                "最終三選一命中": final["any_hit"],
                "最終勝平負命中": final["outcome_hit"],
                "最終比分距離": final["first_score_distance"],
            }
        )
    return pd.DataFrame(rows)


def _rate(series: pd.Series) -> float:
    valid = series[series.isin(["是", "否"])]
    return float((valid == "是").mean()) if len(valid) else 0.0


def render_metrics_dashboard(casebook: pd.DataFrame) -> None:
    st.subheader("模型成績與AI增益")
    metrics = build_metrics_table(casebook)
    if metrics.empty:
        st.info("尚無已輸入實際比分的案例。先到『賽後校準中心』回填結果。")
        return

    confirmed = metrics[metrics["校準狀態"].isin(["已確認", "verified", "reviewed", ""])]
    if confirmed.empty:
        confirmed = metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("已評估案例", len(confirmed))
    c2.metric("規則首選命中率", f"{_rate(confirmed['規則首選命中']):.1%}")
    c3.metric("AI首選命中率", f"{_rate(confirmed['AI首選命中']):.1%}")
    c4.metric("最終三選一命中率", f"{_rate(confirmed['最終三選一命中']):.1%}")

    ai_rows = confirmed[confirmed["AI比分距離"].apply(lambda value: isinstance(value, (int, float)))]
    if not ai_rows.empty:
        improved = (ai_rows["AI比分距離"] < ai_rows["規則比分距離"]).sum()
        worsened = (ai_rows["AI比分距離"] > ai_rows["規則比分距離"]).sum()
        equal = len(ai_rows) - improved - worsened
        st.write(f"AI相對規則：改善 {improved} 場｜惡化 {worsened} 場｜持平 {equal} 場")

    st.caption("命中率只使用已回填實際90分鐘比分的案例；規則、AI與受控最終排序分開統計。")
    st.dataframe(metrics.tail(100), width="stretch", hide_index=True)
