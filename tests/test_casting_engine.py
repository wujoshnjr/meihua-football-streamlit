from __future__ import annotations

from meihua_engine import calculate_casting, count_symbols
from models import CastingInput


def casting(body: str, use: str, full: str) -> CastingInput:
    return CastingInput(
        title="測試排卦",
        body_name="甲",
        use_name="乙",
        body_text=body,
        use_text=use,
        full_text=full,
    )


def test_count_symbols_uses_frozen_mixed_language_rule() -> None:
    text = "阿根廷 Jonathan David Aït-Nouri 2026，3-2"
    assert count_symbols(text) == 9


def test_known_casting_has_complete_main_mutual_moving_changed_structure() -> None:
    result = calculate_casting(
        casting(
            "天地玄黃宇宙洪荒",  # 8 → 坤 / lower
            "天",  # 1 → 乾 / upper
            "天地玄黃宇宙",  # 6 → upper line
        )
    )

    assert result.body_gua == "坤"
    assert result.use_gua == "乾"
    assert result.main_hexagram == "天地否"
    assert result.main_lines_bottom_up == "000111"
    assert result.mutual_lower_gua == "艮"
    assert result.mutual_upper_gua == "巽"
    assert result.mutual_hexagram == "風山漸"
    assert result.moving_line == 6
    assert result.moving_line_label == "上九"
    assert result.moving_side == "用方"
    assert result.use_transition == "乾→兌"
    assert result.changed_hexagram == "澤地萃"
    assert result.changed_lines_bottom_up == "000110"
    assert sum(bool(row["is_moving"]) for row in result.line_table) == 1


def test_every_body_use_and_moving_line_combination_casts_without_interpretation() -> None:
    names: set[tuple[str, str, str]] = set()
    for body_count in range(1, 9):
        for use_count in range(1, 9):
            for moving_line in range(1, 7):
                result = calculate_casting(casting("甲" * body_count, "乙" * use_count, "中" * moving_line))
                assert len(result.main_lines_bottom_up) == 6
                assert len(result.mutual_lines_bottom_up) == 6
                assert len(result.changed_lines_bottom_up) == 6
                assert result.moving_line == moving_line
                assert sum(bool(row["is_moving"]) for row in result.line_table) == 1
                names.add((result.main_hexagram, result.mutual_hexagram, result.changed_hexagram))
    assert len(names) > 64
