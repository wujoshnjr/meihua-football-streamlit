from __future__ import annotations

import streamlit as st


st.set_page_config(
    page_title="JARVIS 術數 AI · Operation STARK",
    page_icon="☯️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

home = st.Page("pages/00_Home.py", title="JARVIS", icon="🏠", default=True)
football_case = st.Page("pages/5_Football_Case.py", title="足球多層案件", icon="⚽", url_path="football-case")
qimen = st.Page("pages/1_Qimen_Cast.py", title="奇門起局", icon="🧭", url_path="qimen")
meihua = st.Page("pages/2_Meihua_Cast.py", title="梅花起卦", icon="☯️", url_path="meihua")
yuanling = st.Page("pages/6_Yuanling_Yanshu.py", title="元靈演數", icon="🔢", url_path="yuanling")
vault = st.Page("pages/3_Knowledge_Vault.py", title="知識庫", icon="📚", url_path="knowledge")
packet = st.Page("pages/4_AI_Packet.py", title="AI 解卦包", icon="🤖", url_path="packet")

navigation = st.navigation(
    {
        "足球": [home, football_case],
        "單術數": [qimen, meihua, yuanling],
        "知識與 AI": [vault, packet],
    },
    position="top",
)
navigation.run()
