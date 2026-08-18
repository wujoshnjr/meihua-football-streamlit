from __future__ import annotations

import pandas as pd
import streamlit as st

from jarvis.football import (
    DYNAMIC_STRENGTH_TUNING_VERSION,
    DYNAMIC_STRENGTH_VERSION,
    FOOTBALL_CONTEXT_TUNING_VERSION,
    FOOTBALL_CONTEXT_VERSION,
)
from jarvis.research import (
    EXPERIMENT_SCHEMA_VERSION,
    MARKET_INCREMENTAL_VALUE_VERSION,
    MULTISIGNAL_DATASET_VERSION,
    MULTISIGNAL_RUNNER_VERSION,
    RESEARCH_CALIBRATION_VERSION,
    RESIDUAL_TUNING_VERSION,
    STABILITY_SCHEMA_VERSION,
)
from version import __version__


st.set_page_config(page_title="JARVIS v8 Dashboard", page_icon="🚀", layout="wide")
st.title("JARVIS v8 Dashboard")
st.caption(
    f"Web app v{__version__}｜v8 research stack 已輸出到 Streamlit｜"
    "live predictor 仍以已存在的 production champion 路徑產生預測，研究 challenger 必須有 frozen artifact 才能升級。"
)

st.success(
    "你現在看到的是實際部署介面的 v8 控制台，不再只是 GitHub 裡的 research modules。",
    icon="✅",
)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Web App", f"v{__version__}")
m2.metric("Dynamic Football", DYNAMIC_STRENGTH_VERSION.rsplit("-v", 1)[-1])
m3.metric("Fixture Context", FOOTBALL_CONTEXT_VERSION.rsplit("-v", 1)[-1])
m4.metric("M0–M3 Runner", MULTISIGNAL_RUNNER_VERSION.rsplit("-v", 1)[-1])

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
- **TEST_UNTOUCHED**：只做最終 proper-score、rolling stability 與 bootstrap 評估。
"""
    )

with right:
    st.subheader("目前升級邊界")
    st.warning(
        "v8 模組已進入網頁與部署包，但在沒有真實 chronological frozen artifacts 前，"
        "主頁的即時 prediction 不會偷偷套用研究係數。這是避免把尚未驗證的 challenger 當成已證明更準。",
        icon="⚠️",
    )
    st.write("下一個 promotion gate：產生足量真實 TRAIN/VALIDATION/CALIBRATION artifacts，然後才把選中的 Football baseline 接進 live predictor。")

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
    state_cols[2].metric("Production 預測", "READY" if "prediction" in st.session_state else "—")
    state_cols[3].metric("盤前鎖定", "PASS" if st.session_state.get("prediction_lock") else "—")
else:
    st.info("先回主頁建立一場比賽；v8 Dashboard 會沿用同一個 Streamlit session。")

with st.expander("完整版本指紋", expanded=False):
    st.json(
        {
            "web_app_version": __version__,
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
            "market_incremental_value_version": MARKET_INCREMENTAL_VALUE_VERSION,
        }
    )

st.divider()
st.caption(
    "JARVIS v8 Web Integration：研究模組已輸出到 Streamlit；模型 promotion 仍受 chronological out-of-sample gate 約束。"
)
