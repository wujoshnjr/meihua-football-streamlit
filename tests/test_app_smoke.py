from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


def test_operation_stark_home_opens_without_obsolete_research_product():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()

    assert not app.exception
    assert any("JARVIS 術數 AI" in item.value for item in app.title)
    assert any("JARVIS 起局／起卦、原典審查與知識整理" in item.value for item in app.caption)
    markdown_text = " ".join(item.value for item in app.markdown)
    info_text = " ".join(item.value for item in app.info)
    all_visible_text = f"{markdown_text} {info_text}"
    assert "奇門遁甲" in all_visible_text
    assert "梅花" in all_visible_text
    assert "周易" in all_visible_text
    assert "384/384" in all_visible_text
    assert "焦氏易林" in all_visible_text
    assert "4096/4096" in all_visible_text
    assert "M0–M3" not in all_visible_text
    assert "Dynamic Football" not in all_visible_text
