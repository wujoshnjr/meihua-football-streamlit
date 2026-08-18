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
    GENERIC_RESIDUAL_FIT_VERSION,
    MARKET_INCREMENTAL_VALUE_VERSION,
    MULTISIGNAL_RUNNER_VERSION,
    RESEARCH_CALIBRATION_VERSION,
    RESIDUAL_TUNING_VERSION,
    STABILITY_SCHEMA_VERSION,
)
from meihua import (
    MEIHUA_ENGINE_VERSION,
    MEIHUA_OUTCOME_DESIGN_VERSION,
    build_meihua_snapshot,
    meihua_outcome_numeric_features,
)
from qimen.outcome_design import QIMEN_OUTCOME_DESIGN_VERSION, qimen_outcome_numeric_features
from qimen.outcome_features import build_qimen_outcome_feature_snapshot
from version import __version__


st.set_page_config(page_title="JARVIS v8 Research Lab", page_icon="🧪", layout="wide")
st.title("JARVIS v8 Research Lab")
st.caption(f"Web app v{__version__}｜多訊號研究、校準、穩定性與 Football challenger 的同一實驗工作台")
st.warning(
    "RESEARCH GATE：此頁可以檢視 v8 raw features 與研究模組，但沒有 frozen TRAIN/VALIDATION/CALIBRATION artifact 時，"
    "不會直接覆蓋主頁的 live prediction。",
    icon="⚠️",
)

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Web App", f"v{__version__}")
m2.metric("Dynamic Football", DYNAMIC_STRENGTH_VERSION.rsplit("-v", 1)[-1])
m3.metric("Fixture Context", FOOTBALL_CONTEXT_VERSION.rsplit("-v", 1)[-1])
m4.metric("Qimen design", QIMEN_OUTCOME_DESIGN_VERSION.rsplit("-v", 1)[-1])
m5.metric("Meihua design", MEIHUA_OUTCOME_DESIGN_VERSION.rsplit("-v", 1)[-1])

st.subheader("研究堆疊")
stack_rows = [
    {"層": "Football strength", "版本": DYNAMIC_STRENGTH_VERSION, "用途": "opponent-adjusted attack/defence + optional xG"},
    {"層": "Football tuning", "版本": DYNAMIC_STRENGTH_TUNING_VERSION, "用途": "VALIDATION-only half-life / L2 / xG weight"},
    {"層": "Fixture context", "版本": FOOTBALL_CONTEXT_VERSION, "用途": "盤前 rest / congestion / workload facts"},
    {"層": "Context tuning", "版本": FOOTBALL_CONTEXT_TUNING_VERSION, "用途": "TRAIN coefficients + VALIDATION L2 / alpha"},
    {"層": "Residual fit", "版本": GENERIC_RESIDUAL_FIT_VERSION, "用途": "no-intercept Qimen / Meihua / context residuals"},
    {"層": "Residual tuning", "版本": RESIDUAL_TUNING_VERSION, "用途": "VALIDATION-only regularization + alpha=0 fallback"},
    {"層": "M0–M3 runner", "版本": MULTISIGNAL_RUNNER_VERSION, "用途": "shared Football baseline for fair ablation"},
    {"層": "Calibration", "版本": RESEARCH_CALIBRATION_VERSION, "用途": "CALIBRATION-only 1X2 temperature scaling"},
    {"層": "Untouched stability", "版本": STABILITY_SCHEMA_VERSION, "用途": "rolling blocks + paired block bootstrap"},
    {"層": "Market incremental value", "版本": MARKET_INCREMENTAL_VALUE_VERSION, "用途": "VALIDATION-only structural-vs-market benchmark"},
]
st.dataframe(pd.DataFrame(stack_rows), hide_index=True, use_container_width=True)

