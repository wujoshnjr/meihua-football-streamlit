from __future__ import annotations

import pandas as pd
import streamlit as st

from jarvis.football import (
    DYNAMIC_STRENGTH_TUNING_VERSION,
    DYNAMIC_STRENGTH_VERSION,
    FOOTBALL_CONTEXT_TUNING_VERSION,
    FOOTBALL_CONTEXT_VERSION,
)
from jarvis.release import runtime_release_status
from jarvis.research import (
    EXPERIMENT_SCHEMA_VERSION,
    MARKET_INCREMENTAL_VALUE_VERSION,
    MULTISIGNAL_DATASET_VERSION,
    MULTISIGNAL_RUNNER_VERSION,
    PROMOTION_REVIEW_VERSION,
    RESEARCH_CALIBRATION_VERSION,
    RESIDUAL_TUNING_VERSION,
    STABILITY_SCHEMA_VERSION,
)


release = runtime_release_status()

st.set_page_config(page_title="JARVIS v8 Dashboard", page_icon="🚀", layout="wide")
st.title("JARVIS v8 Dashboard")
st.caption(
    f"Web app v{release.web_app_version}｜Live predictor code v{release.live_predictor_code_version}｜"
    "v8 research stack 已輸出到 Streamlit；研究 challenger 必須有 frozen chronological artifact 才能升級。"
)

st.success(
    "目前部署狀態已分成 Web App、Live Predictor、Research Stack 三層，不再用單一版本號暗示模型已被替換。",
    icon="✅",
)

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Web App", f"v{release.web_app_version}")
m2.metric("Live Predictor", f"v{release.live_predictor_code_version}")
m3.metric("Dynamic Football", DYNAMIC_STRENGTH_VERSION.rsplit("-v", 1)[-1])
m4.metric("Fixture Context", FOOTBALL_CONTEXT_VERSION.rsplit("-v", 1)[-1])
m5.metric("M0–M3 Runner", MULTISIGNAL_RUNNER_VERSION.rsplit("-v", 1)[-1])

with st.container(border=True):
    st.markdown("### Runtime release contract")
    c1, c2, c3 = st.columns(3)
    c1.write(f"**Web generation**：{release.research_generation}")
    c2.write(f"**Live model**：{release.live_predictor_model_version}")
    c3.write(f"**Promotion**：{release.promotion_policy}")
    st.caption(
        "Web app 升版不等於 live predictor 自動換模；automatic_promotion 固定為 False，"
        "真正替換必須由已凍結且通過 chronological out-of-sample review 的 artifact 明確完成。"
    )

st.subheader("v8 能力上線狀態")
status_rows = [
    {
        "能力": "Dynamic Football + xG",
        "版本": DYNAMIC_STRENGTH_VERSION,
        "網頁狀態": "可見／research-ready",
        "正式預測條件": "需 TRAIN fit + VALIDATION 選定 frozen artifact",
    },
    {
        "能力": "Dynamic half-life / L2 / xG tuning",
        "版本": DYNAMIC_STRENGTH_TUNING_VERSION,
        "網頁狀態": "可見／research-ready",
        "正式預測條件": "VALIDATION-only 選參數後凍結",
    },
    {
        "能力": "Fixture rest / congestion context",
        "版本": FOOTBALL_CONTEXT_VERSION,
        "網頁狀態": "可見／research-ready",
        "正式預測條件": "盤前 cutoff-safe 歷史資料",
    },
    {
        "能力": "Fixture context tuning",
        "版本": FOOTBALL_CONTEXT_TUNING_VERSION,
        "網頁狀態": "可見／research-ready",
        "正式預測條件": "TRAIN 係數 + VALIDATION L2/alpha",
    },
    {
        "能力": "M0 / M1 / M2 / M3 common runner",
        "版本": MULTISIGNAL_RUNNER_VERSION,
        "網頁狀態": "可見／research-ready",
        "正式預測條件": "四家族共用同一 frozen Football baseline",
    },
    {
        "能力": "Residual shrinkage tuning",
        "版本": RESIDUAL_TUNING_VERSION,
        "網頁狀態": "可見／research-ready",
        "正式預測條件": "VALIDATION-only；alpha=0 fallback",
    },
    {
        "能力": "CALIBRATION-only temperature scaling",
        "版本": RESEARCH_CALIBRATION_VERSION,
        "網頁狀態": "可見／research-ready",
        "正式預測條件": "獨立 CALIBRATION artifact；只校準 1X2",
    },
    {
        "能力": "Rolling stability + paired block bootstrap",
        "版本": STABILITY_SCHEMA_VERSION,
        "網頁狀態": "可見／evaluation-ready",
        "正式預測條件": "只讀 TEST_UNTOUCHED，不可反向調參",
    },
    {
        "能力": "Generic promotion review gate",
        "版本": PROMOTION_REVIEW_VERSION,
        "網頁狀態": "可見／governance-ready",
        "正式預測條件": "policy 必須在 TEST_UNTOUCHED 開始前預先登記；只輸出人工 review 資格",
    },
    {
        "能力": "Market incremental value test",
        "版本": MARKET_INCREMENTAL_VALUE_VERSION,
        "網頁狀態": "可見／benchmark-ready",
        "正式預測條件": "盤前 market snapshot + VALIDATION-only pooling weight",
    },
]
st.dataframe(pd.DataFrame(status_rows), hide_index=True, use_container_width=True)

