from __future__ import annotations

import streamlit as st

from jarvis.live_meihua import load_deployed_live_meihua_artifact
from jarvis.release import runtime_release_status


release = runtime_release_status()

st.set_page_config(page_title="JARVIS v8", page_icon="⚽", layout="wide")

try:
    live_meihua_artifact = load_deployed_live_meihua_artifact()
except ValueError:
    live_meihua_artifact = None

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
        max-width: 800px;
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
        JARVIS v8.1 已把梅花易數正式接入 Live Predictor：每場比賽都建立可重現梅花卦象與 feature fingerprint。
        數值機率只有在 M2 完成 chronological validation、獨立 calibration、untouched review 與人工批准後才允許改動，
        因此不會用手寫術數規則冒充已驗證的足球權重。
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

s1, s2, s3, s4 = st.columns(4)
with s1:
    st.markdown(
        f"""
        <div class="status-card">
          <div class="status-label">Football Base</div>
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
          <div class="status-note">JARVIS v8 production UI</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with s3:
    meihua_value = "M2 ACTIVE" if live_meihua_artifact is not None and live_meihua_artifact.shrinkage_alpha > 1e-15 else "LIVE ADVISORY"
    st.markdown(
        f"""
        <div class="status-card">
          <div class="status-label">Meihua Yishu</div>
          <div class="status-value">{meihua_value}</div>
          <div class="status-note">Production-integrated · artifact gated</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with s4:
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
        st.markdown("#### ⚽ Football + 梅花 Live 預測")
        st.write("輸入事件時間與雙方盤前足球資料；系統同時計算 Football baseline 與正式梅花 Live snapshot。")
        st.page_link("pages/3_Live_Meihua.py", label="開啟 Live Predictor", icon="🎯", use_container_width=True)
with middle:
    with st.container(border=True):
        st.markdown("#### 🧭 完整稽核工作台")
        st.write("需要奇門九宮、證據表、盤前鎖定、JSON / Markdown / HTML 匯出時使用完整 Audit Workbench。")
        st.page_link("pages/2_Live_Predictor.py", label="開啟 Audit Workbench", icon="🧭", use_container_width=True)
with right:
    with st.container(border=True):
        st.markdown("#### 🧪 v8 Research / Promotion")
        st.write("查看 Dynamic Football、Qimen / Meihua M0–M3、calibration、stability 與 promotion gate。")
        st.page_link("pages/0_JARVIS_v8_Dashboard.py", label="開啟 v8 Dashboard", icon="📊", use_container_width=True)

st.markdown("### 梅花正式上線的兩層狀態")
status_left, status_right = st.columns(2)
with status_left:
    with st.container(border=True):
        st.markdown("**LIVE COMPUTATION · ON**")
        st.write("年月日時起卦、本卦／互卦／變卦、動爻、體用、旺衰與 numeric features 每場正式計算並 fingerprint。")
with status_right:
    with st.container(border=True):
        st.markdown("**M2 PROBABILITY WEIGHT · ARTIFACT GATED**")
        st.write(
            "只有 TRAIN fit + VALIDATION alpha + M2 CALIBRATION + TEST_UNTOUCHED promotion report + human approval "
            "全部通過，才會改動 λ 與 1X2。"
        )

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
    "目前 v8 研究能力已經部署，梅花也已進入正式 Live computation；"
    "但 repository 尚無合格 M2 deployment artifact，因此目前不宣稱梅花已提高預測準確率。",
    icon="🛡️",
)

st.divider()
st.caption(
    "JARVIS 僅供研究與教育用途。奇門遁甲與梅花易數屬傳統術數；數值機率只接受可重現的 frozen artifact。"
)
