from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


def run_page(relative: str):
    return AppTest.from_file(str(ROOT / relative), default_timeout=30).run()


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
    assert any("足球雙術數案件" in item.value for item in app.title)


def test_yuanling_research_page_starts_with_casting_guide():
    app = run_page("pages/6_Yuanling_Yanshu.py")
    assert not app.exception
    assert any("元靈經" in item.value for item in app.title)
    markdown_text = " ".join(item.value for item in app.markdown)
    assert "演數七要" in markdown_text
    assert "日奇門" in markdown_text
