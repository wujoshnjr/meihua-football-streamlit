from pathlib import Path

from streamlit.testing.v1 import AppTest

from version import __version__


PAGE = Path(__file__).resolve().parents[1] / "pages" / "0_JARVIS_v8_Dashboard.py"


def test_v8_dashboard_starts_and_keeps_promotion_gate_visible():
    app = AppTest.from_file(str(PAGE), default_timeout=30).run()

    assert not app.exception
    assert any("JARVIS v8 Dashboard" in item.value for item in app.title)
    assert any(f"Web app v{__version__}" in item.value for item in app.caption)
    assert any("v8 控制台" in item.value for item in app.success)
    assert any("沒有真實 chronological frozen artifacts" in item.value for item in app.warning)
