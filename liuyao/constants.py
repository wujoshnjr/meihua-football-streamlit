from __future__ import annotations

from meihua.engine import TRIGRAM_FROM_LINES, TRIGRAM_LINES

BRANCH_ELEMENT = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
    "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水",
}

ELEMENT_GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
ELEMENT_CONTROLS = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

TRIGRAM_ELEMENT = {
    "乾": "金", "兌": "金", "離": "火", "震": "木",
    "巽": "木", "坎": "水", "艮": "土", "坤": "土",
}

# 《增刪卜易》渾天甲子章 / 《卜筮正宗》納甲裝卦表。
# Each tuple is ordered from the lower line to the upper line of that trigram.
NAJIA = {
    "乾": {
        "inner_stem": "甲", "inner_branches": ("子", "寅", "辰"),
        "outer_stem": "壬", "outer_branches": ("午", "申", "戌"),
    },
    "震": {
        "inner_stem": "庚", "inner_branches": ("子", "寅", "辰"),
        "outer_stem": "庚", "outer_branches": ("午", "申", "戌"),
    },
    "坎": {
        "inner_stem": "戊", "inner_branches": ("寅", "辰", "午"),
        "outer_stem": "戊", "outer_branches": ("申", "戌", "子"),
    },
    "艮": {
        "inner_stem": "丙", "inner_branches": ("辰", "午", "申"),
        "outer_stem": "丙", "outer_branches": ("戌", "子", "寅"),
    },
    "巽": {
        "inner_stem": "辛", "inner_branches": ("丑", "亥", "酉"),
        "outer_stem": "辛", "outer_branches": ("未", "巳", "卯"),
    },
    "離": {
        "inner_stem": "己", "inner_branches": ("卯", "丑", "亥"),
        "outer_stem": "己", "outer_branches": ("酉", "未", "巳"),
    },
    "坤": {
        "inner_stem": "乙", "inner_branches": ("未", "巳", "卯"),
        "outer_stem": "癸", "outer_branches": ("丑", "亥", "酉"),
    },
    "兌": {
        "inner_stem": "丁", "inner_branches": ("巳", "卯", "丑"),
        "outer_stem": "丁", "outer_branches": ("亥", "酉", "未"),
    },
}

# King-Wen names keyed by (upper trigram, lower trigram).
HEXAGRAM_NAME_BY_TRIGRAMS = {
    ("乾", "乾"): "乾為天", ("坤", "坤"): "坤為地", ("坎", "震"): "水雷屯",
    ("艮", "坎"): "山水蒙", ("坎", "乾"): "水天需", ("乾", "坎"): "天水訟",
    ("坤", "坎"): "地水師", ("坎", "坤"): "水地比", ("巽", "乾"): "風天小畜",
    ("乾", "兌"): "天澤履", ("坤", "乾"): "地天泰", ("乾", "坤"): "天地否",
    ("乾", "離"): "天火同人", ("離", "乾"): "火天大有", ("坤", "艮"): "地山謙",
    ("震", "坤"): "雷地豫", ("兌", "震"): "澤雷隨", ("艮", "巽"): "山風蠱",
    ("坤", "兌"): "地澤臨", ("巽", "坤"): "風地觀", ("離", "震"): "火雷噬嗑",
    ("艮", "離"): "山火賁", ("艮", "坤"): "山地剝", ("坤", "震"): "地雷復",
    ("乾", "震"): "天雷無妄", ("艮", "乾"): "山天大畜", ("艮", "震"): "山雷頤",
    ("兌", "巽"): "澤風大過", ("坎", "坎"): "坎為水", ("離", "離"): "離為火",
    ("兌", "艮"): "澤山咸", ("震", "巽"): "雷風恆", ("乾", "艮"): "天山遯",
    ("震", "乾"): "雷天大壯", ("離", "坤"): "火地晉", ("坤", "離"): "地火明夷",
    ("巽", "離"): "風火家人", ("離", "兌"): "火澤睽", ("坎", "艮"): "水山蹇",
    ("震", "坎"): "雷水解", ("艮", "兌"): "山澤損", ("巽", "震"): "風雷益",
    ("兌", "乾"): "澤天夬", ("乾", "巽"): "天風姤", ("兌", "坤"): "澤地萃",
    ("坤", "巽"): "地風升", ("兌", "坎"): "澤水困", ("坎", "巽"): "水風井",
    ("兌", "離"): "澤火革", ("離", "巽"): "火風鼎", ("震", "震"): "震為雷",
    ("艮", "艮"): "艮為山", ("巽", "艮"): "風山漸", ("震", "兌"): "雷澤歸妹",
    ("震", "離"): "雷火豐", ("離", "艮"): "火山旅", ("巽", "巽"): "巽為風",
    ("兌", "兌"): "兌為澤", ("巽", "坎"): "風水渙", ("坎", "兌"): "水澤節",
    ("巽", "兌"): "風澤中孚", ("震", "艮"): "雷山小過", ("坎", "離"): "水火既濟",
    ("離", "坎"): "火水未濟",
}
TRIGRAMS_BY_HEXAGRAM_NAME = {name: pair for pair, name in HEXAGRAM_NAME_BY_TRIGRAMS.items()}

