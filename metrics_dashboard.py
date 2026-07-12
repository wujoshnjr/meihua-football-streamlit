from __future__ import annotations

from typing import Any, Mapping

import pandas as pd
import streamlit as st

from evaluation import evaluate_predictions, outcome_brier, outcome_log_loss, score_tuple


def _triplet(row: Mapping[str, Any], prefix: str) -> list[tuple[int, int]]:
    names = [f"{prefix}首選比分", f"{prefix}第二選比分", f"{prefix}第三選比分"]
    values: list[tuple[int, int]] = []
    for name in names:
        parsed = score_tuple(str(row.get(name, "")))
        if parsed is not None:
            values.append(parsed)
    return values


def _legacy_triplet(row: Mapping[str, Any]) -> list[tuple[int, int]]:
    values: list[tuple[int, int]] = []
    for name in ["首選比分", "第二選比分", "第三選比分"]:
        parsed = score_tuple(str(row.get(name, "")))
        if parsed is not None:
            values.append(parsed)
    return values


def _probabilities(row: Mapping[str, Any], prefix: str) -> dict[str, Any]:
    return {
        "體方勝": row.get(f"{prefix}體勝機率", ""),
        "平局": row.get(f"{prefix}平局機率", ""),
        "用方勝": row.get(f"{prefix}用勝機率", ""),
    }


def build_metrics_table(casebook: pd.DataFrame) -> pd.DataFrame:
    if casebook is None or casebook.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for _, series in casebook.iterrows():
        row = series.to_dict()
        actual = str(row.get("實際比分", "")).strip()
        if not actual:
            continue
        legacy_scores = _legacy_triplet(row)
        baseline_scores = _triplet(row, "足球基線")
        rule_scores = _triplet(row, "規則") or legacy_scores
        ai_scores = _triplet(row, "AI")
        final_scores = _triplet(row, "最終") or ai_scores or rule_scores
        baseline = evaluate_predictions(baseline_scores, actual)
        rule = evaluate_predictions(rule_scores, actual)
        ai = evaluate_predictions(ai_scores, actual)
        final = evaluate_predictions(final_scores, actual)
        baseline_probabilities = _probabilities(row, "足球基線")
        rule_probabilities = _probabilities(row, "規則")
        baseline_brier = outcome_brier(baseline_probabilities, actual)
        rule_brier = outcome_brier(rule_probabilities, actual)
        baseline_log_loss = outcome_log_loss(baseline_probabilities, actual)
        rule_log_loss = outcome_log_loss(rule_probabilities, actual)
        hexagram_improvement = "未比較"
        if baseline_brier is not None and rule_brier is not None:
            hexagram_improvement = "改善" if rule_brier < baseline_brier else ("惡化" if rule_brier > baseline_brier else "持平")

        rows.append(
            {
                "案例ID": row.get("案例ID", ""),
                "比賽": row.get("比賽", ""),
                "實際比分": actual,
                "校準狀態": row.get("校準狀態", ""),
                "案例品質": row.get("案例品質", ""),
                "鎖定狀態": row.get("鎖定狀態", ""),
                "系統版本": row.get("系統版本", "") or row.get("引擎版本", "") or "legacy",
                "足球基線首選命中": baseline["first_hit"],
                "足球基線三選一命中": baseline["any_hit"],
                "足球基線勝平負命中": baseline["outcome_hit"],
                "足球基線比分距離": baseline["first_score_distance"],
                "足球基線Brier": baseline_brier,
                "足球基線LogLoss": baseline_log_loss,
                "規則首選命中": rule["first_hit"],
                "規則三選一命中": rule["any_hit"],
                "規則勝平負命中": rule["outcome_hit"],
                "規則比分距離": rule["first_score_distance"],
                "卦象調整Brier": rule_brier,
                "卦象調整LogLoss": rule_log_loss,
                "卦象是否改善": hexagram_improvement,
                "AI首選命中": ai["first_hit"],
                "AI三選一命中": ai["any_hit"],
                "AI勝平負命中": ai["outcome_hit"],
                "AI比分距離": ai["first_score_distance"],
                "最終首選命中": final["first_hit"],
                "最終三選一命中": final["any_hit"],
                "最終勝平負命中": final["outcome_hit"],
                "最終比分距離": final["first_score_distance"],
                "最終BTTS命中": final["btts_hit"],
                "最終大小2.5命中": final["over_2_5_hit"],
            }
        )
    return pd.DataFrame(rows)


