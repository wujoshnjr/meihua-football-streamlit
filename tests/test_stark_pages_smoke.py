from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


def run_page(relative: str):
    return AppTest.from_file(str(ROOT / relative), default_timeout=30).run()



def _widget_by_label(items, label: str):
    for item in items:
        if item.label == label:
            return item
    raise AssertionError(f"找不到 widget: {label}")


def _button_by_label(app, label: str):
    for item in app.button:
        if item.label == label:
            return item
    raise AssertionError(f"找不到 button: {label}")

def test_qimen_cast_page_starts():
    app = run_page("pages/1_Qimen_Cast.py")
    assert not app.exception
    assert any("奇門遁甲起局" in item.value for item in app.title)


def test_meihua_cast_page_starts():
    app = run_page("pages/2_Meihua_Cast.py")
    assert not app.exception
    assert any("梅花易數起卦" in item.value for item in app.title)


def test_knowledge_vault_page_starts():
    app = run_page("pages/3_Knowledge_Vault.py")
    assert not app.exception
    assert any("知識庫" in item.value for item in app.title)
    markdown_text = " ".join(item.value for item in app.markdown)
    assert "元靈" in markdown_text


def test_ai_packet_page_starts_without_packet():
    app = run_page("pages/4_AI_Packet.py")
    assert not app.exception
    assert any("AI 解卦包" in item.value for item in app.title)


def test_football_case_workspace_starts():
    app = run_page("pages/5_Football_Case.py")
    assert not app.exception
    assert any("足球多層術數案件" in item.value for item in app.title)


def test_liuyao_page_starts():
    app = run_page("pages/7_Liuyao_Cast.py")
    assert not app.exception
    assert any("六爻納甲" in item.value for item in app.title)


def test_liuyao_submit_executes_chart_branch():
    app = run_page("pages/7_Liuyao_Cast.py")
    _widget_by_label(app.text_area, "占問內容").set_value("測試六爻納甲排盤。")
    _button_by_label(app, "建立 LIUYAO_PACKET_V1").click()
    app.run()

    assert not app.exception
    assert any("六爻 packet 已建立" in item.value for item in app.success)
    metric_values = {item.label: str(item.value) for item in app.metric}
    assert metric_values["本卦"] == "坤為地"
    assert metric_values["卦宮"].startswith("坤宮")
    markdown_text = " ".join(item.value for item in app.markdown)
    info_text = " ".join(item.value for item in app.info)
    assert "六爻排盤" in markdown_text
    assert "用神／題型入口" in markdown_text
    assert "AI 解卦包" in info_text


def test_yuanling_research_page_starts_with_casting_guide():
    app = run_page("pages/6_Yuanling_Yanshu.py")
    assert not app.exception
    assert any("元靈經" in item.value for item in app.title)
    markdown_text = " ".join(item.value for item in app.markdown)
    assert "演數七要" in markdown_text
    assert "日奇門" in markdown_text
    assert "V1_2" not in markdown_text


def test_yuanling_experiment_submit_executes_result_branch():
    app = run_page("pages/6_Yuanling_Yanshu.py")
    _widget_by_label(app.selectbox, "模式").set_value("RIQIMEN_QIYAO_EXPERIMENT")
    _button_by_label(app, "建立 YUANLING_YANSHU_PACKET_V1_3").click()
    app.run()

    assert not app.exception
    assert any("Yuanling packet 已建立" in item.value for item in app.success)
    markdown_text = " ".join(item.value for item in app.markdown)
    assert "日奇門 Base" in markdown_text
    assert any(
        item.label == "局" and str(item.value).endswith("局")
        for item in app.metric
    )


def test_football_form_submit_builds_full_case_bundle():
    app = run_page("pages/5_Football_Case.py")
    _widget_by_label(app.text_input, "主隊").set_value("A隊")
    _widget_by_label(app.text_input, "客隊").set_value("B隊")
    _widget_by_label(app.text_input, "賽事名稱（事件身份啟用時必填）").set_value("測試盲測聯賽")
    _widget_by_label(app.text_input, "賽季（例如 2026-27）").set_value("2026-27")
    _widget_by_label(app.text_input, "主隊官方英文全名").set_value("Team A")
    _widget_by_label(app.text_input, "客隊官方英文全名").set_value("Team B")
    _button_by_label(app, "建立 JARVIS 多層 Case Bundle V2").click()
    app.run()

    assert not app.exception
    assert any("多層案件建立完成" in item.value for item in app.success)
    metric_values = {item.label: str(item.value) for item in app.metric}
    assert metric_values["Alignment"] == "PASS"
    assert metric_values["Bundle SHA"] == "PASS"
    assert metric_values["Differentiation"] in {
        "EVENT_READY__PARTICIPANT_MISSING",
        "EVENT_AND_PARTICIPANT_READY",
    }
    markdown_text = " ".join(item.value for item in app.markdown)
    assert "Event / Participant Differentiation" in markdown_text
