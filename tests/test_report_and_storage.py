from __future__ import annotations

import json
from pathlib import Path

from config import AppConfig
from meihua_engine import calculate_casting
from models import CastingInput
from report_builder import build_markdown_report
from storage import CastingStore, build_casting_row, casting_fingerprint


def fixture() -> tuple[CastingInput, object]:
    casting = CastingInput(
        title="甲 vs 乙",
        body_name="甲",
        use_name="乙",
        body_text="甲乙丙丁",
        use_text="甲乙丙",
        full_text="甲乙丙丁戊",
        context_notes="不參與取數",
    )
    return casting, calculate_casting(casting)


def test_report_contains_complete_casting_but_no_prediction_sections() -> None:
    casting, result = fixture()
    report = build_markdown_report(casting, result)

    assert "取數計算" in report
    assert "本卦六爻排盤" in report
    assert "本、互、動、變結構" in report
    assert "卦辭" in report and "彖傳" in report and "小象" in report
    assert "只排卦，不解卦" in report
    assert "首選比分" not in report
    assert "Poisson" not in report
    assert "GitHub Models" not in report


def test_casting_storage_is_idempotent_and_persists_full_json(tmp_path: Path) -> None:
    casting, result = fixture()
    config = AppConfig(data_dir=tmp_path / "data", reports_dir=tmp_path / "reports")
    config.ensure_dirs()
    store = CastingStore(config)
    row = build_casting_row(casting, result, "reports/test.md")

    first, first_action = store.upsert(row)
    second, second_action = store.upsert(row)

    assert first_action == "新增排卦"
    assert second_action == "確認既有排卦"
    assert len(first) == len(second) == 1
    assert second.iloc[0]["排卦指紋"] == casting_fingerprint(casting, result)
    payload = json.loads(second.iloc[0]["完整排盤JSON"])
    assert payload["main_hexagram"] == result.main_hexagram
    assert len(payload["line_table"]) == 6
