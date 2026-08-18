from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from jarvis.release import runtime_release_status


APP = Path(__file__).resolve().parents[1] / "pages" / "2_Live_Predictor.py"


def test_live_predictor_starts_and_casts_default_chart():
    release = runtime_release_status()
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not app.exception
    assert any("奇門遁甲足球研究系統・JARVIS" in item.value for item in app.title)
    assert any(
        f"Web App v{release.web_app_version}" in item.value
        and f"Live Predictor v{release.live_predictor_code_version}" in item.value
        for item in app.caption
    )
    assert any("frozen Live Predictor champion compatibility path" in item.value for item in app.markdown)
    assert any("JARVIS v8 Web" in item.value for item in app.subheader)
    assert any(item.label == "完整基礎語義" and item.value == "108" for item in app.metric)
    assert any(item.label == "核心組合覆蓋" and item.value == "5,184" for item in app.metric)
    assert any(item.label == "關係矩陣" and item.value == "306" for item in app.metric)

    cast_button = next(item for item in app.button if item.label == "建立／重建奇門盤")
    cast_button.click().run(timeout=30)

    assert not app.exception
    metric_labels = {item.label for item in app.metric}
    assert {"遁局", "三元", "值符", "值使", "節氣"}.issubset(metric_labels)
    assert any("候選情境排序" in item.value for item in app.subheader)
    assert any("已鎖定的問題與盤前稽核" in item.value for item in app.subheader)
