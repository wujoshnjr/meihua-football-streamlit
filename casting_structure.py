from __future__ import annotations

from typing import Any

from knowledge_loader import load_hexagram_interpretations, load_hexagrams
from meihua_engine import CONTROLS, ELEMENTS, GENERATES, line_label
from models import HexagramResult
from najia_structure import BRANCH_ELEMENTS, LUNAR_MONTH_BRANCHES, build_najia_analysis


STRENGTH_RANK = {"死": 1, "囚": 2, "休": 3, "相": 4, "旺": 5}
POSITION_NAMES = {1: "初爻", 2: "二爻", 3: "三爻", 4: "四爻", 5: "五爻", 6: "上爻"}


def seasonal_status(month_element: str, target_element: str) -> str:
    """Return 旺相休囚死 using one frozen month-command relationship table."""

    if month_element == target_element:
        return "旺"
    if GENERATES[month_element] == target_element:
        return "相"
    if GENERATES[target_element] == month_element:
        return "休"
    if CONTROLS[target_element] == month_element:
        return "囚"
    if CONTROLS[month_element] == target_element:
        return "死"
    raise ValueError(f"無法判定月令旺衰：{month_element}/{target_element}")


def _hexagram_classics(name: str) -> dict[str, Any]:
    item = load_hexagrams()[name]
    return {
        "name": name,
        "short_name": str(item["short_name"]),
        "sequence": int(item["sequence"]),
        "unicode": str(item["unicode"]),
        "gua_ci": str(item["judgment_text"]),
        "tuan_text": str(item["tuan_text"]),
        "da_xiang_text": str(item["great_image_text"]),
    }


def build_hexagram_classics(result: HexagramResult) -> dict[str, Any]:
    return {
        "main_hexagram": _hexagram_classics(result.main_hexagram),
        "changed_hexagram": _hexagram_classics(result.changed_hexagram),
    }


def _hexagram_meaning(name: str) -> dict[str, Any]:
    item = load_hexagram_interpretations()["hexagrams"][name]
    return {
        "name": name,
        "short_name": str(item["short_name"]),
        "sequence": int(item["sequence"]),
        "unicode": str(item["unicode"]),
        "classical_meaning": dict(item["classical_meaning"]),
        "football_mapping": dict(item["football_mapping"]),
    }


def build_hexagram_meanings(result: HexagramResult) -> dict[str, Any]:
    return {
        "main_hexagram": _hexagram_meaning(result.main_hexagram),
        "mutual_hexagram": _hexagram_meaning(result.mutual_hexagram),
        "changed_hexagram": _hexagram_meaning(result.changed_hexagram),
        "scope_note": load_hexagram_interpretations()["scope"],
    }


def build_moving_line_classics(result: HexagramResult) -> dict[str, Any]:
    item = load_hexagrams()[result.main_hexagram]
    line = item["lines"][result.moving_line - 1]
    return {
        "hexagram": result.main_hexagram,
        "position": result.moving_line,
        "position_name": POSITION_NAMES[result.moving_line],
        "line_label": result.moving_line_label,
        "line_text": str(line["classic_text"]),
        "small_image_text": str(line["small_image_text"]),
    }


def _line_type(bit: str) -> str:
    return "陽" if bit == "1" else "陰"


def _pair_order(upper_bit: str, lower_bit: str) -> tuple[str, str]:
    if upper_bit == "1" and lower_bit == "0":
        return "剛乘柔／柔承剛", "順"
    if upper_bit == "0" and lower_bit == "1":
        return "柔乘剛／剛承柔", "逆"
    kind = "剛" if upper_bit == "1" else "柔"
    return f"{kind}{kind}相比", "同類"


def _adjacent_relations(lines: str, position: int) -> list[dict[str, Any]]:
    relations: list[dict[str, Any]] = []
    moving_bit = lines[position - 1]
    if position > 1:
        neighbor_position = position - 1
        neighbor_bit = lines[neighbor_position - 1]
        pair_structure, order = _pair_order(moving_bit, neighbor_bit)
        relations.append(
            {
                "neighbor_line": neighbor_position,
                "neighbor_position_name": POSITION_NAMES[neighbor_position],
                "neighbor_line_label": line_label(neighbor_position, neighbor_bit),
                "neighbor_line_type": _line_type(neighbor_bit),
                "direction": "下鄰",
                "moving_line_role": "乘",
                "is_adjacent_bi": True,
                "pair_structure": pair_structure,
                "order": order,
            }
        )
    if position < 6:
        neighbor_position = position + 1
        neighbor_bit = lines[neighbor_position - 1]
        pair_structure, order = _pair_order(neighbor_bit, moving_bit)
        relations.append(
            {
                "neighbor_line": neighbor_position,
                "neighbor_position_name": POSITION_NAMES[neighbor_position],
                "neighbor_line_label": line_label(neighbor_position, neighbor_bit),
                "neighbor_line_type": _line_type(neighbor_bit),
                "direction": "上鄰",
                "moving_line_role": "承",
                "is_adjacent_bi": True,
                "pair_structure": pair_structure,
                "order": order,
            }
        )
    return relations


