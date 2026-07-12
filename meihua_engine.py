from __future__ import annotations

import re
from typing import Iterable

from knowledge_loader import load_hexagrams
from models import HexagramResult, MatchInput


BAGUA_BY_REMAINDER = {1: "乾", 2: "兌", 3: "離", 4: "震", 5: "巽", 6: "坎", 7: "艮", 0: "坤"}
BAGUA_NUMBER = {"乾": 1, "兌": 2, "離": 3, "震": 4, "巽": 5, "坎": 6, "艮": 7, "坤": 8}
# 自下而上：初爻 → 三爻
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

# 一個連續的外文姓名/單字 token 算 1；連字號或撇號內部不中斷。
_LATIN_TOKEN = r"[A-Za-zÀ-ÖØ-öø-ÿĀ-ž]+(?:[-'’][A-Za-zÀ-ÖØ-öø-ÿĀ-ž]+)*"
_CJK_CHAR = r"[\u3400-\u4DBF\u4E00-\u9FFF]"
_NUMBER_TOKEN = r"\d+"
COUNT_PATTERN = re.compile(f"{_CJK_CHAR}|{_LATIN_TOKEN}|{_NUMBER_TOKEN}")


def count_symbols(text: str) -> int:
    """依本系統規則計算起卦字數，標點與空格不計。"""
    return len(COUNT_PATTERN.findall(text or ""))


def trigram_from_count(count: int) -> str:
    if count <= 0:
        raise ValueError("起卦字數必須大於 0")
    return BAGUA_BY_REMAINDER[count % 8]


def moving_line_from_count(total_count: int) -> int:
    if total_count <= 0:
        raise ValueError("完整段落字數必須大於 0")
    remainder = total_count % 6
    return 6 if remainder == 0 else remainder


def hexagram_name(upper: str, lower: str) -> str:
    try:
        return HEXAGRAM_NAMES[(upper, lower)]
    except KeyError as exc:
        raise ValueError(f"無法辨識上下卦：{upper}/{lower}") from exc


def five_element_relation(body_element: str, use_element: str) -> tuple[str, str, str]:
    if body_element == use_element:
        return (
            "equal",
            "比和：體用五行相同",
            "雙方底層能量接近，勝負不能只靠體用判定，必須由本卦、互卦、動爻與變卦決定破口。",
        )
    if GENERATES[body_element] == use_element:
        return (
            "body_generates_use",
            "體生用：體方能量流向用方",
            "體方可能掌握主動卻同時消耗自身，並餵大用方的反擊或完成點；用方進球不可機械壓低。",
        )
    if GENERATES[use_element] == body_element:
        return (
            "use_generates_body",
            "用生體：用方能量回流體方",
            "體方較容易獲得助力、場面與機會轉化；仍須防用方本身卦象帶來的反擊。",
        )
    if CONTROLS[body_element] == use_element:
        return (
            "body_controls_use",
            "體剋用：體方對用方形成制約",
            "體方較能限制用方的主要進攻通道，但剋制會耗力，若變卦反轉仍可能被追平。",
        )
    if CONTROLS[use_element] == body_element:
        return (
            "use_controls_body",
            "用剋體：用方對體方形成壓制",
            "體方容易受阻、失去效率或被迫改變節奏；除非互卦或變卦出現明顯解局。",
        )
    return "unknown", "體用關係未識別", "需以本互變與動爻為主。"


