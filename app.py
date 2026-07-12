from __future__ import annotations

from app_v33 import run_app
from quick_save_v33 import render_quick_save


# Streamlit Community Cloud restarts the process on deployment. Runtime modules
# therefore use one canonical import graph; no reload/monkey-patch layer is needed.
run_app()
render_quick_save()
