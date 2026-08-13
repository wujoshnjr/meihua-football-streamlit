from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from functools import lru_cache
from itertools import product
from typing import Any, TYPE_CHECKING

from .constants import (
    DOOR_ELEMENT,
    ELEMENT_CONTROLS,
    ELEMENT_GENERATES,
    NAMED_STEM_PAIRS,
    PALACES,
    STAR_ELEMENT,
    STEM_ELEMENT,
    VISIBLE_STEMS,
)
from .knowledge import load_knowledge
from .models import PalaceState, QimenBoard

if TYPE_CHECKING:
    from .protocol import MatchInput


RELATION_TYPES = {
    "stem_pair": "天地盤干",
    "star_door": "星門",
    "door_palace": "門宮",
    "star_palace": "星宮",
}


@dataclass(frozen=True)
class RelationReading:
    key: str
    relation_type: str
    relation_label: str
    first: str
    first_role: str
    first_element: str
    second: str
    second_role: str
    second_element: str
    element_relation: str
    summary: str
    classical_pattern: str | None
    classical_category: str | None
    authority: str
    source_id: str
    caution: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AuditCheck:
    id: str
    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class PrecastAudit:
    overall: str
    checks: tuple[AuditCheck, ...]
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class UseGodSummary:
    role: str
    original_stem: str
    visible_stem: str
    palace: int
    palace_name: str


@dataclass(frozen=True)
class PalaceGuide:
    palace: int
    palace_name: str
    stack: str
    structural_modifiers: tuple[str, ...]
    relations: tuple[RelationReading, ...]
    verification_questions: tuple[str, ...]


@dataclass(frozen=True)
class InterpretationGuide:
    mapping_version: str
    question: str
    focus_id: str
    focus_name: str
    locked_at: str | None
    cast_basis: str
    audit: PrecastAudit
    reading_order: tuple[str, ...]
    global_signals: tuple[str, ...]
    home_use_god: UseGodSummary
    away_use_god: UseGodSummary
    focus: dict[str, Any]
    palace_guides: tuple[PalaceGuide, ...]
    boundary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_interpretation_knowledge() -> dict[str, Any]:
    return load_knowledge()["files"]["interpretation.json"]


def focus_topics() -> tuple[dict[str, Any], ...]:
    return tuple(load_interpretation_knowledge()["focus_topics"])


def focus_topic(focus_id: str) -> dict[str, Any]:
    for item in focus_topics():
        if item["id"] == focus_id:
            return item
    raise ValueError(f"未知解盤焦點：{focus_id}")


def interpretation_stats() -> dict[str, Any]:
    contract = load_interpretation_knowledge()["relation_contract"]
    generated = all_relation_readings()
    counts = {
        relation_type: sum(item.relation_type == relation_type for item in generated)
        for relation_type in RELATION_TYPES
    }
    return {
        "mapping_version": load_interpretation_knowledge()["mapping_version"],
        "precast_checks": len(load_interpretation_knowledge()["precast_checklist"]),
        "reading_layers": len(load_interpretation_knowledge()["reading_layers"]),
        "focus_topics": len(focus_topics()),
        "total_relations": len(generated),
        "relation_counts": counts,
        "claim_boundary": contract["claim_boundary"],
    }


@lru_cache(maxsize=1)
def all_relation_readings() -> tuple[RelationReading, ...]:
    relations: list[RelationReading] = []
    relations.extend(
        build_relation("stem_pair", heaven, earth)
        for heaven, earth in product(VISIBLE_STEMS, repeat=2)
    )
    relations.extend(
        build_relation("star_door", star, door)
        for star, door in product(STAR_ELEMENT, DOOR_ELEMENT)
    )
    relations.extend(
        build_relation("door_palace", door, palace_number)
        for door, palace_number in product(DOOR_ELEMENT, PALACES)
    )
    relations.extend(
        build_relation("star_palace", star, palace_number)
        for star, palace_number in product(STAR_ELEMENT, PALACES)
    )
    return tuple(relations)


def search_relation_readings(
    query: str = "",
    *,
    relation_type: str | None = None,
) -> list[RelationReading]:
    if relation_type and relation_type not in RELATION_TYPES:
        raise ValueError(f"未知關係類型：{relation_type}")
    normalized = query.strip().casefold()
    selected = [
        item for item in all_relation_readings()
        if relation_type is None or item.relation_type == relation_type
    ]
    if not normalized:
        return selected
    return [
        item for item in selected
        if normalized in json.dumps(item.to_dict(), ensure_ascii=False).casefold()
    ]


