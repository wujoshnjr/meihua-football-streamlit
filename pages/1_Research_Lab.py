from __future__ import annotations

import streamlit as st

from jarvis.football.strength import DYNAMIC_STRENGTH_VERSION
from jarvis.research.residual import GENERIC_RESIDUAL_FIT_VERSION
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
st.caption(f"Production v{__version__} 保持不變｜v8 多訊號研究層獨立驗證")
st.warning(
    "RESEARCH ONLY：此頁不改動 production 1X2 或比分機率。奇門與梅花只輸出 raw features；"
    "任何 residual 權重都必須由 TRAIN-only 資料學習並通過時序盲測。",
    icon="⚠️",
)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Production", f"v{__version__}")
m2.metric("Dynamic Football", DYNAMIC_STRENGTH_VERSION.rsplit("-v", 1)[-1])
m3.metric("Qimen design", QIMEN_OUTCOME_DESIGN_VERSION.rsplit("-v", 1)[-1])
m4.metric("Meihua design", MEIHUA_OUTCOME_DESIGN_VERSION.rsplit("-v", 1)[-1])

with st.expander("版本與研究契約", expanded=False):
    st.json(
        {
            "production_version": __version__,
            "dynamic_strength_version": DYNAMIC_STRENGTH_VERSION,
            "generic_residual_version": GENERIC_RESIDUAL_FIT_VERSION,
            "qimen_outcome_design_version": QIMEN_OUTCOME_DESIGN_VERSION,
            "meihua_engine_version": MEIHUA_ENGINE_VERSION,
            "meihua_outcome_design_version": MEIHUA_OUTCOME_DESIGN_VERSION,
            "production_changed_by_this_page": False,
        }
    )

st.subheader("固定模型家族")
st.markdown(
    """
- **M0**：Football only
- **M1**：Football + Qimen residual
- **M2**：Football + Meihua residual
- **M3**：Football + Qimen + Meihua residual/fusion

`M4` interaction 只有在 M3 已於 VALIDATION 與 untouched rolling blocks 顯示穩定增量後才允許研究。
"""
)

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
