from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from ai_reasoner_v33 import GitHubModelsClient, run_postmatch_calibration_from_row
from config import AppConfig
from evaluation import calibration_summary_from_row, normalize_score
from storage_v32 import CaseStore


def _case_label(row: pd.Series) -> str:
    status = str(row.get("校準狀態", "") or "未輸入")
    actual = str(row.get("實際比分", "") or "待回填")
    return f"{row.get('比賽', '')}｜{row.get('案例ID', '')}｜{status}｜實際 {actual}"


def render_calibration_center(config: AppConfig, store: CaseStore, casebook: pd.DataFrame) -> pd.DataFrame:
    st.subheader("賽後校準中心")
    st.caption("從GitHub案例庫選擇不可覆寫的賽前版本，回填90分鐘結果；不依賴目前瀏覽器Session，也不改寫原預測。")
    if casebook is None or casebook.empty:
        st.info("案例庫目前為空。請先在『賽前預測』儲存一場比賽。")
        return casebook

    candidates = casebook[casebook["案例ID"].astype(str).str.strip().ne("")].copy()
    if candidates.empty:
        st.warning("舊案例沒有案例ID。請先重新讀取案例庫，系統會自動遷移。")
        return casebook

    options = list(candidates.index)
    selected_index = st.selectbox(
        "選擇要回填結果的比賽",
        options,
        format_func=lambda index: _case_label(candidates.loc[index]),
        key="calibration_case_selector",
    )
    row = candidates.loc[selected_index]
    case_id = str(row.get("案例ID", "")).strip()

    p1, p2, p3, p4 = st.columns(4)
    p1.metric("規則首選", str(row.get("規則首選比分", "") or row.get("首選比分", "") or "—"))
    p2.metric("AI首選", str(row.get("AI首選比分", "") or "—"))
    p3.metric("最終首選", str(row.get("最終首選比分", "") or row.get("AI首選比分", "") or row.get("規則首選比分", "") or "—"))
    p4.metric("卦勢鏈", f"{row.get('本卦', '')}→{row.get('互卦', '')}→{row.get('變卦', '')}")

    default_actual = str(row.get("實際比分", "") or "")
    default_reason = str(row.get("校準原因", "") or "")
    default_quality = str(row.get("案例品質", "") or "中")
    if default_quality not in {"高", "中", "低"}:
        default_quality = "中"

    with st.form("postmatch_result_form", clear_on_submit=False):
        actual_score = st.text_input("實際90分鐘比分", value=default_actual, placeholder="例如 2-1")
        manual_reason = st.text_area(
            "人工校準原因",
            value=default_reason,
            height=150,
            placeholder="原判、實際、偏差、本互動變原因、下次可泛化修正。",
        )
        quality = st.selectbox("案例品質", ["高", "中", "低"], index=["高", "中", "低"].index(default_quality))
        save_as_confirmed = st.checkbox("人工校準內容已確認，可供下一場相似案例檢索", value=bool(default_reason))
        submitted = st.form_submit_button("儲存實際比分與人工校準", type="primary", width="stretch")

    if submitted:
        normalized = normalize_score(actual_score)
        if not normalized:
            st.error("比分格式錯誤，請輸入例如 2-1。")
        else:
            summary = calibration_summary_from_row(row.to_dict(), normalized)
            status = "已確認" if save_as_confirmed and manual_reason.strip() else "待確認"
            updated, info = store.update_postmatch(
                case_id=case_id,
                actual_score=normalized,
                calibration_reason=manual_reason,
                calibration_summary=summary,
                calibration_status=status,
                case_quality=quality,
                confirmed_ai=False,
            )
            st.session_state["casebook_df"] = updated
            st.success(f"已更新 {info['case_id']}：實際比分 {normalized}，狀態 {status}。")
            casebook = updated
            row = pd.Series(store.get_by_id(case_id) or row.to_dict())

    st.markdown("#### AI賽後建議（選用）")
    actual_for_ai = str(row.get("實際比分", "") or "")
    review_for_ai = str(row.get("校準原因", "") or "")
    if not actual_for_ai:
        st.info("先儲存實際比分，才能要求AI產生賽後建議。")
    elif not config.use_ai:
        st.info("GitHub Models AI未啟用；人工校準仍可正常使用。")
    else:
        if st.button("讓AI分析此案例的賽後偏差", key=f"ai_postmatch_{case_id}"):
            try:
                client = GitHubModelsClient(
                    token=config.github_models_token,
                    model=config.ai_model,
                    timeout=config.request_timeout_seconds,
                    max_tokens=config.ai_max_output_tokens,
                    temperature=0.1,
                )
                st.session_state["postmatch_center_ai"] = run_postmatch_calibration_from_row(
                    client, row.to_dict(), actual_for_ai, review_for_ai
                )
                st.success("AI賽後建議已產生，尚未寫入正式校準。")
            except Exception as exc:
                st.error(str(exc))

    ai_payload: dict[str, Any] | None = st.session_state.get("postmatch_center_ai")
    if ai_payload:
        st.json(ai_payload, expanded=True)
        with st.form("confirm_ai_postmatch_form"):
            confirm = st.checkbox("我已閱讀，確認將AI建議合併到此案例")
            confirmed = st.form_submit_button("確認並寫回AI校準", width="stretch")
        if confirmed:
            if not confirm:
                st.warning("請先勾選人工確認。")
            else:
                suggested_reason = str(ai_payload.get("suggested_calibration_reason", "")).strip()
                lesson = str(ai_payload.get("generalizable_lesson", "")).strip()
                merged_reason = "\n".join(x for x in [review_for_ai, suggested_reason] if x).strip()
                summary = lesson or calibration_summary_from_row(row.to_dict(), actual_for_ai)
                updated, _ = store.update_postmatch(
                    case_id=case_id,
                    actual_score=actual_for_ai,
                    calibration_reason=merged_reason,
                    calibration_summary=summary,
                    calibration_status="已確認",
                    case_quality=str(row.get("案例品質", "") or "中"),
                    ai_calibration=ai_payload,
                    confirmed_ai=True,
                )
                st.session_state["casebook_df"] = updated
                st.session_state.pop("postmatch_center_ai", None)
                st.success("AI校準已經人工確認並寫回GitHub案例庫。")
                casebook = updated
    return casebook
