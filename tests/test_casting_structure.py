from __future__ import annotations

from datetime import datetime

from casting_structure import (
    build_casting_structure,
    build_moving_line_dynamics,
    seasonal_status,
)
from meihua_engine import calculate_casting
from models import CastingInput


def _casting(full_text: str = "甲乙丙丁戊") -> CastingInput:
    return CastingInput(
        title="甲 vs 乙",
        body_name="甲",
        use_name="乙",
        body_text="甲乙丙丁",
        use_text="甲乙丙",
        full_text=full_text,
    )


def test_moving_line_classics_and_dynamics_are_structured() -> None:
    result = calculate_casting(_casting(), cast_at=datetime(2026, 7, 13, 15, 30))
    payload = build_casting_structure(result)
    classics = payload["moving_line_classics"]
    dynamics = payload["moving_line_dynamics"]

    assert result.main_hexagram == "火雷噬嗑"
    assert result.changed_hexagram == "天雷無妄"
    assert classics == {
        "hexagram": "火雷噬嗑",
        "position": 5,
        "position_name": "五爻",
        "line_label": "六五",
        "line_text": "六五：噬乾肉，得黃金，貞厲，無咎。",
        "small_image_text": "貞厲無咎，得當也。",
    }
    assert dynamics["position"] == 5
    assert dynamics["is_yang_position"] is True
    assert dynamics["is_correct_position"] is False
    assert dynamics["position_status"] == "失位"
    assert dynamics["is_central"] is True
    assert dynamics["central_status"] == "得中"
    assert dynamics["has_correspondence"] is False
    assert dynamics["corresponding_line"] == 2
    assert dynamics["relation_to_corresponding_line"] == "不應"
    assert [item["moving_line_role"] for item in dynamics["adjacent_relations"]] == [
        "乘",
        "承",
    ]
    assert [item["order"] for item in dynamics["adjacent_relations"]] == ["逆", "順"]
    assert "乘四爻" in dynamics["adjacent_relation"]
    assert "承上爻" in dynamics["adjacent_relation"]


def test_main_and_changed_hexagram_classics_are_exported() -> None:
    result = calculate_casting(_casting(), cast_at=datetime(2026, 7, 13, 15, 30))
    classics = build_casting_structure(result)["hexagram_classics"]

    assert classics["main_hexagram"]["name"] == "火雷噬嗑"
    assert classics["main_hexagram"]["gua_ci"] == "噬嗑：亨。利用獄。"
    assert classics["main_hexagram"]["tuan_text"]
    assert classics["main_hexagram"]["da_xiang_text"] == "雷電噬嗑；先王以明罰敕法。"
    assert classics["changed_hexagram"]["name"] == "天雷無妄"
    assert classics["changed_hexagram"]["gua_ci"].startswith("無妄：元亨")
    assert classics["changed_hexagram"]["tuan_text"]
    assert classics["changed_hexagram"]["da_xiang_text"]


def test_seasonal_strength_uses_one_frozen_month_command_rule() -> None:
    assert {
        element: seasonal_status("木", element)
        for element in ["木", "火", "水", "金", "土"]
    } == {"木": "旺", "火": "相", "水": "休", "金": "囚", "土": "死"}

    result = calculate_casting(_casting(), cast_at=datetime(2026, 7, 13, 15, 30))
    strength = build_casting_structure(result)["seasonal_strength"]
    assert strength["month_branch"] == "午"
    assert strength["month_element"] == "火"
    assert strength["hour_branch"] == "申"
    assert strength["hour_element"] == "金"
    assert strength["body_before_element"] == "木"
    assert strength["use_before_element"] == "火"
    assert strength["body_after_element"] == "木"
    assert strength["use_after_element"] == "金"
    assert strength["body_before"] == "休"
    assert strength["use_before"] == "旺"
    assert strength["body_after"] == "休"
    assert strength["use_after"] == "死"
    assert strength["strength_shift"] == "體方持平／用方轉弱"


def test_correspondence_and_adjacent_relations_cover_all_six_positions() -> None:
    corresponding = {1: 4, 2: 5, 3: 6, 4: 1, 5: 2, 6: 3}
    for position in range(1, 7):
        result = calculate_casting(
            _casting("中" * position),
            cast_at=datetime(2026, 7, 13, 15, 30),
        )
        dynamics = build_moving_line_dynamics(result)
        assert dynamics["corresponding_line"] == corresponding[position]
        assert len(dynamics["adjacent_relations"]) == (1 if position in {1, 6} else 2)
        assert all(item["is_adjacent_bi"] for item in dynamics["adjacent_relations"])
