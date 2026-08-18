from __future__ import annotations

import streamlit as st


st.set_page_config(
    page_title="JARVIS v8",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

home = st.Page(
    "pages/00_Home.py",
    title="JARVIS",
    icon="🏠",
    default=True,
)
live_predictor = st.Page(
    "pages/3_Live_Meihua.py",
    title="Live Predictor",
    icon="🎯",
    url_path="predict",
)
audit_workbench = st.Page(
    "pages/2_Live_Predictor.py",
    title="Audit Workbench",
    icon="🧭",
    url_path="workbench",
)
dashboard = st.Page(
    "pages/0_JARVIS_v8_Dashboard.py",
    title="v8 Dashboard",
    icon="📊",
    url_path="dashboard",
)
research_lab = st.Page(
    "pages/1_Research_Lab.py",
    title="Research Lab",
    icon="🧪",
    url_path="research",
)

navigation = st.navigation(
    {
        "": [home, live_predictor, audit_workbench],
        "Research": [dashboard, research_lab],
    },
    position="top",
)
navigation.run()
