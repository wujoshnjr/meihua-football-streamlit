from __future__ import annotations

import re
from datetime import datetime

from casting_time import build_casting_moment
from models import CastingInput, HexagramResult


BAGUA_BY_REMAINDER = {1: "乾", 2: "兌", 3: "離", 4: "震", 5: "巽", 6: "坎", 7: "艮", 0: "坤"}
BAGUA_NUMBER = {"乾": 1, "兌": 2, "離": 3, "震": 4, "巽": 5, "坎": 6, "艮": 7, "坤": 8}
# Every bit string is stored from the bottom line upward: 初爻 → 三爻 / 上爻.
BAGUA_LINES = {"乾": "111", "兌": "110", "離": "101", "震": "100", "巽": "011", "坎": "010", "艮": "001", "坤": "000"}
LINES_TO_BAGUA = {value: key for key, value in BAGUA_LINES.items()}
ELEMENTS = {"乾": "金", "兌": "金", "離": "火", "震": "木", "巽": "木", "坎": "水", "艮": "土", "坤": "土"}
GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
CONTROLS = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

HEXAGRAM_NAMES = {
    ("乾", "乾"): "乾為天", ("乾", "兌"): "天澤履", ("乾", "離"): "天火同人", ("乾", "震"): "天雷無妄", ("乾", "巽"): "天風姤", ("乾", "坎"): "天水訟", ("乾", "艮"): "天山遯", ("乾", "坤"): "天地否",
    ("兌", "乾"): "澤天夬", ("兌", "兌"): "兌為澤", ("兌", "離"): "澤火革", ("兌", "震"): "澤雷隨", ("兌", "巽"): "澤風大過", ("兌", "坎"): "澤水困", ("兌", "艮"): "澤山咸", ("兌", "坤"): "澤地萃",
    ("離", "乾"): "火天大有", ("離", "兌"): "火澤睽", ("離", "離"): "離為火", ("離", "震"): "火雷噬嗑", ("離", "巽"): "火風鼎", ("離", "坎"): "火水未濟", ("離", "艮"): "火山旅", ("離", "坤"): "火地晉",
    ("震", "乾"): "雷天大壯", ("震", "兌"): "雷澤歸妹", ("震", "離"): "雷火豐", ("震", "震"): "震為雷", ("震", "巽"): "雷風恆", ("震", "坎"): "雷水解", ("震", "艮"): "雷山小過", ("震", "坤"): "雷地豫",
    ("巽", "乾"): "風天小畜", ("巽", "兌"): "風澤中孚", ("巽", "離"): "風火家人", ("巽", "震"): "風雷益", ("巽", "巽"): "巽為風", ("巽", "坎"): "風水渙", ("巽", "艮"): "風山漸", ("巽", "坤"): "風地觀",
    ("坎", "乾"): "水天需", ("坎", "兌"): "水澤節", ("坎", "離"): "水火既濟", ("坎", "震"): "水雷屯", ("坎", "巽"): "水風井", ("坎", "坎"): "坎為水", ("坎", "艮"): "水山蹇", ("坎", "坤"): "水地比",
    ("艮", "乾"): "山天大畜", ("艮", "兌"): "山澤損", ("艮", "離"): "山火賁", ("艮", "震"): "山雷頤", ("艮", "巽"): "山風蠱", ("艮", "坎"): "山水蒙", ("艮", "艮"): "艮為山", ("艮", "坤"): "山地剝",
    ("坤", "乾"): "地天泰", ("坤", "兌"): "地澤臨", ("坤", "離"): "地火明夷", ("坤", "震"): "地雷復", ("坤", "巽"): "地風升", ("坤", "坎"): "地水師", ("坤", "艮"): "地山謙", ("坤", "坤"): "坤為地",
}

_LATIN_TOKEN = r"[A-Za-zÀ-ÖØ-öø-ÿĀ-ž]+(?:[-'’][A-Za-zÀ-ÖØ-öø-ÿĀ-ž]+)*"
_CJK_CHAR = r"[\u3400-\u4DBF\u4E00-\u9FFF]"
_NUMBER_TOKEN = r"\d+"
COUNT_PATTERN = re.compile(f"{_CJK_CHAR}|{_LATIN_TOKEN}|{_NUMBER_TOKEN}")


def count_symbols(text: str) -> int:
    """Count text with the project's frozen, auditable tokenization rule."""
    return len(COUNT_PATTERN.findall(text or ""))


def trigram_from_count(count: int) -> str:
    if count <= 0:
        raise ValueError("起卦字數必須大於 0")
    return BAGUA_BY_REMAINDER[count % 8]


def moving_line_from_count(total_count: int) -> int:
    if total_count <= 0:
        raise ValueError("完整段落字數必須大於 0")
    return total_count % 6 or 6


def hexagram_name(upper: str, lower: str) -> str:
    try:
        return HEXAGRAM_NAMES[(upper, lower)]
    except KeyError as exc:
        raise ValueError(f"無法辨識上下卦：{upper}/{lower}") from exc


def five_element_relation(body_element: str, use_element: str) -> tuple[str, str]:
    if body_element == use_element:
        return "equal", "比和"
    if GENERATES[body_element] == use_element:
        return "body_generates_use", "體生用"
    if GENERATES[use_element] == body_element:
        return "use_generates_body", "用生體"
    if CONTROLS[body_element] == use_element:
        return "body_controls_use", "體剋用"
    if CONTROLS[use_element] == body_element:
        return "use_controls_body", "用剋體"
    raise ValueError(f"無法辨識五行關係：{body_element}/{use_element}")