left, right = st.columns(2)
with left:
    st.subheader("資料與實驗契約")
    st.code("TRAIN → VALIDATION → CALIBRATION → TEST_UNTOUCHED", language=None)
    st.markdown(
        """
- **TRAIN**：只學 Football / Qimen / Meihua 係數。
- **VALIDATION**：只選 half-life、L2、xG weight、alpha 等超參數。
- **CALIBRATION**：只擬合 1X2 temperature。
- **TEST_UNTOUCHED**：只做最終 proper-score、rolling stability、bootstrap 與已預先登記的 promotion review。
"""
    )

with right:
    st.subheader("目前升級邊界")
    st.warning(
        "v8 模組已進入網頁與部署包，但在沒有真實 chronological frozen artifacts 前，"
        "主頁的即時 prediction 不會偷偷套用研究係數。Generic promotion gate 也只會回傳人工審查資格，永不自動換模。",
        icon="⚠️",
    )
    st.write("下一個 promotion gate：產生足量真實 TRAIN/VALIDATION/CALIBRATION artifacts，凍結 policy，再完成 TEST_UNTOUCHED review。")

st.subheader("目前事件")
if "match" in st.session_state:
    match = st.session_state.match
    st.info(
        f"{match.home_team} vs {match.away_team}｜{match.competition}｜"
        f"{match.event_at.isoformat()}｜{match.timezone_name}"
    )
    state_cols = st.columns(4)
    state_cols[0].metric("奇門盤", "READY" if "board" in st.session_state else "—")
    state_cols[1].metric("賽事研究", "READY" if "reading" in st.session_state else "—")
    state_cols[2].metric("Live 預測", "READY" if "prediction" in st.session_state else "—")
    state_cols[3].metric("盤前鎖定", "PASS" if st.session_state.get("prediction_lock") else "—")
else:
    st.info("先回主頁建立一場比賽；v8 Dashboard 會沿用同一個 Streamlit session。")

with st.expander("完整版本指紋", expanded=False):
    st.json(
        {
            "runtime_release_status": release.to_dict(),
            "experiment_schema_version": EXPERIMENT_SCHEMA_VERSION,
            "multisignal_dataset_version": MULTISIGNAL_DATASET_VERSION,
            "multisignal_runner_version": MULTISIGNAL_RUNNER_VERSION,
            "dynamic_strength_version": DYNAMIC_STRENGTH_VERSION,
            "dynamic_strength_tuning_version": DYNAMIC_STRENGTH_TUNING_VERSION,
            "football_context_version": FOOTBALL_CONTEXT_VERSION,
            "football_context_tuning_version": FOOTBALL_CONTEXT_TUNING_VERSION,
            "residual_tuning_version": RESIDUAL_TUNING_VERSION,
            "research_calibration_version": RESEARCH_CALIBRATION_VERSION,
            "stability_schema_version": STABILITY_SCHEMA_VERSION,
            "promotion_review_version": PROMOTION_REVIEW_VERSION,
            "market_incremental_value_version": MARKET_INCREMENTAL_VALUE_VERSION,
        }
    )

st.divider()
st.caption(
    "JARVIS v8 Web Integration：研究模組已輸出到 Streamlit；模型 promotion 仍受 chronological out-of-sample gate 約束。"
)
