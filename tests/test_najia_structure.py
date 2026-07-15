from datetime import datetime

from meihua_engine import calculate_casting
from models import CastingInput
from najia_structure import PALACE_BY_LINES, branch_relation, build_najia_analysis, six_relative, xun_void


def _example():
    casting = CastingInput(
        title="伊朗 vs 紐西蘭", body_name="伊朗", use_name="紐西蘭",
        body_text="甲乙丙丁", use_text="甲乙", full_text="甲乙丙丁戊己",
    )
    return calculate_casting(casting, cast_at=datetime(2026, 7, 15, 20, 45, 39))


def test_requested_date_day_cycle_and_void_are_exact() -> None:
    result = _example()
    analysis = build_najia_analysis(result)
    assert result.casting_moment.day_ganzhi == "庚寅"
    assert analysis["day_cycle"]["month_branch"] == "未"
    assert analysis["xun_void"]["xun_name"] == "甲申旬"
    assert analysis["xun_void"]["void_branches"] == ["午", "未"]


def test_sui_example_has_exact_najia_world_and_response() -> None:
    result = _example()
    assert (result.main_hexagram, result.mutual_hexagram, result.changed_hexagram) == ("澤雷隨", "風山漸", "天雷無妄")
    chart = build_najia_analysis(result)["main_hexagram"]
    assert (chart["palace"], chart["palace_stage"], chart["world_line"], chart["response_line"]) == ("震", "歸魂", 3, 6)
    assert [line["gan_zhi"] for line in chart["lines"]] == ["庚子", "庚寅", "庚辰", "丁亥", "丁酉", "丁未"]
    assert chart["lines"][2]["roles"] == ["世"]
    assert chart["lines"][5]["roles"] == ["應"]
    assert chart["lines"][5]["is_void"] is True


def test_palace_void_relatives_and_branch_pairs_are_complete() -> None:
    assert len(PALACE_BY_LINES) == 64
    assert xun_void("甲子")["void_branches"] == ["戌", "亥"]
    assert xun_void("甲戌")["void_branches"] == ["申", "酉"]
    assert [six_relative("木", element) for element in ("木", "火", "土", "金", "水")] == ["兄弟", "子孫", "妻財", "官鬼", "父母"]
    assert branch_relation("子", "午") == "六沖"
    assert branch_relation("子", "丑") == "六合"
    assert branch_relation("子", "寅") is None
