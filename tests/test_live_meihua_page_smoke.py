from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest


PAGE = Path(__file__).resolve().parents[1] / "pages" / "3_Live_Meihua.py"


def test_live_meihua_page_starts_and_builds_default_forecast():
    app = AppTest.from_file(str(PAGE), default_timeout=30).run()

    assert not app.exception
    assert any("JARVIS Live Predictor" in item.value for item in app.title)
    metric_labels = {item.label for item in app.metric}
    assert {"JARVIS", "Football base", "梅花引擎", "梅花機率層"}.issubset(metric_labels)
    assert any("梅花易數現在是 Live Predictor 的正式運算層" in item.value for item in app.success)
    assert any("沒有通過 TRAIN" in item.value for item in app.warning)

    build_button = next(
        item for item in app.button if item.label == "建立 Football + 梅花 Live 預測"
    )
    build_button.click().run(timeout=30)

    assert not app.exception
    metric_labels = {item.label for item in app.metric}
    assert {"主勝", "和局", "客勝", "本卦", "動爻", "體 / 用", "體用關係"}.issubset(metric_labels)
    assert any("梅花卦象已正式計算與記錄" in item.value for item in app.warning)