def build_relation(relation_type: str, first: str, second: str | int) -> RelationReading:
    if relation_type not in RELATION_TYPES:
        raise ValueError(f"未知關係類型：{relation_type}")

    if relation_type == "stem_pair":
        first_name = _require_key(first, STEM_ELEMENT, "天盤干")
        second_name = _require_key(str(second), STEM_ELEMENT, "地盤干")
        first_role, second_role = "天盤觸發", "地盤底層"
        first_element, second_element = STEM_ELEMENT[first_name], STEM_ELEMENT[second_name]
        classical = NAMED_STEM_PAIRS.get((first_name, second_name))
        source_id = "qimen-daquan-ten-stems"
        authority = "古籍固定格名" if classical else "古籍十干合參框架＋五行組合推導"
        caution = (
            "固定格名仍須合看門、星、宮、旺衰、空墓迫制；不可單獨判結果。"
            if classical
            else "此摘要是完整矩陣的五行推導，不是杜撰的古訣名稱。"
        )
    elif relation_type == "star_door":
        first_name = _require_key(first, STAR_ELEMENT, "九星")
        second_name = _require_key(str(second), DOOR_ELEMENT, "八門")
        first_role, second_role = "九星能力／中段機制", "八門行動／出口"
        first_element, second_element = STAR_ELEMENT[first_name], DOOR_ELEMENT[second_name]
        classical = None
        source_id = "qimen-daquan-star-door"
        authority = "古籍有逐組合參傳統＋本站五行組合推導"
        caution = "本站未把生成摘要冒充古籍逐句斷例；仍須加入所在宮、旺衰與題目。"
    elif relation_type == "door_palace":
        first_name = _require_key(first, DOOR_ELEMENT, "八門")
        palace_number = _require_palace(second)
        second_name = PALACES[palace_number]["name"]
        first_role, second_role = "八門功能", "九宮環境"
        first_element, second_element = DOOR_ELEMENT[first_name], PALACES[palace_number]["element"]
        relation = _element_relation(first_element, second_element, first_role, second_role)
        if relation[0] == "前剋後":
            classical = ("門迫", "宮門關係")
        elif relation[0] == "後剋前":
            classical = ("宮迫", "宮門關係")
        else:
            classical = None
        source_id = "qimen-daquan-door-pressure"
        authority = "古籍門宮生剋概念＋完整矩陣推導"
        caution = "吉門受迫未必能順用，凶門得生也不等於必凶；須依任務與旺衰判讀。"
    else:
        first_name = _require_key(first, STAR_ELEMENT, "九星")
        palace_number = _require_palace(second)
        second_name = PALACES[palace_number]["name"]
        first_role, second_role = "九星能力", "九宮環境"
        first_element, second_element = STAR_ELEMENT[first_name], PALACES[palace_number]["element"]
        classical = None
        source_id = "dunjia-yanyi"
        authority = "古籍九星旺衰框架＋五行組合推導"
        caution = "星的基礎吉凶會受宮、門、時令及結構狀態改變，不作單符號結論。"

    relation_code, relation_text = _element_relation(
        first_element,
        second_element,
        first_role,
        second_role,
    )
    classical_pattern = classical[0] if classical else None
    classical_category = classical[1] if classical else None
    summary = relation_text
    if classical_pattern:
        summary = f"{classical_pattern}（{classical_category}）；{relation_text}"

    return RelationReading(
        key=f"{relation_type}:{first_name}:{second_name}",
        relation_type=relation_type,
        relation_label=RELATION_TYPES[relation_type],
        first=first_name,
        first_role=first_role,
        first_element=first_element,
        second=second_name,
        second_role=second_role,
        second_element=second_element,
        element_relation=relation_code,
        summary=summary,
        classical_pattern=classical_pattern,
        classical_category=classical_category,
        authority=authority,
        source_id=source_id,
        caution=caution,
    )


def relations_for_palace(state: PalaceState) -> tuple[RelationReading, ...]:
    relations: list[RelationReading] = []
    earth_stems = (state.earth_stem, *state.earth_hidden_stems)
    for heaven, earth in product(state.heaven_stems, earth_stems):
        relations.append(build_relation("stem_pair", heaven, earth))
    if state.door:
        relations.append(build_relation("door_palace", state.door, state.number))
    for star in state.stars:
        relations.append(build_relation("star_palace", star, state.number))
        if state.door:
            relations.append(build_relation("star_door", star, state.door))
    unique = {item.key: item for item in relations}
    return tuple(unique.values())