def _unique(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        item = str(item).strip()
        if item and item not in seen:
            seen.add(item)
            output.append(item)
    return output


def calculate_match_hexagram(match: MatchInput) -> HexagramResult:
    body_count = count_symbols(match.body_text)
    use_count = count_symbols(match.use_text)
    total_count = count_symbols(match.full_text)
    if not all([body_count, use_count, total_count]):
        raise ValueError("體方段落、用方段落與完整段落都必須含有可計數文字")

    body_gua = trigram_from_count(body_count)
    use_gua = trigram_from_count(use_count)
    moving_line = moving_line_from_count(total_count)

    # 六爻由下而上：體卦在下，用卦在上。
    six_lines = BAGUA_LINES[body_gua] + BAGUA_LINES[use_gua]
    mutual_lower = LINES_TO_BAGUA[six_lines[1:4]]
    mutual_upper = LINES_TO_BAGUA[six_lines[2:5]]

    changed_lines = list(six_lines)
    moving_index = moving_line - 1
    changed_lines[moving_index] = "0" if changed_lines[moving_index] == "1" else "1"
    changed_body_gua = LINES_TO_BAGUA["".join(changed_lines[:3])]
    changed_use_gua = LINES_TO_BAGUA["".join(changed_lines[3:])]

    main_hexagram = hexagram_name(use_gua, body_gua)
    mutual_hexagram = hexagram_name(mutual_upper, mutual_lower)
    changed_hexagram = hexagram_name(changed_use_gua, changed_body_gua)

    body_element = ELEMENTS[body_gua]
    use_element = ELEMENTS[use_gua]
    relation_code, relation, relation_detail = five_element_relation(body_element, use_element)
    changed_body_element = ELEMENTS[changed_body_gua]
    changed_use_element = ELEMENTS[changed_use_gua]
    changed_relation_code, changed_relation, changed_relation_detail = five_element_relation(
        changed_body_element,
        changed_use_element,
    )

    moving_side = "體方" if moving_line <= 3 else "用方"
    moving_layer = "下卦" if moving_line <= 3 else "上卦"
    if moving_side == "體方":
        moving_detail = (
            f"第{moving_line}爻位於下卦，變動首先落在體方。"
            f"體方由{body_gua}轉{changed_body_gua}，要判斷其主動、失誤、換人或節奏轉折。"
        )
    else:
        moving_detail = (
            f"第{moving_line}爻位於上卦，變動首先落在用方。"
            f"用方由{use_gua}轉{changed_use_gua}，要判斷其防守承壓、反擊爆發或後段轉勢。"
        )

    hexagrams = load_hexagrams()
    main_tags = hexagrams.get(main_hexagram, {}).get("tags", [])
    mutual_tags = hexagrams.get(mutual_hexagram, {}).get("tags", [])
    changed_tags = hexagrams.get(changed_hexagram, {}).get("tags", [])
    structural_tags = _unique(
        [
            f"體卦:{body_gua}", f"用卦:{use_gua}", f"體五行:{body_element}", f"用五行:{use_element}",
            f"體用:{relation_code}", f"本卦:{main_hexagram}", f"互卦:{mutual_hexagram}",
            f"動爻:{moving_line}", f"動方:{moving_side}", f"變卦:{changed_hexagram}",
            f"體轉:{body_gua}->{changed_body_gua}", f"用轉:{use_gua}->{changed_use_gua}",
        ]
        + [f"本象:{tag}" for tag in main_tags]
        + [f"互象:{tag}" for tag in mutual_tags]
        + [f"變象:{tag}" for tag in changed_tags]
    )

    return HexagramResult(
        match_name=match.match_name.strip(),
        body_team=match.body_team.strip(),
        use_team=match.use_team.strip(),
        body_count=body_count,
        use_count=use_count,
        total_count=total_count,
        body_gua=body_gua,
        use_gua=use_gua,
        body_number=BAGUA_NUMBER[body_gua],
        use_number=BAGUA_NUMBER[use_gua],
        body_element=body_element,
        use_element=use_element,
        main_hexagram=main_hexagram,
        mutual_hexagram=mutual_hexagram,
        moving_line=moving_line,
        moving_side=moving_side,
        moving_layer=moving_layer,
        changed_hexagram=changed_hexagram,
        changed_body_gua=changed_body_gua,
        changed_use_gua=changed_use_gua,
        body_transition=f"{body_gua}->{changed_body_gua}",
        use_transition=f"{use_gua}->{changed_use_gua}",
        relation_code=relation_code,
        relation=relation,
        relation_detail=relation_detail,
        moving_detail=moving_detail,
        structural_tags=structural_tags,
        changed_body_number=BAGUA_NUMBER[changed_body_gua],
        changed_use_number=BAGUA_NUMBER[changed_use_gua],
        changed_body_element=changed_body_element,
        changed_use_element=changed_use_element,
        changed_relation_code=changed_relation_code,
        changed_relation=changed_relation,
        changed_relation_detail=changed_relation_detail,
    )
