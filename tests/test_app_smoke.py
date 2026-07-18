from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from meihua_engine import count_symbols


APP = Path(__file__).resolve().parents[1] / "app.py"


def _button(app: AppTest, label: str):
    matches = [item for item in app.button if item.label == label]
    assert len(matches) == 1
    return matches[0]


def _text_area(app: AppTest, label: str):
    matches = [item for item in app.text_area if item.label == label]
    assert len(matches) == 1
    return matches[0]


def _pad_to(text: str, target: int) -> str:
    return text + "穩" * (target - count_symbols(text))


def _self_narrative(name: str) -> str:
    return _pad_to(
        "\n".join(
            (
                f"我是{name}。",
                "目前我的客觀狀態為略正面，陣容完整。",
                "我的士氣與比賽壓力為中性，壓力明確。",
                "我的預計比賽策略是主動控球。",
                "我主要依靠的組織支點是後腰出球。",
                "我的主要進攻通道是右路推進。",
                "我的主要防守結構是中位四後衛。",
                "我最大的相對優勢是邊路速度。",
                "我目前最明顯的限制是終結不穩。",
                "我最需要防範對手的是快速反擊。",
                "我希望在九十分鐘內減少失誤提高射門品質。",
            )
        ),
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
    assert app.title[0].value == "梅花易數完整排卦系統 v5.8.0"
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
    _button(app, "完整排卦").click().run()

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
    _button(app, "完整排卦").click().run()

    assert not app.exception
    assert any("請輸入體方名稱與用方名稱" in item.value for item in app.error)


def test_streamlit_form_rejects_text_outside_v3_input_protocol() -> None:
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    for index, value in enumerate(["甲", "乙", "足球賽前內容"]):
        app.text_input[index].set_value(value)
    for index, value in enumerate(["我是甲。", "我是乙。", "這場比賽由甲對陣乙。"]):
        app.text_area[index].set_value(value)
    _button(app, "完整排卦").click().run()

    assert not app.exception
    assert any("v3 起象輸入規格未通過" in item.value for item in app.error)
    assert "casting_result" not in app.session_state


def test_each_text_area_has_an_independent_one_click_clear_button() -> None:
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    values = {
        "體方自述（起象）": "體方測試內容",
        "用方自述（起象）": "用方測試內容",
        "賽前中性介紹（動爻）": "中性測試內容",
    }
    for label, value in values.items():
        _text_area(app, label).set_value(value)

    _button(app, "清除體方自述").click().run()
    assert _text_area(app, "體方自述（起象）").value == ""
    assert _text_area(app, "用方自述（起象）").value == values["用方自述（起象）"]
    assert _text_area(app, "賽前中性介紹（動爻）").value == values["賽前中性介紹（動爻）"]

    _button(app, "清除用方自述").click().run()
    assert _text_area(app, "用方自述（起象）").value == ""
    assert _text_area(app, "賽前中性介紹（動爻）").value == values["賽前中性介紹（動爻）"]

    _button(app, "清除賽前中性介紹").click().run()
    assert _text_area(app, "賽前中性介紹（動爻）").value == ""


def test_protocol_check_reports_counts_without_casting() -> None:
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    for index, value in enumerate(["甲", "乙", "足球賽前內容"]):
        app.text_input[index].set_value(value)
    values = [_self_narrative("甲"), _self_narrative("乙"), _neutral_introduction("甲", "乙")]
    for index, value in enumerate(values):
        app.text_area[index].set_value(value)

    _button(app, "只檢查格式與計數").click().run()

    assert not app.exception
    assert any("全部通過" in item.value for item in app.success)
    assert "casting_result" not in app.session_state
    metrics = {item.label: item.value for item in app.metric}
    assert metrics["體方自述（起象）"] == "180 數"
    assert metrics["用方自述（起象）"] == "180 數"
    assert metrics["賽前中性介紹（動爻）"] == "300 數"
