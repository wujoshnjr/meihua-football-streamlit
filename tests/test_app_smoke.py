from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest


APP = Path(__file__).resolve().parents[1] / "app.py"


def test_streamlit_app_loads_as_casting_only_product() -> None:
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not app.exception
    assert app.title[0].value == "梅花易數完整排卦系統 v5.4.0"
    assert any("只排卦，不解卦" in item.value for item in app.success)
    labels = {item.label for item in app.text_input}
    assert "體方名稱（vs 前）" in labels
    assert "用方名稱（vs 後）" in labels
    assert "事件／比賽名稱" not in labels
    assert any(">vs</div>" in item.value for item in app.markdown)
    selectbox_labels = {item.label for item in app.selectbox}
    assert {"本卦", "之卦"}.issubset(selectbox_labels)
    assert any("4,096 條林辭" in item.value for item in app.caption)


def test_streamlit_form_casts_without_score_or_ai_output() -> None:
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    for index, value in enumerate(["甲", "乙", "足球賽前內容"]):
        app.text_input[index].set_value(value)
    for index, value in enumerate(["甲乙丙丁", "甲乙丙", "甲乙丙丁戊"]):
        app.text_area[index].set_value(value)
    app.button[0].click().run()

    assert not app.exception
    assert any(message.value.startswith("排卦完成：") for message in app.success)
    casting = app.session_state["casting_input"]
    assert casting.title == "甲 vs 乙"
    assert casting.body_name == "甲"
    assert casting.use_name == "乙"
    assert casting.context_notes == ""
    assert len(app.text_area) == 3
    labels = {metric.label for metric in app.metric}
    assert {"體卦／下卦", "用卦／上卦", "本卦", "互卦", "變卦", "動爻"}.issubset(labels)
    assert any("起卦農曆時間" in message.value for message in app.info)
    rendered = "\n".join(item.value for item in app.markdown)
    assert "首選比分" not in rendered
    assert "Poisson" not in rendered
    assert "AI推理" not in rendered


def test_streamlit_form_requires_both_party_names() -> None:
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    for index, value in enumerate(["", "乙", "足球賽前內容"]):
        app.text_input[index].set_value(value)
    for index, value in enumerate(["甲乙丙丁", "甲乙丙", "甲乙丙丁戊"]):
        app.text_area[index].set_value(value)
    app.button[0].click().run()

    assert not app.exception
    assert any("請輸入體方名稱與用方名稱" in item.value for item in app.error)