def build_precast_audit(
    *,
    board: QimenBoard,
    question: str,
    focus_id: str,
    match: MatchInput | None = None,
    locked_before_cast: bool = True,
) -> PrecastAudit:
    focus = focus_topic(focus_id)
    checks: list[AuditCheck] = []

    normalized_question = question.strip()
    if not normalized_question:
        checks.append(AuditCheck("single_question", "一事一問", "FAIL", "固定問題空白。"))
    elif len(normalized_question) < 12:
        checks.append(AuditCheck("single_question", "一事一問", "WARN", "問題已保存，但過短，建議加入範圍與可觀察對象。"))
    else:
        checks.append(AuditCheck("single_question", "一事一問", "PASS", normalized_question))

    checks.append(AuditCheck(
        "cast_basis",
        "起局時點",
        "PASS",
        f"固定採官方事件時：{board.calendar.local_datetime.isoformat()}。",
    ))
    timezone_ok = bool(board.calendar.timezone_name and board.calendar.local_datetime.tzinfo)
    checks.append(AuditCheck(
        "location_timezone",
        "地點與 IANA 時區",
        "PASS" if timezone_ok else "FAIL",
        f"時區：{board.calendar.timezone_name or '缺少'}；事件偏移：{board.calendar.local_datetime.utcoffset()}。",
    ))
    method = board.method
    method_ok = method.plate_method == "轉盤" and method.ju_method == "拆補法"
    checks.append(AuditCheck(
        "method_lock",
        "方法版本鎖定",
        "PASS" if method_ok else "FAIL",
        f"{method.family}／{method.plate_method}／{method.ju_method}／{method.version}。",
    ))
    checks.append(AuditCheck(
        "role_lock",
        "主客角色鎖定",
        "PASS",
        "主隊＝日干；客隊＝時干；甲＝值符宮。",
    ))
    checks.append(AuditCheck(
        "focus_lock",
        "焦點用神鎖定",
        "PASS",
        f"{focus['name']}（{focus_id}）；焦點只作第二層鏡頭。",
    ))

    match_errors = match.validate() if match else []
    scope_ok = not any("勝負口徑" in error for error in match_errors)
    checks.append(AuditCheck(
        "scope_lock",
        "賽果口徑鎖定",
        "PASS" if scope_ok else "FAIL",
        match.scope if match else "未提供 MatchInput；盤面本身仍可讀，但無賽果口徑稽核。",
    ))
    if not match:
        evidence_status, evidence_detail = "WARN", "未提供賽前證據物件。"
    elif match_errors:
        evidence_status, evidence_detail = "FAIL", "；".join(match_errors)
    elif not match.evidence:
        evidence_status, evidence_detail = "WARN", "目前沒有外部證據；可起局，但不能驗證陣容、傷停與情境。"
    else:
        evidence_status, evidence_detail = "PASS", f"{len(match.evidence)} 筆來源通過時間與對稱更新規約。"
    checks.append(AuditCheck("evidence_cutoff", "資料截止點", evidence_status, evidence_detail))
    checks.append(AuditCheck(
        "counterevidence",
        "反證預先登記",
        "PASS" if focus.get("counterevidence") else "FAIL",
        focus.get("counterevidence", "缺少反證。"),
    ))
    checks.append(AuditCheck(
        "lock_timestamp",
        "鎖定時間與指紋",
        "PASS" if locked_before_cast else "WARN",
        "問題與焦點已在建立盤面時鎖定。" if locked_before_cast else "此指南在盤後建立，僅供探索，不計入事前命中。",
    ))

    blockers = tuple(check.detail for check in checks if check.status == "FAIL")
    overall = "FAIL" if blockers else "WARN" if any(check.status == "WARN" for check in checks) else "PASS"
    return PrecastAudit(overall=overall, checks=tuple(checks), blockers=blockers)


