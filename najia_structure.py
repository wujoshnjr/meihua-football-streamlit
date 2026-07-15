from __future__ import annotations

from itertools import combinations
from typing import Any

from knowledge_loader import load_hexagrams
from meihua_engine import BAGUA_LINES, CONTROLS, ELEMENTS, GENERATES, line_label
from models import HexagramResult


STEMS = "甲乙丙丁戊己庚辛壬癸"
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
STEM_ELEMENTS = {
    "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
    "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水",
}
BRANCH_ELEMENTS = {
    "寅": "木", "卯": "木", "辰": "土", "巳": "火", "午": "火", "未": "土",
    "申": "金", "酉": "金", "戌": "土", "亥": "水", "子": "水", "丑": "土",
}
LUNAR_MONTH_BRANCHES = {
    1: "寅", 2: "卯", 3: "辰", 4: "巳", 5: "午", 6: "未",
    7: "申", 8: "酉", 9: "戌", 10: "亥", 11: "子", 12: "丑",
}
NAJIA_TABLE = {
    "乾": ("甲子", "甲寅", "甲辰", "壬午", "壬申", "壬戌"),
    "坤": ("乙未", "乙巳", "乙卯", "癸丑", "癸亥", "癸酉"),
    "震": ("庚子", "庚寅", "庚辰", "庚午", "庚申", "庚戌"),
    "巽": ("辛丑", "辛亥", "辛酉", "辛未", "辛巳", "辛卯"),
    "坎": ("戊寅", "戊辰", "戊午", "戊申", "戊戌", "戊子"),
    "離": ("己卯", "己丑", "己亥", "己酉", "己未", "己巳"),
    "艮": ("丙辰", "丙午", "丙申", "丙戌", "丙子", "丙寅"),
    "兌": ("丁巳", "丁卯", "丁丑", "丁亥", "丁酉", "丁未"),
}
PALACE_STAGES = (
    ("本宮六世", 6, 3),
    ("一世", 1, 4),
    ("二世", 2, 5),
    ("三世", 3, 6),
    ("四世", 4, 1),
    ("五世", 5, 2),
    ("遊魂", 4, 1),
    ("歸魂", 3, 6),
)
CLASH_PAIRS = {
    frozenset(pair) for pair in (("子", "午"), ("丑", "未"), ("寅", "申"),
                                 ("卯", "酉"), ("辰", "戌"), ("巳", "亥"))
}
COMBINATION_PAIRS = {
    frozenset(pair) for pair in (("子", "丑"), ("寅", "亥"), ("卯", "戌"),
                                 ("辰", "酉"), ("巳", "申"), ("午", "未"))
}
FOOTBALL_SIX_RELATIVE_ROLES = {
    "兄弟": "同伴協作、競爭、球權分流與正面對抗",
    "子孫": "進攻創造力、機會釋放與降低防守壓力",
    "妻財": "成果與進球訊號；是否兌現仍須看旺衰、空亡與沖合",
    "官鬼": "防守壓力、犯規、危險、阻力與失誤負擔",
    "父母": "戰術組織、傳導、保護、規則與供應系統",
}


def _flip(lines: str, positions: tuple[int, ...]) -> str:
    values = list(lines)
    for position in positions:
        values[position] = "0" if values[position] == "1" else "1"
    return "".join(values)


def _build_palace_index() -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for palace, trigram_lines in BAGUA_LINES.items():
        pure = trigram_lines + trigram_lines
        stage_lines = [
            pure,
            _flip(pure, (0,)),
            _flip(pure, (0, 1)),
            _flip(pure, (0, 1, 2)),
            _flip(pure, (0, 1, 2, 3)),
            _flip(pure, (0, 1, 2, 3, 4)),
            _flip(pure, (0, 1, 2, 4)),
            _flip(pure, (4,)),
        ]
        for lines, (stage, world, response) in zip(stage_lines, PALACE_STAGES, strict=True):
            if lines in index:
                raise ValueError(f"八宮索引重複：{lines}")
            index[lines] = {
                "palace": palace,
                "palace_element": ELEMENTS[palace],
                "stage": stage,
                "world_line": world,
                "response_line": response,
            }
    if len(index) != 64:
        raise ValueError("八宮世應索引必須完整包含六十四卦")
    return index


PALACE_BY_LINES = _build_palace_index()