with st.expander("版本與研究契約", expanded=False):
    st.json(
        {
            "web_app_version": __version__,
            "dynamic_strength_version": DYNAMIC_STRENGTH_VERSION,
            "dynamic_strength_tuning_version": DYNAMIC_STRENGTH_TUNING_VERSION,
            "football_context_version": FOOTBALL_CONTEXT_VERSION,
            "football_context_tuning_version": FOOTBALL_CONTEXT_TUNING_VERSION,
            "generic_residual_version": GENERIC_RESIDUAL_FIT_VERSION,
            "residual_tuning_version": RESIDUAL_TUNING_VERSION,
            "multisignal_runner_version": MULTISIGNAL_RUNNER_VERSION,
            "research_calibration_version": RESEARCH_CALIBRATION_VERSION,
            "stability_schema_version": STABILITY_SCHEMA_VERSION,
            "market_incremental_value_version": MARKET_INCREMENTAL_VALUE_VERSION,
            "qimen_outcome_design_version": QIMEN_OUTCOME_DESIGN_VERSION,
            "meihua_engine_version": MEIHUA_ENGINE_VERSION,
            "meihua_outcome_design_version": MEIHUA_OUTCOME_DESIGN_VERSION,
        }
    )

st.subheader("固定模型家族")
st.markdown(
    """
- **M0**：Football only
- **M1**：Football + Qimen residual
- **M2**：Football + Meihua residual
- **M3**：Football + Qimen + Meihua residual/fusion

所有家族必須共用同一份 frozen Football baseline。`M4` interaction 只有在 M3 已於 VALIDATION 與 untouched rolling blocks 顯示穩定增量後才允許研究。
"""
)

st.code("TRAIN → VALIDATION → CALIBRATION → TEST_UNTOUCHED", language=None)
st.caption("TRAIN 學係數；VALIDATION 選超參數；CALIBRATION 只做 1X2 機率校準；TEST_UNTOUCHED 只做最後評估。")

required_state = ("match", "board", "reading")
if not all(key in st.session_state for key in required_state):
    st.info("請先回主頁建立／重建同一場比賽的奇門盤；Research Lab 會沿用同一 event_at 與 timezone。")
else:
    match = st.session_state.match
    board = st.session_state.board
    reading = st.session_state.reading

    st.subheader("同場雙訊號 raw snapshot")
    st.caption(
        f"{match.home_team} vs {match.away_team}｜{match.event_at.isoformat()}｜{match.timezone_name}｜"
        "兩套訊號使用同一註冊事件，不在此頁人工轉成比分。"
    )

    qimen_snapshot = build_qimen_outcome_feature_snapshot(board, reading)
    qimen_features = qimen_outcome_numeric_features(qimen_snapshot)
    meihua_snapshot = build_meihua_snapshot(match.event_at, match.timezone_name)
    meihua_features = meihua_outcome_numeric_features(meihua_snapshot)

    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            st.markdown("### 奇門遁甲")
            st.write(f"主用神：**{qimen_snapshot.home_original_stem}**")
            st.write(f"客用神：**{qimen_snapshot.away_original_stem}**")
            st.write(f"同宮：**{'是' if qimen_snapshot.same_palace else '否'}**")
            st.write(f"方向解析度：**{qimen_snapshot.direction_resolution}**")
            st.caption(f"numeric features：{len(qimen_features)}")
            with st.expander("Qimen raw features"):
                st.json(qimen_features)

    with right:
        with st.container(border=True):
            st.markdown("### 梅花易數")
            st.write(f"本卦：**{meihua_snapshot.upper_trigram}上・{meihua_snapshot.lower_trigram}下**")
            st.write(f"動爻：**{meihua_snapshot.moving_line}**")
            st.write(f"體／用：**{meihua_snapshot.body_trigram}／{meihua_snapshot.use_trigram}**")
            st.write(f"體用關係：**{meihua_snapshot.body_use_relation}**")
            st.caption(f"numeric features：{len(meihua_features)}")
            with st.expander("Meihua raw features"):
                st.json(meihua_features)

    st.subheader("融合邊界")
    st.info(
        "目前只允許把兩套 raw features 保存到同一歷史 prematch record。"
        "沒有 TRAIN artifact 時，不做 Qimen + Meihua 人工投票，也不把兩者相同方向解讀成雙倍信心。"
    )

st.divider()
st.caption("Research Lab 顯示的是可重現研究能力；真正模型 promotion 仍需 frozen chronological out-of-sample evidence。")
