from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from config import AppConfig
from meihua_engine import calculate_casting
from models import CastingInput
from report_builder import build_markdown_report
from storage import CastingStore, build_casting_row, casting_fingerprint


ROOT = Path(__file__).resolve().parents[1]


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
    return casting, calculate_casting(casting, cast_at=datetime(2026, 7, 13, 15, 30))


def test_report_contains_complete_casting_but_no_prediction_sections() -> None:
    casting, result = fixture()
    report = build_markdown_report(casting, result)

    assert "取數計算" in report
    assert "起卦農曆時間" in report
    assert "農曆二〇二六年（丙午年）五月廿九 庚申時（申時）" in report
    assert "本卦六爻排盤" in report
    assert "本、互、動、變結構" in report
    assert "卦辭" in report and "彖傳" in report and "小象" in report
    assert "只排卦，不解卦" in report
    assert "首選比分" not in report
    assert "Poisson" not in report
    assert "GitHub Models" not in report
    assert "補充資料" not in report


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
    assert second[0]["排卦指紋"] == casting_fingerprint(casting, result)
    payload = json.loads(second[0]["完整排盤JSON"])
    assert payload["main_hexagram"] == result.main_hexagram
    assert len(payload["line_table"]) == 6
    assert payload["casting_moment"]["lunar_year_ganzhi"] == "丙午"
    assert second[0]["建立時間"] == "2026-07-13 15:30:00"
    assert second[0]["起卦農曆時間"] == result.casting_moment.lunar_text
    assert second[0]["起卦時辰"] == "申時"

    csv_payload = store.csv_bytes(second).decode("utf-8-sig")
    assert "排卦指紋" in csv_payload
    assert "起卦農曆時間" in csv_payload
    assert casting_fingerprint(casting, result) in csv_payload


def test_recasting_same_text_gets_a_distinct_time_audit_record() -> None:
    casting, first = fixture()
    second = calculate_casting(
        casting,
        cast_at=datetime.fromisoformat(first.casting_moment.gregorian_iso) + timedelta(minutes=1),
    )

    assert first.main_hexagram == second.main_hexagram
    assert first.moving_line == second.moving_line
    assert first.casting_moment.gregorian_iso != second.casting_moment.gregorian_iso
    assert casting_fingerprint(casting, first) != casting_fingerprint(casting, second)


def test_existing_multiline_casting_csv_round_trips_without_data_loss() -> None:
    source = (ROOT / "data" / "meihua_castings.csv").read_text(encoding="utf-8-sig")
    rows = CastingStore._read_csv(source)

    assert rows
    assert "\n" in rows[0]["補充資料"]
    assert CastingStore._read_csv(CastingStore._csv_text(rows)) == rows
