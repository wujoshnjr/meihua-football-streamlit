from __future__ import annotations

from datetime import datetime
from typing import Iterable

from qimen.calendar import build_calendar_context

from .constants import (
    BAGONG_SEQUENCE,
    BRANCH_ELEMENT,
    ELEMENT_CONTROLS,
    ELEMENT_GENERATES,
    HEXAGRAM_NAME_BY_TRIGRAMS,
    HEXAGRAM_PALACE,
    LIUCHONG_PAIRS,
    LIUHE_PAIRS,
    LINE_VALUE_LABEL,
    NAJIA,
    PALACE_ELEMENT,
    SIX_CLASH_HEXAGRAMS,
    SIX_HARMONY_HEXAGRAMS,
    SIX_SPIRITS,
    SIX_SPIRIT_START,
    trigram_from_lines,
)
from .models import LiuyaoChart, LiuyaoLine


LIUYAO_ENGINE_VERSION = "JARVIS_LIUYAO_NAJIA_V1"
LIUYAO_CAST_METHOD = "THREE_COIN_VALUES_OR_MANUAL_6789__SOURCE_GROUNDED"


def _relative(palace_element: str, line_element: str) -> str:
    if line_element == palace_element:
        return "兄弟"
    if ELEMENT_GENERATES[line_element] == palace_element:
        return "父母"
    if ELEMENT_GENERATES[palace_element] == line_element:
        return "子孫"
    if ELEMENT_CONTROLS[line_element] == palace_element:
        return "官鬼"
    if ELEMENT_CONTROLS[palace_element] == line_element:
        return "妻財"
    raise AssertionError("五行六親關係不完整")


def _is_pair(a: str, b: str, pairs: set[frozenset[str]]) -> bool:
    return frozenset((a, b)) in pairs


def _month_relation(month_branch: str, branch: str) -> str | None:
    if branch == month_branch:
        return "臨月建"
    if _is_pair(month_branch, branch, LIUCHONG_PAIRS):
        return "月破"
    if _is_pair(month_branch, branch, LIUHE_PAIRS):
        return "月合"
    return None


def _day_relation(day_branch: str, branch: str) -> str | None:
    if branch == day_branch:
        return "臨日辰"
    if _is_pair(day_branch, branch, LIUCHONG_PAIRS):
        return "日沖"
    if _is_pair(day_branch, branch, LIUHE_PAIRS):
        return "日合"
    return None


def _six_spirits(day_stem: str) -> tuple[str, ...]:
    start = SIX_SPIRIT_START[day_stem]
    index = SIX_SPIRITS.index(start)
    return tuple(SIX_SPIRITS[(index + offset) % 6] for offset in range(6))


def _trigrams_from_binary_lines(lines: tuple[int, ...]) -> tuple[str, str]:
    if len(lines) != 6:
        raise ValueError("六爻必須正好六條")
    lower = trigram_from_lines(tuple(lines[:3]))
    upper = trigram_from_lines(tuple(lines[3:]))
    return upper, lower


def _hexagram_name(lines: tuple[int, ...]) -> tuple[str, str, str]:
    upper, lower = _trigrams_from_binary_lines(lines)
    try:
        name = HEXAGRAM_NAME_BY_TRIGRAMS[(upper, lower)]
    except KeyError as exc:
        raise AssertionError(f"缺少卦名映射：{upper}/{lower}") from exc
    return name, upper, lower


def _najia_for_hexagram(upper: str, lower: str) -> tuple[tuple[str, str], ...]:
    lower_map = NAJIA[lower]
    upper_map = NAJIA[upper]
    lines: list[tuple[str, str]] = []
    for branch in lower_map["inner_branches"]:
        lines.append((str(lower_map["inner_stem"]), str(branch)))
    for branch in upper_map["outer_branches"]:
        lines.append((str(upper_map["outer_stem"]), str(branch)))
    return tuple(lines)