def build_interpretation_guide(
    board: QimenBoard,
    *,
    question: str,
    focus_id: str = "whole_match",
    match: MatchInput | None = None,
    locked_at: datetime | None = None,
    locked_before_cast: bool = True,
) -> InterpretationGuide:
    focus = focus_topic(focus_id)
    home = _use_god_summary("主隊／日干", board.calendar.day_ganzhi[0], board)
    away = _use_god_summary("客隊／時干", board.calendar.hour_ganzhi[0], board)
    audit = build_precast_audit(
        board=board,
        question=question,
        focus_id=focus_id,
        match=match,
        locked_before_cast=locked_before_cast,
    )
    reading_order = tuple(
        f"{item['name']}：{item['instruction']}"
        for item in load_interpretation_knowledge()["reading_layers"]
    )
    patterns = "、".join(pattern.name for pattern in board.patterns) or "目前版本未命中自動格局"
    global_signals = (
        f"局盤：{board.ju_label}／{board.yuan}／旬首{board.hour_xun}（{board.xun_head_instrument}）",
        f"值符：{board.chief_star}落{board.chief_star_palace}宮；值使：{board.chief_door}落{board.chief_door_palace}宮",
        f"旬空：{'、'.join(board.void_branches)}；驛馬：{board.horse_branch}／{board.horse_palace}宮",
        f"全盤格局：{patterns}",
        f"足球焦點：{focus['name']}；先驗證：{focus['observable']}",
        f"預先反證：{focus['counterevidence']}",
    )
    palace_guides = tuple(
        _palace_guide(board, board.palaces[number], focus)
        for number in (4, 9, 2, 3, 5, 7, 8, 1, 6)
    )
    return InterpretationGuide(
        mapping_version=load_interpretation_knowledge()["mapping_version"],
        question=question.strip(),
        focus_id=focus_id,
        focus_name=focus["name"],
        locked_at=locked_at.isoformat() if locked_at else None,
        cast_basis="官方開賽事件時／事件所在地 IANA 民用時",
        audit=audit,
        reading_order=reading_order,
        global_signals=global_signals,
        home_use_god=home,
        away_use_god=away,
        focus=dict(focus),
        palace_guides=palace_guides,
        boundary=(
            "本指南完整覆蓋目前 schema 的關係槽位並提供可反證閱讀流程；"
            "它不宣稱窮盡所有奇門流派，也不輸出勝負、比分、進球數、機率、醫療或投注結論。"
        ),
    )


def _palace_guide(board: QimenBoard, state: PalaceState, focus: dict[str, Any]) -> PalaceGuide:
    flags: list[str] = []
    if state.is_void:
        flags.append("旬空")
    if state.is_horse:
        flags.append("驛馬")
    flags.extend(
        pattern.name for pattern in board.patterns
        if pattern.palace in {None, state.number}
    )
    stack = (
        f"{state.name}（{state.element}）｜門 {state.door or '—'}｜"
        f"星 {'・'.join(state.stars) or '—'}｜神 {state.deity or '—'}｜"
        f"天盤 {'・'.join(state.heaven_stems) or '—'}｜地盤 {state.earth_stem}"
    )
    return PalaceGuide(
        palace=state.number,
        palace_name=state.name,
        stack=stack,
        structural_modifiers=tuple(dict.fromkeys(flags)),
        relations=relations_for_palace(state),
        verification_questions=(
            f"此宮的環境、能力與行動通道，如何對應「{focus['name']}」而不越過固定用神？",
            f"可觀察資料是否出現：{focus['observable']}",
            f"是否已出現反證：{focus['counterevidence']}",
        ),
    )


def _use_god_summary(role: str, stem: str, board: QimenBoard) -> UseGodSummary:
    if stem == "甲":
        palace = board.chief_star_palace
        visible_stem = board.xun_head_instrument
    else:
        palace = next(
            (number for number, state in board.palaces.items() if stem in state.heaven_stems),
            None,
        )
        if palace is None:
            raise ValueError(f"天盤找不到用神：{stem}")
        visible_stem = stem
    return UseGodSummary(
        role=role,
        original_stem=stem,
        visible_stem=visible_stem,
        palace=palace,
        palace_name=board.palaces[palace].name,
    )


def _element_relation(
    first_element: str,
    second_element: str,
    first_role: str,
    second_role: str,
) -> tuple[str, str]:
    if first_element == second_element:
        return "比和", f"{first_role}與{second_role}同氣，訊號容易重複或放大，也要防止功能單一化。"
    if ELEMENT_GENERATES[first_element] == second_element:
        return "前生後", f"{first_role}生{second_role}：前層投入並支援後層，同時存在耗洩。"
    if ELEMENT_GENERATES[second_element] == first_element:
        return "後生前", f"{second_role}生{first_role}：前層有根與支援，後層承擔輸出。"
    if ELEMENT_CONTROLS[first_element] == second_element:
        return "前剋後", f"{first_role}剋{second_role}：前層主動限制後層，功能可能以壓制方式發用。"
    return "後剋前", f"{second_role}剋{first_role}：前層受環境或底層限制，作用可能延遲、變形或費力。"


def _require_key(value: str, mapping: dict[str, str], label: str) -> str:
    if value not in mapping:
        raise ValueError(f"未知{label}：{value}")
    return value


def _require_palace(value: str | int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"未知九宮：{value}") from exc
    if number not in PALACES:
        raise ValueError(f"宮位必須為 1–9：{number}")
    return number