def _rate(series: pd.Series) -> float | None:
    valid = series[series.isin(["是", "否"])]
    return float((valid == "是").mean()) if len(valid) else None


def _rate_text(series: pd.Series) -> str:
    value = _rate(series)
    return "—" if value is None else f"{value:.1%}"


def _numeric_mean(series: pd.Series) -> float | None:
    values = pd.to_numeric(series, errors="coerce").dropna()
    return float(values.mean()) if len(values) else None


def render_metrics_dashboard(casebook: pd.DataFrame) -> None:
    st.subheader("模型成績、盲測與卦象增益")
    metrics = build_metrics_table(casebook)
    if metrics.empty:
        st.info("尚無已輸入實際90分鐘比分的案例。先到『賽後校準中心』回填結果。")
        return

    confirmed = metrics[metrics["校準狀態"].isin(["已確認", "verified", "reviewed", ""])]
    if confirmed.empty:
        confirmed = metrics
    v4_locked = confirmed[
        confirmed["系統版本"].astype(str).str.startswith("4")
        & confirmed["鎖定狀態"].astype(str).eq("已鎖定")
    ]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("已評估案例", len(confirmed))
    c2.metric("足球基線勝平負", _rate_text(confirmed["足球基線勝平負命中"]))
    c3.metric("卦象調整勝平負", _rate_text(confirmed["規則勝平負命中"]))
    c4.metric("最終首選命中", _rate_text(confirmed["最終首選命中"]))
    c5.metric("最終三選一命中", _rate_text(confirmed["最終三選一命中"]))

    if v4_locked.empty:
        st.warning("目前尚無『v4、賽前已鎖定、賽後已回填』的盲測樣本；舊案例只列為歷史參考，不代表v4成績。")
    else:
        baseline_brier = _numeric_mean(v4_locked["足球基線Brier"])
        adjusted_brier = _numeric_mean(v4_locked["卦象調整Brier"])
        improved = int((v4_locked["卦象是否改善"] == "改善").sum())
        worsened = int((v4_locked["卦象是否改善"] == "惡化").sum())
        equal = len(v4_locked) - improved - worsened
        st.success(
            f"v4盲測 {len(v4_locked)} 場｜卦象相對足球Brier：改善 {improved}、惡化 {worsened}、持平/未比較 {equal}｜"
            f"足球平均Brier {'—' if baseline_brier is None else f'{baseline_brier:.3f}'}｜"
            f"卦象平均Brier {'—' if adjusted_brier is None else f'{adjusted_brier:.3f}'}"
        )

    ai_rows = confirmed[pd.to_numeric(confirmed["AI比分距離"], errors="coerce").notna()]
    if not ai_rows.empty:
        ai_distance = pd.to_numeric(ai_rows["AI比分距離"], errors="coerce")
        rule_distance = pd.to_numeric(ai_rows["規則比分距離"], errors="coerce")
        improved = int((ai_distance < rule_distance).sum())
        worsened = int((ai_distance > rule_distance).sum())
        equal = len(ai_rows) - improved - worsened
        st.write(f"AI相對卦象規則比分距離：改善 {improved} 場｜惡化 {worsened} 場｜持平 {equal} 場")

    st.caption(
        "足球基線、卦象調整、AI與最終排序分開評估。Brier與LogLoss只比較賽前已保存的勝平負機率；"
        "單場產生的卦象假說不會直接取得預測權重。"
    )
    st.download_button(
        "下載完整評估CSV",
        data=metrics.to_csv(index=False, lineterminator="\n").encode("utf-8-sig"),
        file_name="meihua_model_metrics.csv",
        mime="text/csv",
        width="stretch",
    )
    display_columns = [
        "比賽", "實際比分", "系統版本", "足球基線勝平負命中", "規則勝平負命中",
        "最終首選命中", "最終三選一命中", "足球基線Brier", "卦象調整Brier", "卦象是否改善",
    ]
    table_rows = [
        "| " + " | ".join(display_columns) + " |",
        "|" + "|".join(["---"] * len(display_columns)) + "|",
    ]
    for _, row in metrics.tail(50).iterrows():
        values = [str(row.get(column, "")).replace("|", "／").replace("\n", " ") for column in display_columns]
        table_rows.append("| " + " | ".join(values) + " |")
    st.markdown("\n".join(table_rows))


__all__ = ["build_metrics_table", "render_metrics_dashboard"]
