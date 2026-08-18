from __future__ import annotations

import streamlit as st

from jarvis.release import runtime_release_status


release = runtime_release_status()

st.set_page_config(page_title="JARVIS v8", page_icon="⚽", layout="wide")

st.markdown(
    """
    <style>
      .block-container {
        max-width: 1180px;
        padding-top: 2.2rem;
        padding-bottom: 4rem;
      }
      .jarvis-hero {
        padding: 2.25rem 2.4rem;
        border: 1px solid rgba(128, 128, 128, 0.22);
        border-radius: 22px;
        background:
          radial-gradient(circle at 88% 12%, rgba(88, 166, 255, 0.18), transparent 32%),
          linear-gradient(135deg, rgba(20, 29, 48, 0.98), rgba(11, 18, 32, 0.96));
        color: white;
        margin-bottom: 1.4rem;
      }
      .jarvis-kicker {
        font-size: .82rem;
        font-weight: 700;
        letter-spacing: .16em;
        text-transform: uppercase;
        opacity: .72;
        margin-bottom: .7rem;
      }
      .jarvis-hero h1 {
        font-size: clamp(2.2rem, 4.5vw, 4.4rem);
        line-height: 1.02;
        margin: 0 0 .85rem 0;
        letter-spacing: -.035em;
      }
      .jarvis-hero p {
        max-width: 760px;
        font-size: 1.06rem;
        line-height: 1.75;
        opacity: .82;
        margin: 0;
      }
      .status-card {
        border: 1px solid rgba(128, 128, 128, 0.20);
        border-radius: 16px;
        padding: 1.05rem 1.15rem;
        min-height: 116px;
      }
      .status-label {
        font-size: .76rem;
        opacity: .62;
        text-transform: uppercase;
        letter-spacing: .08em;
      }
      .status-value {
        font-size: 1.35rem;
        font-weight: 700;
        margin-top: .3rem;
      }
      .status-note {
        font-size: .86rem;
        opacity: .68;
        margin-top: .3rem;
      }
      div[data-testid="stPageLink"] a {
        border-radius: 12px;
        padding: .72rem .9rem;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="jarvis-hero">
      <div class="jarvis-kicker">JARVIS · Football Intelligence Research Platform</div>
      <h1>足球預測，研究與實戰分開。</h1>
      <p>
        一個可重現、可稽核的足球賽前研究系統。正式 Live Predictor 維持 frozen champion；
        Dynamic Football、xG、Fixture Context、奇門與梅花等 v8 challenger 只在通過 chronological validation 與 untouched review 後才有資格升級。
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

s1, s2, s3 = st.columns(3)
with s1:
    st.markdown(
        f"""
        <div class="status-card">
          <div class="status-label">Live Predictor</div>
          <div class="status-value">v{release.live_predictor_code_version}</div>
          <div class="status-note">Frozen champion compatibility path</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with s2:
    st.markdown(
        f"""
        <div class="status-card">
          <div class="status-label">Web / Research Stack</div>
          <div class="status-value">v{release.web_app_version}</div>
          <div class="status-note">JARVIS v8 research tooling online</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with s3:
    st.markdown(
        """
        <div class="status-card">
          <div class="status-label">Automatic Promotion</div>
          <div class="status-value">OFF</div>
          <div class="status-note">Frozen artifacts + human review required</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("### 你要做什麼？")
left, middle, right = st.columns(3)
with left:
    with st.container(border=True):
        st.markdown("#### ⚽ 建立一場賽前預測")
        st.write("輸入事件時間、雙方盤前足球資料，建立奇門盤與 frozen Live Predictor 機率輸出。")
        st.page_link("pages/2_Live_Predictor.py", label="開啟 Live Predictor", icon="🎯", use_container_width=True)
with middle:
    with st.container(border=True):
        st.markdown("#### 🚀 看目前 v8 狀態")
        st.write("查看 Web、Live、Research 三層版本，以及 Dynamic Football、Context、M0–M3 與 promotion gate。")
        st.page_link("pages/0_JARVIS_v8_Dashboard.py", label="開啟 v8 Dashboard", icon="📊", use_container_width=True)
with right:
    with st.container(border=True):
        st.markdown("#### 🧪 研究多訊號模型")
        st.write("查看 Qimen / Meihua raw features 與 M0–M3 研究契約；沒有 frozen artifact 時不覆蓋正式預測。")
        st.page_link("pages/1_Research_Lab.py", label="開啟 Research Lab", icon="🧪", use_container_width=True)

st.markdown("### 目前模型治理")
flow = st.columns(4)
for column, title, detail in (
    (flow[0], "01 · TRAIN", "只學係數與 Football strength"),
    (flow[1], "02 · VALIDATION", "只選超參數與 shrinkage"),
    (flow[2], "03 · CALIBRATION", "只做 1X2 機率校準"),
    (flow[3], "04 · TEST_UNTOUCHED", "只做最終評估與 promotion review"),
):
    with column:
        with st.container(border=True):
            st.markdown(f"**{title}**")
            st.caption(detail)

st.info(
    "目前 v8 研究能力已經部署，但這不等於 v8 challenger 已經成為正式模型。"
    "Live Predictor 仍保持 frozen champion，直到足量真實 chronological data 完成 untouched review。",
    icon="🛡️",
)

if "match" in st.session_state:
    match = st.session_state.match
    st.markdown("### 本次工作階段")
    a, b, c, d = st.columns(4)
    a.metric("比賽", f"{match.home_team} vs {match.away_team}")
    b.metric("奇門盤", "READY" if "board" in st.session_state else "—")
    c.metric("Live 預測", "READY" if "prediction" in st.session_state else "—")
    d.metric("盤前鎖定", "PASS" if st.session_state.get("prediction_lock") else "—")

st.divider()
st.caption(
    "JARVIS 僅供研究與教育用途。奇門遁甲與梅花易數屬傳統術數；正式機率層與研究 challenger 必須分離治理。"
)