def _return_relation(original_branch: str, changed_branch: str) -> str:
    original = BRANCH_ELEMENT[original_branch]
    changed = BRANCH_ELEMENT[changed_branch]
    if changed == original:
        relation = "比和"
    elif ELEMENT_GENERATES[changed] == original:
        relation = "回頭生"
    elif ELEMENT_CONTROLS[changed] == original:
        relation = "回頭克"
    elif ELEMENT_GENERATES[original] == changed:
        relation = "原爻生變"
    elif ELEMENT_CONTROLS[original] == changed:
        relation = "原爻克變"
    else:
        raise AssertionError("五行關係不完整")

    if _is_pair(original_branch, changed_branch, LIUHE_PAIRS):
        relation += "＋化合"
    if _is_pair(original_branch, changed_branch, LIUCHONG_PAIRS):
        relation += "＋回頭沖"
    return relation


def _pure_palace_hidden_candidates(
    palace: str,
    present_relatives: set[str],
) -> dict[int, tuple[str, str, str]]:
    pure_name = BAGONG_SEQUENCE[palace][0]
    upper, lower = palace, palace
    if pure_name not in HEXAGRAM_PALACE:
        raise AssertionError(f"八宮本宮缺失：{pure_name}")
    najia = _najia_for_hexagram(upper, lower)
    palace_element = PALACE_ELEMENT[palace]
    result: dict[int, tuple[str, str, str]] = {}
    for index, (_stem, branch) in enumerate(najia, start=1):
        element = BRANCH_ELEMENT[branch]
        relative = _relative(palace_element, element)
        if relative not in present_relatives:
            result[index] = (relative, branch, element)
    return result


def validate_line_values(values: Iterable[int]) -> tuple[int, ...]:
    normalized = tuple(int(value) for value in values)
    if len(normalized) != 6:
        raise ValueError("六爻起卦必須提供六次結果，順序為初爻→上爻")
    invalid = [value for value in normalized if value not in LINE_VALUE_LABEL]
    if invalid:
        raise ValueError(f"六爻每爻只接受 6/7/8/9，收到：{invalid}")
    return normalized


