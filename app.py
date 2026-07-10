from __future__ import annotations

import hashlib
import json
from typing import Any

import pandas as pd
import streamlit as st

from ai_reasoner import GitHubModelsClient, PROMPT_VERSION, run_ai_prediction, run_postmatch_calibration
from case_memory import retrieve_similar_cases
from config import load_config
from evaluation import final_scores, local_calibration_summary, normalize_score
from knowledge_loader import load_calibration_rules, load_hexagrams, load_trigrams
from meihua_engine import calculate_match_hexagram
from models import AIAnalysis, MatchInput
from report_builder import build_markdown_report
from score_engine import predict_scores
from storage import CaseStore, build_case_row, save_report, safe_filename


st.set_page_config(page_title="梅花易數足球AI自主推理系統 v3.1", page_icon="☯️", layout="wide")

try:
    _secrets = dict(st.secrets)
except Exception:
    _secrets = {}
CONFIG = load_config(_secrets)
STORE = CaseStore(CONFIG)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.4rem; padding-bottom: 3rem;}
    .small-note {font-size: 0.9rem; opacity: 0.8;}
    div[data-testid="stMetric"] {border: 1px solid rgba(128,128,128,.25); padding: .7rem; border-radius: .7rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


def _load_casebook(force: bool = False) -> pd.DataFrame:
    if force or "casebook_df" not in st.session_state:
        try:
            st.session_state["casebook_df"] = STORE.load()
            st.session_state.pop("casebook_error", None)
        except Exception as exc:
            st.session_state["casebook_df"] = pd.DataFrame()
            st.session_state["casebook_error"] = str(exc)
    return st.session_state["casebook_df"]


def _match_signature(match: MatchInput) -> str:
    payload = json.dumps(match.to_dict(), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _score_text(score: tuple[int, int]) -> str:
    return f"{score[0]}-{score[1]}"


def _validate_match(match: MatchInput) -> list[str]:
    fields = {
        "比賽名稱": match.match_name,
        "體方": match.body_team,
        "用方": match.use_team,
        "體方段落": match.body_text,
        "用方段落": match.use_text,
        "完整賽前中性介紹段落": match.full_text,
    }
    return [name for name, value in fields.items() if not str(value).strip()]


def _current_ai_model() -> str:
    return str(st.session_state.get("ai_model_override", CONFIG.ai_model)).strip() or CONFIG.ai_model


casebook_df = _load_casebook()

with st.sidebar:
    st.header("比賽與後台")
    competition = st.text_input("賽事", value="")
    match_name = st.text_input("比賽名稱", value="阿根廷 vs 埃及")
    body_team = st.text_input("體方", value="阿根廷")
    use_team = st.text_input("用方", value="埃及")
    prematch_leaning = st.text_input("賽前偏向", value="支持阿根廷，因此阿根廷為體")
    scope = st.selectbox("判斷範圍", ["90分鐘，不含延長賽與PK"], index=0)
    save_mode = st.radio("案例儲存模式", ["自動更新", "強制新增"], index=0)

    st.divider()
    if CONFIG.use_github_backend:
        st.success(f"GitHub案例後台：{CONFIG.github_repo} / {CONFIG.github_branch}")
    else:
        st.warning("GitHub案例後台未啟用，目前只寫入Streamlit暫存空間。")

    if CONFIG.use_ai:
        st.success("GitHub Models AI：已啟用（免費額度）")
        st.text_input("AI模型ID", value=CONFIG.ai_model, key="ai_model_override")
        if st.button("測試AI連線與模型"):
            try:
                client = GitHubModelsClient(
                    token=CONFIG.github_models_token,
                    model=_current_ai_model(),
                    timeout=CONFIG.request_timeout_seconds,
                    max_tokens=500,
                    temperature=0.0,
                )
                models = client.list_models()
                ids = {str(item.get("id", "")) for item in models}
                if _current_ai_model() in ids:
                    st.success(f"連線成功，模型存在：{_current_ai_model()}")
                else:
                    st.warning(f"連線成功，但 catalog 未找到目前模型。共讀到 {len(ids)} 個模型，請更換模型ID。")
            except Exception as exc:
                st.error(str(exc))
    else:
        st.info("GitHub Models AI尚未啟用；本地起卦、規則引擎與相似案例仍可完整運作。")

    if st.button("重新讀取GitHub案例庫"):
        _load_casebook(force=True)
        st.rerun()

st.title(CONFIG.app_title)
st.caption(
    "固定起卦引擎＋64卦知識庫＋本地結構/TF-IDF相似案例＋GitHub Models免費AI。"
    "AI不改卦、不自動改程式、不讀取本場賽後資料；所有預測固定只看90分鐘。"
)

col_body, col_use = st.columns(2)
with col_body:
    body_text = st.text_area("體方段落", height=190, placeholder="貼上只描述體方的賽前資料。")
with col_use:
    use_text = st.text_area("用方段落", height=190, placeholder="貼上只描述用方的賽前資料。")
full_text = st.text_area(
    "完整賽前中性介紹段落（用來算動爻）",
    height=250,
    placeholder="貼上完整賽前中性介紹段落；只使用賽前資訊。",
)
context_notes = st.text_area(
    "賽前補充資料（只輔助解卦，不參與字數）",
    height=120,
    placeholder="傷停、輪換、小組壓力、戰術、主客場、你的直覺等。",
)

match = MatchInput(
    match_name=match_name,
    competition=competition,
    body_team=body_team,
    use_team=use_team,
    body_text=body_text,
    use_text=use_text,
    full_text=full_text,
    scope=scope,
    prematch_leaning=prematch_leaning,
    context_notes=context_notes,
)

if st.button("固定起卦並建立規則預測", type="primary", use_container_width=True):
    missing = _validate_match(match)
    if missing:
        st.error("請先補齊：" + "、".join(missing))
    else:
        try:
            result = calculate_match_hexagram(match)
            rule_prediction = predict_scores(result)
            similar_cases = retrieve_similar_cases(
                result,
                casebook_df,
                top_k=CONFIG.ai_top_k_cases,
                max_rows=CONFIG.max_casebook_rows_for_ai,
            )
            signature = _match_signature(match)
            st.session_state["prediction_signature"] = signature
            st.session_state["match_input"] = match
            st.session_state["hexagram_result"] = result
            st.session_state["rule_prediction"] = rule_prediction
            st.session_state["similar_cases"] = similar_cases
            st.session_state.pop("ai_analysis", None)
            st.session_state.pop("postmatch_ai", None)
            st.session_state.pop("excel_bytes", None)
            st.success("固定起卦、規則預測與本地相似案例搜尋已完成。")
        except Exception as exc:
            st.exception(exc)

if "hexagram_result" in st.session_state:
    saved_match: MatchInput = st.session_state["match_input"]
    result = st.session_state["hexagram_result"]
    rule_prediction = st.session_state["rule_prediction"]
    similar_cases = st.session_state.get("similar_cases", [])
    ai_analysis: AIAnalysis | None = st.session_state.get("ai_analysis")

    st.divider()
    st.subheader("一、固定規則預測")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("首選", _score_text(rule_prediction.scores[0]))
    c2.metric("第二選", _score_text(rule_prediction.scores[1]))
    c3.metric("第三選", _score_text(rule_prediction.scores[2]))
    c4.metric("方向", rule_prediction.direction)
    st.caption(
        f"期望進球：{result.body_team} {rule_prediction.expected_body_goals:.2f}｜"
        f"{result.use_team} {rule_prediction.expected_use_goals:.2f}｜規則信心 {rule_prediction.confidence:.3f}"
    )

    ai_col, info_col = st.columns([1, 2])
    with ai_col:
        can_call = CONFIG.use_ai and st.session_state.get("ai_call_count", 0) < 20
        if st.button("讓GitHub Models AI綜合推理", disabled=not can_call, use_container_width=True):
            with st.spinner("AI正在比較卦勢結構、校準原因與相似案例……"):
                client = GitHubModelsClient(
                    token=CONFIG.github_models_token,
                    model=_current_ai_model(),
                    timeout=CONFIG.request_timeout_seconds,
                    max_tokens=CONFIG.ai_max_output_tokens,
                    temperature=CONFIG.ai_temperature,
                )
                ai_analysis = run_ai_prediction(client, saved_match, result, rule_prediction, similar_cases)
                st.session_state["ai_analysis"] = ai_analysis
                st.session_state["ai_call_count"] = st.session_state.get("ai_call_count", 0) + 1
                if ai_analysis.ok:
                    st.success("AI推理完成。")
                else:
                    st.warning("AI不可用，已自動退回固定規則引擎。")
    with info_col:
        if not CONFIG.use_ai:
            st.info("尚未設定GITHUB_MODELS_TOKEN；目前顯示固定規則與本地相似案例結果。")
        elif st.session_state.get("ai_call_count", 0) >= 20:
            st.warning("本次瀏覽工作階段已達20次AI防誤觸上限；重新開啟App後才會重置。")
        else:
            st.caption("只有按下按鈕才會呼叫一次AI；重新整理頁面不會自動消耗免費額度。")

    ai_analysis = st.session_state.get("ai_analysis")
    chosen_scores = final_scores(rule_prediction, ai_analysis)
    st.subheader("二、目前最終排序")
    f1, f2, f3 = st.columns(3)
    f1.metric("最終首選", _score_text(chosen_scores[0]))
    f2.metric("最終第二選", _score_text(chosen_scores[1]))
    f3.metric("最終第三選", _score_text(chosen_scores[2]))
    st.caption("若AI成功，最終排序採AI綜合結果；AI失敗或未呼叫時，採固定規則結果。")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["起卦全解", "規則與校準", "相似案例", "AI推理", "報告與儲存"])

    with tab1:
        st.markdown("### 起卦結果")
        st.dataframe(
            pd.DataFrame(
                [
                    {"項目": "體卦", "內容": f"{result.body_team}＝{result.body_gua}，數{result.body_number}，{result.body_element}"},
                    {"項目": "用卦", "內容": f"{result.use_team}＝{result.use_gua}，數{result.use_number}，{result.use_element}"},
                    {"項目": "本卦", "內容": result.main_hexagram},
                    {"項目": "互卦", "內容": result.mutual_hexagram},
                    {"項目": "動爻", "內容": f"第{result.moving_line}爻，在{result.moving_side}（{result.moving_layer}）"},
                    {"項目": "體方轉象", "內容": result.body_transition},
                    {"項目": "用方轉象", "內容": result.use_transition},
                    {"項目": "變卦", "內容": result.changed_hexagram},
                    {"項目": "體用", "內容": result.relation},
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
        st.write(result.relation_detail)
        st.write(result.moving_detail)

        trigrams = load_trigrams()
        hexagrams = load_hexagrams()
        left, right = st.columns(2)
        with left:
            st.markdown(f"### 體卦：{result.body_gua}")
            st.json(trigrams[result.body_gua], expanded=True)
        with right:
            st.markdown(f"### 用卦：{result.use_gua}")
            st.json(trigrams[result.use_gua], expanded=True)
        for label, name in [("本卦", result.main_hexagram), ("互卦", result.mutual_hexagram), ("變卦", result.changed_hexagram)]:
            data = hexagrams[name]
            with st.expander(f"{label}：{name}", expanded=(label == "本卦")):
                st.markdown(f"**核心：** {data['core']}")
                st.markdown(f"**足球象：** {data['football']}")
                st.markdown(f"**開局：** {data['opening']}")
                st.markdown(f"**中段：** {data['middle']}")
                st.markdown(f"**後段：** {data['ending']}")
                st.markdown(f"**比分傾向：** {data['goal_bias']}｜{'、'.join(data['score_patterns'])}")
                st.markdown(f"**誤判風險：** {data['risk']}")

    with tab2:
        st.markdown("### 規則引擎理由")
        for item in rule_prediction.reasons:
            st.write("- " + item)
        st.markdown("### 本場命中的校準規則")
        if rule_prediction.matched_rules:
            for rule in rule_prediction.matched_rules:
                st.info(f"{rule['id']}｜{rule['name']}\n\n{rule['lesson']}")
        else:
            st.write("本場沒有命中特定已驗證規則，只使用一般卦象與五行規則。")
        with st.expander("查看前15個比分權重"):
            st.dataframe(pd.DataFrame(rule_prediction.score_grid), use_container_width=True, hide_index=True)
        with st.expander("查看結構標籤"):
            st.write("、".join(result.structural_tags))

    with tab3:
        st.markdown("### 本地雙引擎檢索結果")
        st.caption("結構相似度占68%，TF-IDF文字相似度占32%；同一場比賽會被排除，避免賽果倒灌。")
        if not similar_cases:
            st.warning("目前案例庫沒有可用的賽後案例。請逐步補上實際比分與校準原因。")
        for case in similar_cases:
            with st.expander(f"{case.case_id}｜{case.match_name}｜相似度 {case.similarity:.3f}"):
                st.write(f"結構相似度：{case.structural_similarity:.3f}")
                st.write(f"文字相似度：{case.text_similarity:.3f}")
                st.write(f"歷史預測：{case.predicted_scores or '未記錄'}")
                st.write(f"實際比分：{case.actual_score or '未記錄'}")
                st.markdown("**共同點**")
                for item in case.common_points:
                    st.write("- " + item)
                st.markdown("**重要差異**")
                for item in case.differences:
                    st.write("- " + item)
                st.markdown("**校準教訓**")
                st.write(case.calibration_reason or case.lesson_summary or "未記錄")

    with tab4:
        if ai_analysis is None:
            st.info("尚未按下AI綜合推理。")
        elif not ai_analysis.ok:
            st.error(ai_analysis.error)
            st.write("系統已保留固定起卦與本地相似案例結果。")
        else:
            st.success(f"AI模型：{ai_analysis.model}｜方向：{ai_analysis.direction}")
            for index, score in enumerate(ai_analysis.scores, start=1):
                confidence = ai_analysis.confidences[index - 1] if index - 1 < len(ai_analysis.confidences) else 0.0
                reason = ai_analysis.score_reasons[index - 1] if index - 1 < len(ai_analysis.score_reasons) else ""
                st.markdown(f"**第{index}選：{_score_text(score)}｜信心 {confidence:.2f}**")
                st.write(reason)
            st.markdown("**整體推理摘要**")
            st.write(ai_analysis.overall_reasoning)
            st.markdown("**風險提醒**")
            st.warning(ai_analysis.risk_warning or "無")
            st.markdown("**AI如何使用相似案例**")
            if ai_analysis.similar_case_analysis:
                st.dataframe(pd.DataFrame(ai_analysis.similar_case_analysis), use_container_width=True, hide_index=True)
            else:
                st.write("AI未列出相似案例。")
            st.markdown("**待賽後驗證的建議**")
            for item in ai_analysis.calibration_suggestions:
                st.write("- " + item)

    with tab5:
        st.markdown("### 賽後校準與案例儲存")
        actual_score = st.text_input("實際90分鐘比分（賽前留空）", key="actual_score_input", placeholder="例如 3-2")
        user_review = st.text_area(
            "人工校準原因",
            key="calibration_reason_input",
            height=140,
            placeholder="寫清楚原判、實際、偏差、卦象原因與下次修正。",
        )
        normalized_actual = normalize_score(actual_score)
        local_summary = local_calibration_summary(result, rule_prediction, normalized_actual)
        st.markdown("**本地自動校準摘要**")
        st.write(local_summary)

        if normalized_actual and CONFIG.use_ai:
            if st.button("讓AI產生賽後校準建議"):
                with st.spinner("AI正在比較賽前原判與實際90分鐘比分……"):
                    try:
                        client = GitHubModelsClient(
                            token=CONFIG.github_models_token,
                            model=_current_ai_model(),
                            timeout=CONFIG.request_timeout_seconds,
                            max_tokens=CONFIG.ai_max_output_tokens,
                            temperature=0.1,
                        )
                        postmatch_ai = run_postmatch_calibration(
                            client,
                            saved_match,
                            result,
                            rule_prediction,
                            ai_analysis,
                            normalized_actual,
                            user_review,
                            similar_cases,
                        )
                        st.session_state["postmatch_ai"] = postmatch_ai
                    except Exception as exc:
                        st.error(str(exc))
        postmatch_ai: dict[str, Any] | None = st.session_state.get("postmatch_ai")
        if postmatch_ai:
            st.markdown("**AI賽後建議（尚未確認）**")
            st.json(postmatch_ai, expanded=True)
        confirmed = st.checkbox(
            "我已閱讀並確認採用AI的校準摘要",
            value=False,
            disabled=not bool(postmatch_ai),
            key="confirm_ai_calibration",
        )

        calibration_reason = user_review.strip()
        calibration_summary = local_summary
        if confirmed and postmatch_ai:
            suggested_reason = str(postmatch_ai.get("suggested_calibration_reason", "")).strip()
            suggested_lesson = str(postmatch_ai.get("generalizable_lesson", "")).strip()
            if suggested_reason:
                calibration_reason = (calibration_reason + "\n" + suggested_reason).strip()
            if suggested_lesson:
                calibration_summary = suggested_lesson

        live_report = build_markdown_report(
            saved_match,
            result,
            rule_prediction,
            similar_cases,
            ai_analysis=ai_analysis,
            actual_score=normalized_actual,
            calibration_reason=calibration_reason,
            calibration_summary=calibration_summary,
            postmatch_ai=postmatch_ai,
        )
        st.download_button(
            "下載目前Markdown完整報告",
            data=live_report,
            file_name=safe_filename(result.match_name) + ".md",
            mime="text/markdown",
            use_container_width=True,
        )

        if st.button("儲存或更新案例庫與報告", type="primary", use_container_width=True):
            try:
                report_path = save_report(CONFIG, result, live_report)
                row = build_case_row(
                    saved_match,
                    result,
                    rule_prediction,
                    ai_analysis,
                    similar_cases,
                    normalized_actual,
                    calibration_reason,
                    calibration_summary,
                    confirmed,
                    report_path,
                )
                updated, action = STORE.upsert(row, save_mode)
                st.session_state["casebook_df"] = updated
                st.success(f"案例庫已{action}，目前共 {len(updated)} 筆；報告：{report_path}")
            except Exception as exc:
                st.exception(exc)

st.divider()
st.subheader("三、完整知識庫")
kb1, kb2, kb3, kb4 = st.tabs(["八卦", "六十四卦", "校準規則", "案例庫"])

with kb1:
    trigrams = load_trigrams()
    selected = st.selectbox("選擇八卦", list(trigrams.keys()), key="kb_trigram")
    st.json(trigrams[selected], expanded=True)

with kb2:
    hexagrams = load_hexagrams()
    selected_hex = st.selectbox(
        "選擇六十四卦",
        sorted(hexagrams.keys(), key=lambda name: int(hexagrams[name]["sequence"])),
        key="kb_hexagram",
    )
    data = hexagrams[selected_hex]
    st.markdown(f"### 第{data['sequence']}卦｜{selected_hex}")
    st.json(data, expanded=True)

with kb3:
    rules = load_calibration_rules()
    st.caption("verified＝已由案例回測確認；reviewed＝已回顧但仍需更多案例；general＝一般原則。")
    status_filter = st.multiselect("狀態", ["verified", "reviewed", "general"], default=["verified", "reviewed", "general"])
    filtered_rules = [rule for rule in rules if rule.get("status") in status_filter]
    for rule in filtered_rules:
        with st.expander(f"{rule['id']}｜{rule['name']}｜{rule['status']}"):
            st.write("來源：" + rule.get("source_case", ""))
            st.write("教訓：" + rule.get("lesson", ""))
            st.json({"conditions": rule.get("conditions", {}), "effects": rule.get("effects", {})}, expanded=False)

with kb4:
    casebook_df = st.session_state.get("casebook_df", pd.DataFrame())
    if st.session_state.get("casebook_error"):
        st.error(st.session_state["casebook_error"])
    if casebook_df.empty:
        st.info("案例庫目前為空。")
    else:
        st.write(f"共 {len(casebook_df)} 筆，顯示最近30筆。")
        st.dataframe(casebook_df.tail(30), use_container_width=True, hide_index=True)
        st.download_button(
            "下載CSV案例庫",
            data=casebook_df.to_csv(index=False, lineterminator="\n"),
            file_name="meihua_cases.csv",
            mime="text/csv",
        )
        if st.button("準備Excel下載"):
            with st.spinner("正在建立Excel……"):
                st.session_state["excel_bytes"] = STORE.excel_bytes(casebook_df)
        if "excel_bytes" in st.session_state:
            st.download_button(
                "下載Excel案例庫",
                data=st.session_state["excel_bytes"],
                file_name="meihua_cases.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

st.caption(
    f"Prompt版本：{PROMPT_VERSION}。本系統是研究與紀錄工具，不是投注建議。"
    "AI只能提出待驗證推理，不能取代固定起卦、人工校準與資料品質管理。"
)