def six_relative(reference_element: str, line_element: str) -> str:
    if reference_element == line_element:
        return "兄弟"
    if GENERATES[reference_element] == line_element:
        return "子孫"
    if CONTROLS[reference_element] == line_element:
        return "妻財"
    if CONTROLS[line_element] == reference_element:
        return "官鬼"
    if GENERATES[line_element] == reference_element:
        return "父母"
    raise ValueError(f"無法判定六親：{reference_element}/{line_element}")


def xun_void(day_ganzhi: str) -> dict[str, Any]:
    if len(day_ganzhi) != 2 or day_ganzhi[0] not in STEMS or day_ganzhi[1] not in BRANCHES:
        raise ValueError(f"無效日辰：{day_ganzhi}")
    cycle = [STEMS[index % 10] + BRANCHES[index % 12] for index in range(60)]
    try:
        day_index = cycle.index(day_ganzhi)
    except ValueError as exc:
        raise ValueError(f"日辰不在六十甲子：{day_ganzhi}") from exc
    xun_start = day_index - day_index % 10
    xun_start_ganzhi = cycle[xun_start]
    start_branch_index = BRANCHES.index(xun_start_ganzhi[1])
    void_branches = [
        BRANCHES[(start_branch_index + 10) % 12],
        BRANCHES[(start_branch_index + 11) % 12],
    ]
    return {
        "day_ganzhi": day_ganzhi,
        "xun_name": f"{xun_start_ganzhi}旬",
        "void_branches": void_branches,
        "void_text": "、".join(void_branches),
        "rule_note": "以六十甲子每十日一旬計算，該旬未配天干的兩個地支為旬空。",
    }


def branch_relation(first: str, second: str) -> str | None:
    pair = frozenset((first, second))
    if pair in CLASH_PAIRS:
        return "六沖"
    if pair in COMBINATION_PAIRS:
        return "六合"
    return None


def _interaction(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any] | None:
    relation = branch_relation(str(first["branch"]), str(second["branch"]))
    if relation is None:
        return None
    football_note = (
        "節奏與結構可能被沖開；是否形成進球仍須合看旺衰、空亡、動爻與卦線。"
        if relation == "六沖"
        else "兩爻有黏合與收束傾向；可能穩固防守，也可能形成配合，不可直接等同無球。"
    )
    return {
        "relation": relation,
        "first_line": int(first["position"]),
        "first_label": str(first["line_label"]),
        "first_branch": str(first["branch"]),
        "second_line": int(second["position"]),
        "second_label": str(second["line_label"]),
        "second_branch": str(second["branch"]),
        "pair": f"{first['branch']}{second['branch']}",
        "football_note": football_note,
    }


def _hexagram_najia(
    name: str,
    lines_bottom_up: str,
    day_element: str,
    void_branches: set[str],
    original_moving_line: int,
) -> dict[str, Any]:
    item = load_hexagrams()[name]
    lower = str(item["lower"])
    upper = str(item["upper"])
    addresses = NAJIA_TABLE[lower][:3] + NAJIA_TABLE[upper][3:]
    palace = PALACE_BY_LINES[lines_bottom_up]
    palace_element = str(palace["palace_element"])
    lines: list[dict[str, Any]] = []
    for position, (bit, gan_zhi) in enumerate(zip(lines_bottom_up, addresses, strict=True), 1):
        stem, branch = gan_zhi
        branch_element = BRANCH_ELEMENTS[branch]
        day_relative = six_relative(day_element, branch_element)
        palace_relative = six_relative(palace_element, branch_element)
        roles: list[str] = []
        if position == palace["world_line"]:
            roles.append("世")
        if position == palace["response_line"]:
            roles.append("應")
        is_void = branch in void_branches
        lines.append(
            {
                "position": position,
                "position_name": ("初爻", "二爻", "三爻", "四爻", "五爻", "上爻")[position - 1],
                "line_label": line_label(position, bit),
                "line_type": "陽" if bit == "1" else "陰",
                "trigram": lower if position <= 3 else upper,
                "layer": "下卦" if position <= 3 else "上卦",
                "gan_zhi": gan_zhi,
                "stem": stem,
                "stem_element": STEM_ELEMENTS[stem],
                "branch": branch,
                "branch_element": branch_element,
                "roles": roles,
                "is_world_line": "世" in roles,
                "is_response_line": "應" in roles,
                "is_original_moving_position": position == original_moving_line,
                "six_relative_by_day_stem": day_relative,
                "six_relative_by_palace": palace_relative,
                "football_role_by_day_stem": FOOTBALL_SIX_RELATIVE_ROLES[day_relative],
                "is_void": is_void,
                "void_status": "旬空／作用暫受限制" if is_void else "不空",
                "void_football_note": (
                    "此爻訊號先列為受限；是否填空與何時觸發須另看後續日、時，不自動視為永久無效。"
                    if is_void
                    else "此爻不受本日日旬空直接限制。"
                ),
            }
        )

    interactions = [
        found
        for first, second in combinations(lines, 2)
        if (found := _interaction(first, second)) is not None
    ]
    moving_interactions = [
        relation
        for relation in interactions
        if original_moving_line in {relation["first_line"], relation["second_line"]}
    ]
    world = lines[int(palace["world_line"]) - 1]
    response = lines[int(palace["response_line"]) - 1]
    world_response = _interaction(world, response)
    return {
        "name": name,
        "short_name": str(item["short_name"]),
        "unicode": str(item["unicode"]),
        "upper_trigram": upper,
        "lower_trigram": lower,
        "lines_bottom_up": lines_bottom_up,
        "palace": str(palace["palace"]),
        "palace_element": palace_element,
        "palace_stage": str(palace["stage"]),
        "world_line": int(palace["world_line"]),
        "world_line_label": str(world["line_label"]),
        "response_line": int(palace["response_line"]),
        "response_line_label": str(response["line_label"]),
        "lines": lines,
        "branch_interactions": interactions,
        "moving_line_interactions": moving_interactions,
        "world_response_interaction": world_response,
    }


