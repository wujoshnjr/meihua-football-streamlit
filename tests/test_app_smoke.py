from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from jarvis.release import runtime_release_status


APP = Path(__file__).resolve().parents[1] / "app.py"


def test_streamlit_entrypoint_opens_product_home_instead_of_legacy_workbench():
    release = runtime_release_status()
    app = AppTest.from_file(str(APP), default_timeout=30).run()

    assert not app.exception
    assert any("Football Intelligence Research Platform" in item.value for item in app.markdown)
    assert any("足球預測，研究與實戰分開" in item.value for item in app.markdown)
    assert any(f"v{release.live_predictor_code_version}" in item.value for item in app.markdown)
    assert any(f"v{release.web_app_version}" in item.value for item in app.markdown)
    assert any("Automatic Promotion" in item.value and "OFF" in item.value for item in app.markdown)
    assert any("目前 v8 研究能力已經部署" in item.value for item in app.info)
