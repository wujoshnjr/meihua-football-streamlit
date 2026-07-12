from streamlit.testing.v1 import AppTest


def test_streamlit_app_loads_without_runtime_exception() -> None:
    app = AppTest.from_file("app.py", default_timeout=30).run()
    assert not app.exception
    assert app.title[0].value == "梅花易數足球AI自主推理系統 v4.0.0"


def test_streamlit_prediction_form_renders_results_without_arrow_crash() -> None:
    app = AppTest.from_file("app.py", default_timeout=30).run()
    values = [
        "測試甲整體實力完整擅長控球推進與高位逼搶",
        "測試乙防守穩健依靠快速反擊與定位球製造機會",
        "本場只判斷九十分鐘雙方各有優勢勝負關鍵在中場控制轉換速度與禁區完成度",
        "只使用賽前資訊",
    ]
    for index, value in enumerate(values):
        app.text_area[index].set_value(value)
    app.button[0].click().run()
    assert not app.exception
    assert any(message.value.startswith("足球基線λ") for message in app.success)
    labels = {metric.label for metric in app.metric}
    assert {"基線首選", "首選", "最終首選"}.issubset(labels)
