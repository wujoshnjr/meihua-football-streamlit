from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from meihua_engine import count_symbols


APP = Path(__file__).resolve().parents[1] / "app.py"


def _pad_to(text: str, target: int) -> str:
    return text + "穩" * (target - count_symbols(text))


def _self_narrative(name: str) -> str:
    return _pad_to(
        f"我是{name}。目前我的整體狀態穩定。我的士氣專注。"
        "我的比賽策略是控制節奏。我主要依靠整體合作。"
        "我的進攻方式是持續施壓。我的防守方式是保持距離。"
        "我最大的優勢是行動一致。我最需要注意快速反擊。"
        "我希望在九十分鐘內掌握主動。",
        180,
    )


def _neutral_introduction(body: str, use: str) -> str:
    return _pad_to(
        f"這場比賽由{body}對陣{use}，判斷範圍為九十分鐘。"
        f"{body}希望主動控制節奏，{use}準備穩定防守，比賽關鍵在於雙方的攻守選擇。",
        300,
    )


def test_streamlit_app_loads_as_casting_only_product() -> None:
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not app.exception
    assert app.title[0].value == "梅花易數完整排卦系統 v5.7.0"
    assert any("完整排卦與卦義資料" in item.value for item in app.success)
    labels = {item.label for item in app.text_input}
    assert "體方名稱（vs 前）" in labels
    assert "用方名稱（vs 後）" in labels
    assert "事件／比賽名稱" not in labels
    assert any(">vs</div>" in item.value for item in app.markdown)
    text_area_labels = {item.label for item in app.text_area}
    assert text_area_labels == {"體方自述（起象）", "用方自述（起象）", "賽前中性介紹（動爻）"}
    selectbox_labels = {item.label for item in app.selectbox}
    assert {"本卦", "之卦"}.issubset(selectbox_labels)
    assert any("4,096 條林辭" in item.value for item in app.caption)


def test_streamlit_form_casts_without_score_or_ai_output() -> None:
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    for index, value in enumerate(["甲", "乙", "足球賽前內容"]):
        app.text_input[index].set_value(value)
    for index, value in enumerate(
        [_self_narrative("甲"), _self_narrative("乙"), _neutral_introduction("甲", "乙")]
    ):
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


def test_streamlit_form_rejects_text_outside_v2_input_protocol() -> None:
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    for index, value in enumerate(["甲", "乙", "足球賽前內容"]):
        app.text_input[index].set_value(value)
    for index, value in enumerate(["我是甲。", "我是乙。", "這場比賽由甲對陣乙。"]):
        app.text_area[index].set_value(value)
    app.button[0].click().run()

    assert not app.exception
    assert any("v2 起象輸入規格未通過" in item.value for item in app.error)
    assert "casting_result" not in app.session_state
