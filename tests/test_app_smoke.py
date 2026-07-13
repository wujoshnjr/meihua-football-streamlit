from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest


APP = Path(__file__).resolve().parents[1] / "app.py"


def test_streamlit_app_loads_as_casting_only_product() -> None:
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not app.exception
    assert app.title[0].value == "梅花易數完整排卦系統 v5.0.0"
    assert any("只排卦，不解卦" in item.value for item in app.success)


def test_streamlit_form_casts_without_score_or_ai_output() -> None:
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    for index, value in enumerate(["甲 vs 乙", "甲", "乙", "足球賽前內容"]):
        app.text_input[index].set_value(value)
    for index, value in enumerate(["甲乙丙丁", "甲乙丙", "甲乙丙丁戊", "補充"]):
        app.text_area[index].set_value(value)
    app.button[0].click().run()

    assert not app.exception
    assert any(message.value.startswith("排卦完成：") for message in app.success)
    labels = {metric.label for metric in app.metric}
    assert {"體卦／下卦", "用卦／上卦", "本卦", "互卦", "變卦", "動爻"}.issubset(labels)
    rendered = "\n".join(item.value for item in app.markdown)
    assert "首選比分" not in rendered
    assert "Poisson" not in rendered
    assert "AI推理" not in rendered