def build_moving_line_dynamics(result: HexagramResult) -> dict[str, Any]:
    position = result.moving_line
    lines = result.main_lines_bottom_up
    moving_bit = lines[position - 1]
    corresponding_line = position + 3 if position <= 3 else position - 3
    corresponding_bit = lines[corresponding_line - 1]
    is_yang_position = position % 2 == 1
    is_correct_position = (moving_bit == "1") == is_yang_position
    is_central = position in {2, 5}
    has_correspondence = moving_bit != corresponding_bit
    adjacent_relations = _adjacent_relations(lines, position)
    adjacent_summary = "；".join(
        f"{relation['moving_line_role']}{relation['neighbor_position_name']}（比，"
        f"{relation['pair_structure']}，{relation['order']}）"
        for relation in adjacent_relations
    )
    return {
        "position": position,
        "position_name": POSITION_NAMES[position],
        "line_label": result.moving_line_label,
        "line_type": _line_type(moving_bit),
        "is_yang_position": is_yang_position,
        "is_correct_position": is_correct_position,
        "position_status": "得位" if is_correct_position else "失位",
        "is_central": is_central,
        "central_status": "得中" if is_central else "不得中",
        "is_central_and_correct": is_central and is_correct_position,
        "has_correspondence": has_correspondence,
        "corresponding_line": corresponding_line,
        "corresponding_position_name": POSITION_NAMES[corresponding_line],
        "corresponding_line_label": line_label(corresponding_line, corresponding_bit),
        "corresponding_line_type": _line_type(corresponding_bit),
        "relation_to_corresponding_line": "相應" if has_correspondence else "不應",
        "has_riding_relation": position > 1,
        "has_supporting_relation": position < 6,
        "has_adjacent_bi_relation": bool(adjacent_relations),
        "adjacent_relation": adjacent_summary,
        "adjacent_relations": adjacent_relations,
        "rule_note": "相應以初四、二五、三上陰陽相異判定；乘承比只列客觀爻位結構，不直接判定吉凶。",
    }


def _shift(before: str, after: str) -> str:
    difference = STRENGTH_RANK[after] - STRENGTH_RANK[before]
    if difference > 0:
        return "轉強"
    if difference < 0:
        return "轉弱"
    return "持平"


def build_seasonal_strength(result: HexagramResult) -> dict[str, Any]:
    month = result.casting_moment.lunar_month
    month_branch = LUNAR_MONTH_BRANCHES[month]
    month_element = BRANCH_ELEMENTS[month_branch]
    hour_branch = result.casting_moment.shichen
    hour_element = BRANCH_ELEMENTS[hour_branch]
    body_before_element = result.body_element
    use_before_element = result.use_element
    body_after_element = ELEMENTS[result.changed_body_gua]
    use_after_element = ELEMENTS[result.changed_use_gua]
    body_before = seasonal_status(month_element, body_before_element)
    use_before = seasonal_status(month_element, use_before_element)
    body_after = seasonal_status(month_element, body_after_element)
    use_after = seasonal_status(month_element, use_after_element)
    body_shift = _shift(body_before, body_after)
    use_shift = _shift(use_before, use_after)
    return {
        "lunar_month": month,
        "is_leap_month": result.casting_moment.lunar_is_leap_month,
        "month_branch": month_branch,
        "month_element": month_element,
        "hour_branch": hour_branch,
        "hour_element": hour_element,
        "body_before_element": body_before_element,
        "use_before_element": use_before_element,
        "body_after_element": body_after_element,
        "use_after_element": use_after_element,
        "body_before": body_before,
        "use_before": use_before,
        "body_after": body_after,
        "use_after": use_after,
        "body_shift": body_shift,
        "use_shift": use_shift,
        "strength_shift": f"體方{body_shift}／用方{use_shift}",
        "status_scale": ["旺", "相", "休", "囚", "死"],
        "rule_note": "旺衰固定依農曆月建五行判定：同月令為旺、月令所生為相、生月令者為休、克月令者為囚、月令所克為死；時支五行只列輔助，不覆寫月令狀態。",
    }


def build_casting_structure(result: HexagramResult) -> dict[str, Any]:
    return {
        "hexagram_classics": build_hexagram_classics(result),
        "hexagram_meanings": build_hexagram_meanings(result),
        "moving_line_classics": build_moving_line_classics(result),
        "moving_line_dynamics": build_moving_line_dynamics(result),
        "seasonal_strength": build_seasonal_strength(result),
        "najia_analysis": build_najia_analysis(result),
    }


__all__ = [
    "BRANCH_ELEMENTS",
    "LUNAR_MONTH_BRANCHES",
    "build_casting_structure",
    "build_hexagram_classics",
    "build_hexagram_meanings",
    "build_moving_line_classics",
    "build_moving_line_dynamics",
    "build_seasonal_strength",
    "seasonal_status",
]
