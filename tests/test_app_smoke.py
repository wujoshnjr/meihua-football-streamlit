from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


def test_operation_stark_home_opens_without_obsolete_research_product():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()

    assert not app.exception
    assert any("JARVIS 術數 AI" in item.value for item in app.title)
    assert any("JARVIS 起局／起卦，ChatGPT 負責最後解讀" in item.value for item in app.caption)
    visible = " ".join(item.value for item in app.markdown)
    assert "奇門遁甲" in visible
    assert "梅花易數" in visible
    assert "M0–M3" not in visible
    assert "Dynamic Football" not in visible
