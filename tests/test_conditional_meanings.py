from __future__ import annotations

from datetime import datetime

from casting_structure import build_casting_structure
from meihua_engine import calculate_casting
from models import CastingInput


CAST_AT = datetime(2026, 7, 15, 20, 45, 39)


def _cast(body_count: int, use_count: int, moving_line: int):
    casting = CastingInput(
        title="甲 vs 乙",
        body_name="甲",
        use_name="乙",
        body_text="甲" * body_count,
        use_text="乙" * use_count,
        full_text="丙" * moving_line,
    )
    return calculate_casting(casting, cast_at=CAST_AT)


def test_high_energy_li_changing_to_gen_prioritizes_attack_stopping() -> None:
    result = _cast(3, 1, 1)
    conditional = build_casting_structure(result)["conditional_meanings"]
    body = conditional["body_path"]

    assert body["transition"] == "離→艮"
    assert (result.relation, result.changed_relation) == ("體剋用", "體生用")
    changed = body["stages"][1]
    assert changed["trigram"] == "艮"
    assert changed["prioritized_meanings"][0]["meaning"] == "攻勢中斷"
    assert "gen_attack_stops" in {rule["rule_id"] for rule in changed["matched_rules"]}


def test_unchanged_strong_gen_prioritizes_holding_and_stable_defense() -> None:
    result = _cast(7, 3, 4)
    conditional = build_casting_structure(result)["conditional_meanings"]
    body = conditional["body_path"]
    stage = body["stages"][0]

    assert body["transition"] == "艮→艮"
    assert stage["prioritized_meanings"][0]["meaning"] == "守成"
    matched = {rule["rule_id"] for rule in stage["matched_rules"]}
    assert {"gen_holding", "gen_stable_defense"}.issubset(matched)


def test_all_384_casting_combinations_produce_auditable_conditional_paths() -> None:
    for body_count in range(1, 9):
        for use_count in range(1, 9):
            for moving_line in range(1, 7):
                result = _cast(body_count, use_count, moving_line)
                conditional = build_casting_structure(result)["conditional_meanings"]
                for key in ("body_path", "use_path"):
                    path = conditional[key]
                    assert path["stages"]
                    assert all(len(stage["possible_meanings"]) == 8 for stage in path["stages"])
                    assert all(len(stage["prioritized_meanings"]) == 3 for stage in path["stages"])
                    assert all(stage["active_signals"] for stage in path["stages"])