def line_label(position: int, bit: str) -> str:
    polarity = "九" if bit == "1" else "六"
    if position == 1:
        return f"初{polarity}"
    if position == 6:
        return f"上{polarity}"
    chinese_number = {2: "二", 3: "三", 4: "四", 5: "五"}[position]
    return f"{polarity}{chinese_number}"


def _line_table(main_lines: str, changed_lines: str, moving_line: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for position, (original, changed) in enumerate(zip(main_lines, changed_lines, strict=True), start=1):
        rows.append(
            {
                "position": position,
                "position_name": ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"][position - 1],
                "line_label": line_label(position, original),
                "original_bit": original,
                "original_type": "陽" if original == "1" else "陰",
                "original_symbol": "⚊" if original == "1" else "⚋",
                "is_moving": position == moving_line,
                "moving_marker": "○" if position == moving_line and original == "1" else "×" if position == moving_line else "",
                "changed_bit": changed,
                "changed_type": "陽" if changed == "1" else "陰",
                "changed_symbol": "⚊" if changed == "1" else "⚋",
                "layer": "下卦／體卦" if position <= 3 else "上卦／用卦",
            }
        )
    return rows


def calculate_casting(casting: CastingInput, *, cast_at: datetime | None = None) -> HexagramResult:
    body_count = count_symbols(casting.body_text)
    use_count = count_symbols(casting.use_text)
    total_count = count_symbols(casting.full_text)
    if not all([body_count, use_count, total_count]):
        raise ValueError("體方段落、用方段落與完整段落都必須含有可計數文字")

    body_gua = trigram_from_count(body_count)
    use_gua = trigram_from_count(use_count)
    moving_line = moving_line_from_count(total_count)
    main_lines = BAGUA_LINES[body_gua] + BAGUA_LINES[use_gua]

    mutual_lower = LINES_TO_BAGUA[main_lines[1:4]]
    mutual_upper = LINES_TO_BAGUA[main_lines[2:5]]
    mutual_lines = BAGUA_LINES[mutual_lower] + BAGUA_LINES[mutual_upper]

    changed_values = list(main_lines)
    moving_index = moving_line - 1
    changed_values[moving_index] = "0" if changed_values[moving_index] == "1" else "1"
    changed_lines = "".join(changed_values)
    changed_body_gua = LINES_TO_BAGUA[changed_lines[:3]]
    changed_use_gua = LINES_TO_BAGUA[changed_lines[3:]]

    body_element = ELEMENTS[body_gua]
    use_element = ELEMENTS[use_gua]
    relation_code, relation = five_element_relation(body_element, use_element)
    changed_relation_code, changed_relation = five_element_relation(
        ELEMENTS[changed_body_gua], ELEMENTS[changed_use_gua]
    )
    moving_original = main_lines[moving_index]

    return HexagramResult(
        casting_moment=build_casting_moment(cast_at),
        title=casting.title.strip(),
        body_name=casting.body_name.strip(),
        use_name=casting.use_name.strip(),
        body_count=body_count,
        use_count=use_count,
        total_count=total_count,
        body_modulo=body_count % 8,
        use_modulo=use_count % 8,
        moving_modulo=total_count % 6,
        body_gua=body_gua,
        use_gua=use_gua,
        body_number=BAGUA_NUMBER[body_gua],
        use_number=BAGUA_NUMBER[use_gua],
        body_element=body_element,
        use_element=use_element,
        main_hexagram=hexagram_name(use_gua, body_gua),
        main_lines_bottom_up=main_lines,
        mutual_lower_gua=mutual_lower,
        mutual_upper_gua=mutual_upper,
        mutual_hexagram=hexagram_name(mutual_upper, mutual_lower),
        mutual_lines_bottom_up=mutual_lines,
        moving_line=moving_line,
        moving_line_label=line_label(moving_line, moving_original),
        moving_original_type="陽" if moving_original == "1" else "陰",
        moving_changed_type="陰" if moving_original == "1" else "陽",
        moving_side="體方" if moving_line <= 3 else "用方",
        moving_layer="下卦" if moving_line <= 3 else "上卦",
        changed_hexagram=hexagram_name(changed_use_gua, changed_body_gua),
        changed_lines_bottom_up=changed_lines,
        changed_body_gua=changed_body_gua,
        changed_use_gua=changed_use_gua,
        body_transition=f"{body_gua}→{changed_body_gua}",
        use_transition=f"{use_gua}→{changed_use_gua}",
        relation_code=relation_code,
        relation=relation,
        changed_relation_code=changed_relation_code,
        changed_relation=changed_relation,
        line_table=_line_table(main_lines, changed_lines, moving_line),
    )


# Compatibility wrapper for old imports.  It performs casting only.
calculate_match_hexagram = calculate_casting


__all__ = [
    "BAGUA_BY_REMAINDER",
    "BAGUA_LINES",
    "BAGUA_NUMBER",
    "ELEMENTS",
    "HEXAGRAM_NAMES",
    "calculate_casting",
    "calculate_match_hexagram",
    "count_symbols",
    "five_element_relation",
    "hexagram_name",
    "line_label",
    "moving_line_from_count",
    "trigram_from_count",
]
