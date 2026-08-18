from pathlib import Path

from streamlit.testing.v1 import AppTest

from jarvis.release import runtime_release_status


PAGE = Path(__file__).resolve().parents[1] / "pages" / "1_Research_Lab.py"


def test_research_lab_starts_without_promoting_research_models():
    release = runtime_release_status()
    app = AppTest.from_file(str(PAGE), default_timeout=30).run()

    assert not app.exception
    assert any("JARVIS v8 Research Lab" in item.value for item in app.title)
    assert any(
        f"Web app v{release.web_app_version}" in item.value
        and f"Live predictor code v{release.live_predictor_code_version}" in item.value
        for item in app.caption
    )
    assert any("RESEARCH GATE" in item.value for item in app.warning)
    assert any("M0" in item.value and "Football only" in item.value for item in app.markdown)
    assert any("請先回主頁" in item.value for item in app.info)
