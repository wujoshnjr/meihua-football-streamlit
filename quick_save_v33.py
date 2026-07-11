from __future__ import annotations

from typing import Any

import streamlit as st

from config import load_config
from report_builder_v33 import build_markdown_report
from storage_v33 import CaseStore, build_case_row, save_report


def _load_config_and_store() -> tuple[Any, CaseStore]:
    try:
        secrets = dict(st.secrets)
    except Exception:
        secrets = {}
    config = load_config(secrets)
    return config, CaseStore(config)


def render_quick_save() -> None:
    """在側邊欄永久顯示賽前預測儲存入口。

    原本儲存按鈕放在「報告與鎖定」分頁，使用者容易找不到。
    這裡直接使用 session_state 內已完成的預測結果，寫入同一個 GitHub 案例庫。
    """
    with st.sidebar:
        st.divider()
        st.subheader("賽前預測儲存")

        required = ["match_input", "hexagram_result", "rule_prediction"]
        ready = all(key in st.session_state for key in required)
        if not ready:
            st.caption("完成一次賽前預測後，這裡會出現可用的儲存按鈕。")
            st.button(
                "鎖定並儲存賽前預測",
                key="quick_save_v33_disabled",
                type="primary",
                width="stretch",
                disabled=True,
            )
            return

        saved_match = st.session_state["match_input"]
        result = st.session_state["hexagram_result"]
        rule_prediction = st.session_state["rule_prediction"]
        similar_cases = st.session_state.get("similar_cases", [])
        ai_analysis = st.session_state.get("ai_analysis")
        save_mode = st.session_state.get("save_mode", "自動更新")

        st.caption(f"目前待儲存：{result.match_name}")
        scores = "、".join(f"{a}-{b}" for a, b in rule_prediction.scores[:3])
        st.caption(f"規則三選：{scores}")

        if st.button(
            "鎖定並儲存賽前預測",
            key="quick_save_v33_active",
            type="primary",
            width="stretch",
            help="把目前的賽前輸入、卦象、規則預測、AI結果與相似案例寫入GitHub案例庫。",
        ):
            try:
                config, store = _load_config_and_store()
                report = build_markdown_report(
                    saved_match,
                    result,
                    rule_prediction,
                    similar_cases,
                    ai_analysis=ai_analysis,
                )
                report_path = save_report(config, result, report)
                row = build_case_row(
                    saved_match,
                    result,
                    rule_prediction,
                    ai_analysis,
                    similar_cases,
                    actual_score="",
                    calibration_reason="",
                    calibration_summary="賽前預測已鎖定，尚未回填實際比分。",
                    confirmed_ai_calibration=False,
                    report_path=report_path,
                )
                updated, action = store.upsert(row, save_mode)
                st.session_state["casebook_df"] = updated
                st.session_state["last_saved_match"] = result.match_name
                st.session_state["last_saved_action"] = action
                st.success(f"已{action}並鎖定：{result.match_name}")
                st.caption("現在可在賽後到『賽後校準中心』選擇這場比賽並回填90分鐘實際比分。")
            except Exception as exc:
                st.exception(exc)

        last_saved = str(st.session_state.get("last_saved_match", "")).strip()
        if last_saved:
            action = str(st.session_state.get("last_saved_action", "已儲存"))
            st.info(f"最近儲存：{last_saved}（{action}）")