def build_najia_analysis(result: HexagramResult) -> dict[str, Any]:
    day_ganzhi = result.casting_moment.day_ganzhi
    day_stem = result.casting_moment.day_stem
    day_branch = result.casting_moment.day_branch
    day_element = STEM_ELEMENTS[day_stem]
    void = xun_void(day_ganzhi)
    void_branches = set(void["void_branches"])
    month_branch = LUNAR_MONTH_BRANCHES[result.casting_moment.lunar_month]
    main = _hexagram_najia(
        result.main_hexagram,
        result.main_lines_bottom_up,
        day_element,
        void_branches,
        result.moving_line,
    )
    mutual = _hexagram_najia(
        result.mutual_hexagram,
        result.mutual_lines_bottom_up,
        day_element,
        void_branches,
        result.moving_line,
    )
    changed = _hexagram_najia(
        result.changed_hexagram,
        result.changed_lines_bottom_up,
        day_element,
        void_branches,
        result.moving_line,
    )
    return {
        "day_cycle": {
            "day_ganzhi": day_ganzhi,
            "day_stem": day_stem,
            "day_branch": day_branch,
            "day_stem_element": day_element,
            "lunar_month": result.casting_moment.lunar_month,
            "month_branch": month_branch,
            "month_element": BRANCH_ELEMENTS[month_branch],
        },
        "xun_void": void,
        "six_relatives_method": {
            "requested_primary": "依起卦日天干五行與各爻地支五行定六親",
            "traditional_reference": "另列依八宮卦宮五行定六親，避免與常見文王卦口徑混淆",
            "football_mapping_boundary": "妻財、子孫、官鬼等足球角色是本專案應用層，不是固定進球或比分公式。",
        },
        "main_hexagram": main,
        "mutual_hexagram": mutual,
        "changed_hexagram": changed,
        "workflow": [
            {"step": 1, "content": "確定日辰、月令", "purpose": "定旺衰與旬空"},
            {"step": 2, "content": "本卦、互卦、變卦納甲", "purpose": "為每一爻裝上天干地支"},
            {"step": 3, "content": "依八宮安世應", "purpose": "標示主體與客體位置"},
            {"step": 4, "content": "定六親", "purpose": "辨識成果、創造、壓力、組織與競爭訊號"},
            {"step": 5, "content": "查旬空", "purpose": "標示暫受限制的爻"},
            {"step": 6, "content": "查動爻及世應六沖六合", "purpose": "觀察節奏打開、黏合或收束的可能"},
            {"step": 7, "content": "合看動爻爻辭、小象、卦義與焦氏易林", "purpose": "提供完整原始資料，不自動指定比分"},
        ],
    }


__all__ = [
    "BRANCH_ELEMENTS",
    "COMBINATION_PAIRS",
    "CLASH_PAIRS",
    "LUNAR_MONTH_BRANCHES",
    "NAJIA_TABLE",
    "PALACE_BY_LINES",
    "STEM_ELEMENTS",
    "branch_relation",
    "build_najia_analysis",
    "six_relative",
    "xun_void",
]