BAGONG_SEQUENCE = {
    "乾": ("乾為天", "天風姤", "天山遯", "天地否", "風地觀", "山地剝", "火地晉", "火天大有"),
    "震": ("震為雷", "雷地豫", "雷水解", "雷風恆", "地風升", "水風井", "澤風大過", "澤雷隨"),
    "坎": ("坎為水", "水澤節", "水雷屯", "水火既濟", "澤火革", "雷火豐", "地火明夷", "地水師"),
    "艮": ("艮為山", "山火賁", "山天大畜", "山澤損", "火澤睽", "天澤履", "風澤中孚", "風山漸"),
    "坤": ("坤為地", "地雷復", "地澤臨", "地天泰", "雷天大壯", "澤天夬", "水天需", "水地比"),
    "巽": ("巽為風", "風天小畜", "風火家人", "風雷益", "天雷無妄", "火雷噬嗑", "山雷頤", "山風蠱"),
    "離": ("離為火", "火山旅", "火風鼎", "火水未濟", "山水蒙", "風水渙", "天水訟", "天火同人"),
    "兌": ("兌為澤", "澤水困", "澤地萃", "澤山咸", "水山蹇", "地山謙", "雷山小過", "雷澤歸妹"),
}

PALACE_ELEMENT = {palace: TRIGRAM_ELEMENT[palace] for palace in BAGONG_SEQUENCE}
STAGE_BY_INDEX = ("本宮六世", "一世", "二世", "三世", "四世", "五世", "遊魂", "歸魂")
SHI_LINE_BY_INDEX = (6, 1, 2, 3, 4, 5, 4, 3)

HEXAGRAM_PALACE: dict[str, tuple[str, int, str, int, int]] = {}
for palace, names in BAGONG_SEQUENCE.items():
    for index, name in enumerate(names):
        shi = SHI_LINE_BY_INDEX[index]
        ying = shi + 3 if shi <= 3 else shi - 3
        HEXAGRAM_PALACE[name] = (palace, index, STAGE_BY_INDEX[index], shi, ying)

SIX_SPIRITS = ("青龍", "朱雀", "勾陳", "螣蛇", "白虎", "玄武")
SIX_SPIRIT_START = {
    "甲": "青龍", "乙": "青龍", "丙": "朱雀", "丁": "朱雀",
    "戊": "勾陳", "己": "螣蛇", "庚": "白虎", "辛": "白虎",
    "壬": "玄武", "癸": "玄武",
}

LIUHE_PAIRS = {
    frozenset(("子", "丑")), frozenset(("寅", "亥")), frozenset(("卯", "戌")),
    frozenset(("辰", "酉")), frozenset(("巳", "申")), frozenset(("午", "未")),
}
LIUCHONG_PAIRS = {
    frozenset(("子", "午")), frozenset(("丑", "未")), frozenset(("寅", "申")),
    frozenset(("卯", "酉")), frozenset(("辰", "戌")), frozenset(("巳", "亥")),
}

SIX_CLASH_HEXAGRAMS = {
    "乾為天", "坤為地", "坎為水", "離為火", "震為雷",
    "巽為風", "艮為山", "兌為澤", "天雷無妄", "雷天大壯",
}
SIX_HARMONY_HEXAGRAMS = {
    "天地否", "水澤節", "山火賁", "雷地豫",
    "火山旅", "地雷復", "地天泰", "澤水困",
}

TRINE_BY_BRANCH = {
    **{branch: ("申", "子", "辰", "水") for branch in ("申", "子", "辰")},
    **{branch: ("亥", "卯", "未", "木") for branch in ("亥", "卯", "未")},
    **{branch: ("寅", "午", "戌", "火") for branch in ("寅", "午", "戌")},
    **{branch: ("巳", "酉", "丑", "金") for branch in ("巳", "酉", "丑")},
}

LINE_VALUE_LABEL = {
    6: ("老陰", "陰", True, "陽"),
    7: ("少陽", "陽", False, "陽"),
    8: ("少陰", "陰", False, "陰"),
    9: ("老陽", "陽", True, "陰"),
}

def trigram_from_lines(lines: tuple[int, int, int]) -> str:
    return TRIGRAM_FROM_LINES[lines]


def lines_for_trigram(trigram: str) -> tuple[int, int, int]:
    return TRIGRAM_LINES[trigram]