def cast_liuyao(
    line_values: Iterable[int],
    event_at: datetime,
    timezone_name: str,
) -> LiuyaoChart:
    """Build one deterministic Wen-Wang-Gua / Najia Liuyao chart.

    line_values are ordered from the first cast (bottom line) to the sixth cast
    (top line). 6=old yin, 7=young yang, 8=young yin, 9=old yang.

    JARVIS deliberately stops at source-grounded structural facts here. It does
    not turn a spirit, relative, void, clash or harmony into an automatic final
    judgment.
    """

    values = validate_line_values(line_values)
    calendar = build_calendar_context(event_at, timezone_name)

    original_binary = tuple(1 if value in (7, 9) else 0 for value in values)
    changed_binary = tuple(
        (1 - original_binary[index]) if values[index] in (6, 9) else original_binary[index]
        for index in range(6)
    )
    original_name, original_upper, original_lower = _hexagram_name(original_binary)
    changed_name, changed_upper, changed_lower = _hexagram_name(changed_binary)

    palace, _palace_index, palace_stage, shi_line, ying_line = HEXAGRAM_PALACE[original_name]
    palace_element = PALACE_ELEMENT[palace]

    original_najia = _najia_for_hexagram(original_upper, original_lower)
    changed_najia = _najia_for_hexagram(changed_upper, changed_lower)
    spirits = _six_spirits(calendar.day_ganzhi[0])

    present_relatives = {
        _relative(palace_element, BRANCH_ELEMENT[branch])
        for _stem, branch in original_najia
    }
    hidden = _pure_palace_hidden_candidates(palace, present_relatives)

    lines: list[LiuyaoLine] = []
    moving_lines: list[int] = []
    for index, value in enumerate(values, start=1):
        kind, yin_yang, moving, changed_yin_yang = LINE_VALUE_LABEL[value]
        stem, branch = original_najia[index - 1]
        element = BRANCH_ELEMENT[branch]
        relative = _relative(palace_element, element)
        month_relation = _month_relation(calendar.month_ganzhi[1], branch)
        day_relation = _day_relation(calendar.day_ganzhi[1], branch)
        notes: list[str] = []
        if branch in calendar.day_void_branches:
            notes.append(f"旬空：{branch}")
        if month_relation == "月破":
            notes.append("月建相沖＝月破")
        if day_relation == "日沖":
            notes.append("日辰相沖；是否暗動／日破須結合旺衰，不在結構層自動下結論")

        changed_stem = changed_branch = changed_element = changed_relative = changed_relation = None
        if moving:
            moving_lines.append(index)
            changed_stem, changed_branch = changed_najia[index - 1]
            changed_element = BRANCH_ELEMENT[changed_branch]
            changed_relative = _relative(palace_element, changed_element)
            changed_relation = _return_relation(branch, changed_branch)

        hidden_relative = hidden_branch = hidden_element = None
        if index in hidden:
            hidden_relative, hidden_branch, hidden_element = hidden[index]
            notes.append(
                f"伏神候選：本宮純卦同位藏{hidden_relative}{hidden_branch}{hidden_element}"
            )

        lines.append(
            LiuyaoLine(
                position=index,
                raw_value=value,
                line_kind=kind,
                yin_yang=yin_yang,
                moving=moving,
                changed_yin_yang=changed_yin_yang,
                stem=stem,
                branch=branch,
                element=element,
                relative=relative,
                six_spirit=spirits[index - 1],
                is_shi=index == shi_line,
                is_ying=index == ying_line,
                is_void=branch in calendar.day_void_branches,
                month_relation=month_relation,
                day_relation=day_relation,
                month_break=month_relation == "月破",
                day_clash=day_relation == "日沖",
                changed_stem=changed_stem,
                changed_branch=changed_branch,
                changed_element=changed_element,
                changed_relative=changed_relative,
                changed_relation_to_original=changed_relation,
                hidden_relative=hidden_relative,
                hidden_branch=hidden_branch,
                hidden_element=hidden_element,
                notes=tuple(notes),
            )
        )

    source_boundary = (
        "納甲、八宮、世應、六親、六神、動變、旬空、月建／日辰直接關係屬 source-grounded deterministic layer。",
        "變爻六親固定依正卦卦宮五行，不依變卦自身卦宮重算。",
        "六神只作附合／象意層，不直接凌駕五行生克判吉凶。",
        "日沖靜爻不自動等同暗動；《增刪卜易》要求結合旺衰區分暗動與日破。",
        "伏神依本宮純卦同位補缺六親；是否有用仍須再審飛神、日月、旺衰與空破墓絕。",
    )
    warnings = (
        "此 V1 核心只建立可稽核的裝卦與直接關係，不自動選用神、不自動定吉凶、不自動應期。",
        "神煞、十二長生、進退神、三刑三合成局、卦身與專項占法會分層加入，不得未驗證就混入核心。",
        "若用於足球，世應／子鬼／主客的映射必須另作 project adaptation 或 classical battle mapping，不得偷換。",
    )

    return LiuyaoChart(
        schema_version=LIUYAO_ENGINE_VERSION,
        method_id=LIUYAO_CAST_METHOD,
        event_local_at=calendar.local_datetime,
        timezone_name=calendar.timezone_name,
        month_ganzhi=calendar.month_ganzhi,
        month_branch=calendar.month_ganzhi[1],
        day_ganzhi=calendar.day_ganzhi,
        day_stem=calendar.day_ganzhi[0],
        day_branch=calendar.day_ganzhi[1],
        day_xun=calendar.day_xun,
        void_branches=calendar.day_void_branches,
        original_hexagram=original_name,
        changed_hexagram=changed_name,
        original_upper_trigram=original_upper,
        original_lower_trigram=original_lower,
        changed_upper_trigram=changed_upper,
        changed_lower_trigram=changed_lower,
        palace=palace,
        palace_element=palace_element,
        palace_stage=palace_stage,
        shi_line=shi_line,
        ying_line=ying_line,
        moving_lines=tuple(moving_lines),
        original_is_six_clash=original_name in SIX_CLASH_HEXAGRAMS,
        original_is_six_harmony=original_name in SIX_HARMONY_HEXAGRAMS,
        changed_is_six_clash=changed_name in SIX_CLASH_HEXAGRAMS,
        changed_is_six_harmony=changed_name in SIX_HARMONY_HEXAGRAMS,
        six_spirit_start=spirits[0],
        lines=tuple(lines),
        source_boundary=source_boundary,
        warnings=warnings,
    )
