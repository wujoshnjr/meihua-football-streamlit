from __future__ import annotations

from typing import Any

from .constants import BRANCH_ELEMENT, ELEMENT_CONTROLS, ELEMENT_GENERATES
from .models import LiuyaoChart, LiuyaoQuestionRole, LiuyaoReview


LIUYAO_REVIEW_VERSION = "JARVIS_LIUYAO_SOURCE_REVIEW_V1"

QUESTION_ROLE_CATALOG: dict[str, dict[str, Any]] = {
    "SELF": {
        "primary_use": "世爻",
        "secondary_uses": (),
        "authority": "CLASSICAL_SHI_AS_SELF",
        "rationale": ("世為己、應為人；本人自身狀態先看世爻。",),
    },
    "OTHER_PERSON": {
        "primary_use": "應爻",
        "secondary_uses": (),
        "authority": "CLASSICAL_YING_AS_OTHER",
        "rationale": ("世為己、應為人；純問對方而無更具體六親身份時可先審應爻。",),
    },
    "WEALTH": {
        "primary_use": "妻財",
        "secondary_uses": ("世爻",),
        "authority": "CLASSICAL_SIX_RELATIVE_CATEGORY",
        "rationale": ("財帛、貨物等傳統以妻財為用；仍須合看世爻與日月動變。",),
    },
    "CAREER_OFFICE": {
        "primary_use": "官鬼",
        "secondary_uses": ("世爻", "父母"),
        "authority": "CLASSICAL_SIX_RELATIVE_CATEGORY",
        "rationale": ("功名官職傳統以官鬼為核心；文書印信等另參父母。",),
    },
    "DOCUMENT_CONTRACT": {
        "primary_use": "父母",
        "secondary_uses": ("世爻",),
        "authority": "CLASSICAL_SIX_RELATIVE_CATEGORY",
        "rationale": ("文書、契約、房舍、舟車等多歸父母類；具體題型仍須再細分。",),
    },
    "CHILDREN_MEDICINE_RELIEF": {
        "primary_use": "子孫",
        "secondary_uses": ("世爻",),
        "authority": "CLASSICAL_SIX_RELATIVE_CATEGORY",
        "rationale": ("子女、醫藥、解憂避禍等傳統常取子孫；不得跨題型機械套用。",),
    },
    "SIBLINGS_PEERS": {
        "primary_use": "兄弟",
        "secondary_uses": ("世爻",),
        "authority": "CLASSICAL_SIX_RELATIVE_CATEGORY",
        "rationale": ("兄弟、同輩、朋友等可取兄弟；財占時兄弟又可能成為阻財因素。",),
    },
}


def question_role(category: str) -> LiuyaoQuestionRole:
    normalized = category.strip().upper()
    if normalized == "FOOTBALL_MATCH":
        return LiuyaoQuestionRole(
            schema_version=LIUYAO_REVIEW_VERSION,
            status="PROJECT_ADAPTATION_REQUIRED__NO_SINGLE_CLASSICAL_FOOTBALL_USE_GOD",
            question_category=normalized,
            primary_use=None,
            secondary_uses=("世爻", "應爻", "子孫", "官鬼"),
            rationale=(
                "古籍有征戰占：官鬼可代表敵、子孫可代表我軍，另有世應強弱之法。",
                "現代足球不是古代戰陣；世應、子鬼、主客隊之間如何映射必須作候選 protocol 比較。",
                "JARVIS 不在核心排卦時自動指定主隊/客隊用神，避免把 project adaptation 冒充古法。",
            ),
            authority="CLASSICAL_BATTLE_ANALOGY__FOOTBALL_MAPPING_NOT_SOURCE_LOCKED",
            football_adaptation={
                "candidate_protocols": [
                    {
                        "id": "L-F1_SHI_YING",
                        "home": "世爻",
                        "away": "應爻",
                        "authority": "PROJECT_ADAPTATION_FROM_CLASSICAL_SELF_OTHER",
                    },
                    {
                        "id": "L-F2_ZISUN_GUANGUI",
                        "home": "子孫",
                        "away": "官鬼",
                        "authority": "PROJECT_ADAPTATION_FROM_HUOZHULIN_BATTLE_LENS",
                    },
                ],
                "rule": "候選 protocol 必須按同一批比賽平行比較；不得逐場挑最像賽果的一套。",
            },
        )

    row = QUESTION_ROLE_CATALOG.get(normalized)
    if row is None:
        return LiuyaoQuestionRole(
            schema_version=LIUYAO_REVIEW_VERSION,
            status="QUESTION_CATEGORY_UNMAPPED__CHATGPT_MUST_SELECT_FROM_SOURCE_RULES",
            question_category=normalized or "GENERAL",
            primary_use=None,
            rationale=(
                "六爻用神依所問之事而定；題目未落入已 source-reviewed 類別時不可由關鍵字硬猜。",
            ),
            authority="SOURCE_AWARE_UNMAPPED",
        )

    return LiuyaoQuestionRole(
        schema_version=LIUYAO_REVIEW_VERSION,
        status="SOURCE_CATEGORY_MAPPING_READY",
        question_category=normalized,
        primary_use=row["primary_use"],
        secondary_uses=tuple(row["secondary_uses"]),
        rationale=tuple(row["rationale"]),
        authority=row["authority"],
    )


def _element_relation(actor: str, target: str) -> str:
    if actor == target:
        return "比和"
    if ELEMENT_GENERATES[actor] == target:
        return "生爻"
    if ELEMENT_CONTROLS[actor] == target:
        return "克爻"
    if ELEMENT_GENERATES[target] == actor:
        return "爻生"
    if ELEMENT_CONTROLS[target] == actor:
        return "爻克"
    raise AssertionError("五行關係不完整")


def _source_enemy_rival_elements(use_element: str) -> dict[str, str]:
    source = next(element for element, target in ELEMENT_GENERATES.items() if target == use_element)
    enemy = next(element for element, target in ELEMENT_CONTROLS.items() if target == use_element)
    rival = next(
        element
        for element in ELEMENT_GENERATES
        if ELEMENT_CONTROLS[element] == source and ELEMENT_GENERATES[element] == enemy
    )
    return {"用神五行": use_element, "元神五行": source, "忌神五行": enemy, "仇神五行": rival}


def _line_role_matches(chart: LiuyaoChart, element: str) -> list[int]:
    return [line.position for line in chart.lines if line.element == element]


def build_use_god_review(
    chart: LiuyaoChart,
    role: LiuyaoQuestionRole,
) -> dict[str, Any]:
    primary = role.primary_use
    if primary is None:
        return {
            "schema_version": LIUYAO_REVIEW_VERSION,
            "status": "NO_SINGLE_PRIMARY_USE_SELECTED",
            "question_role_status": role.status,
            "candidates": [],
            "rule": (
                "題型未 source-lock 單一用神時不強選。若屬足球，必須先固定 candidate protocol，"
                "再在同一 cohort 比較，不得逐場切換。"
            ),
        }

    candidates: list[dict[str, Any]] = []
    if primary == "世爻":
        selected = [line for line in chart.lines if line.is_shi]
    elif primary == "應爻":
        selected = [line for line in chart.lines if line.is_ying]
    else:
        selected = [line for line in chart.lines if line.relative == primary]

    for line in selected:
        elements = _source_enemy_rival_elements(line.element)
        candidates.append(
            {
                "source": "VISIBLE_LINE",
                "position": line.position,
                "relative": line.relative,
                "branch": line.branch,
                "element": line.element,
                "moving": line.moving,
                "void": line.is_void,
                "month_relation": line.month_relation,
                "day_relation": line.day_relation,
                "spirit_roles": {
                    **elements,
                    "元神現爻": _line_role_matches(chart, elements["元神五行"]),
                    "忌神現爻": _line_role_matches(chart, elements["忌神五行"]),
                    "仇神現爻": _line_role_matches(chart, elements["仇神五行"]),
                },
            }
        )

    if not candidates and primary in {"父母", "兄弟", "官鬼", "妻財", "子孫"}:
        for line in chart.lines:
            if line.hidden_relative == primary and line.hidden_element:
                elements = _source_enemy_rival_elements(line.hidden_element)
                candidates.append(
                    {
                        "source": "HIDDEN_GOD_CANDIDATE",
                        "position": line.position,
                        "relative": line.hidden_relative,
                        "branch": line.hidden_branch,
                        "element": line.hidden_element,
                        "moving": False,
                        "void": line.hidden_branch in chart.void_branches,
                        "month_relation": None,
                        "day_relation": None,
                        "spirit_roles": {
                            **elements,
                            "元神現爻": _line_role_matches(chart, elements["元神五行"]),
                            "忌神現爻": _line_role_matches(chart, elements["忌神五行"]),
                            "仇神現爻": _line_role_matches(chart, elements["仇神五行"]),
                        },
                    }
                )

    if not candidates:
        status = "PRIMARY_USE_NOT_FOUND__REQUIRES_SOURCE_REVIEW"
    elif len(candidates) == 1:
        status = "SINGLE_CANDIDATE_READY"
    else:
        status = "MULTIPLE_USE_CANDIDATES__DO_NOT_PICK_BY_OUTCOME"

    return {
        "schema_version": LIUYAO_REVIEW_VERSION,
        "status": status,
        "primary_use_category": primary,
        "candidates": candidates,
        "selection_rule": [
            "同類用神多現時，不以爻位或吉凶直覺隨意挑一；須依日月旺衰、動靜、空破及題意綜合。",
            "元神＝生用神者；忌神＝克用神者；仇神＝克元神而生忌神者。",
            "元神、忌神、仇神是否有力仍取決於旺衰、動變、空破等，不因名目存在就自動有效。",
            "若用神伏藏，先標伏神候選；飛神生克、日月扶抑與是否得出仍須另審。",
        ],
    }


def build_strength_review(chart: LiuyaoChart) -> dict[str, Any]:
    month_element = BRANCH_ELEMENT[chart.month_branch]
    day_element = BRANCH_ELEMENT[chart.day_branch]
    rows: list[dict[str, Any]] = []

    for line in chart.lines:
        rows.append(
            {
                "position": line.position,
                "relative": line.relative,
                "branch": line.branch,
                "element": line.element,
                "month": {
                    "branch": chart.month_branch,
                    "element": month_element,
                    "direct_branch_relation": line.month_relation,
                    "element_relation_to_line": _element_relation(month_element, line.element),
                    "month_break": line.month_break,
                },
                "day": {
                    "branch": chart.day_branch,
                    "element": day_element,
                    "direct_branch_relation": line.day_relation,
                    "element_relation_to_line": _element_relation(day_element, line.element),
                    "day_clash": line.day_clash,
                },
                "void": line.is_void,
                "moving": line.moving,
                "boundary": (
                    "此列只列日月與爻的直接五行／沖合／空破事實；"
                    "不把多條件壓成單一旺衰分數。"
                ),
            }
        )

    return {
        "schema_version": LIUYAO_REVIEW_VERSION,
        "status": "DIRECT_MONTH_DAY_RELATIONS_READY__NO_NUMERIC_STRENGTH_SCORE",
        "month_branch": chart.month_branch,
        "month_element": month_element,
        "day_branch": chart.day_branch,
        "day_element": day_element,
        "lines": rows,
        "classical_priority": [
            "月建是萬卦提綱，日辰為六爻主宰；二者皆須參。",
            "月破、旬空、日沖不可脫離旺衰與動靜單獨定吉凶。",
            "同一爻可能同時得生又受沖；矛盾訊號必須保留，不做符號投票。",
        ],
    }


def build_motion_review(chart: LiuyaoChart) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for line in chart.lines:
        status: list[str] = []
        if line.moving:
            status.append("明動")
        elif line.day_clash:
            status.append("日沖靜爻")
            status.append("暗動／日破待旺衰判別")

        if line.changed_relation_to_original:
            status.append(line.changed_relation_to_original)
        if line.is_void:
            status.append("旬空")
        if line.month_break:
            status.append("月破")

        rows.append(
            {
                "position": line.position,
                "moving": line.moving,
                "status": status or ["靜"],
                "original": {
                    "relative": line.relative,
                    "stem": line.stem,
                    "branch": line.branch,
                    "element": line.element,
                },
                "changed": (
                    {
                        "relative": line.changed_relative,
                        "stem": line.changed_stem,
                        "branch": line.changed_branch,
                        "element": line.changed_element,
                        "relation_to_original": line.changed_relation_to_original,
                    }
                    if line.moving
                    else None
                ),
                "hidden": (
                    {
                        "relative": line.hidden_relative,
                        "branch": line.hidden_branch,
                        "element": line.hidden_element,
                        "status": "HIDDEN_CANDIDATE__UTILITY_NOT_AUTOMATIC",
                    }
                    if line.hidden_relative
                    else None
                ),
            }
        )

    return {
        "schema_version": LIUYAO_REVIEW_VERSION,
        "status": "MOTION_AND_CHANGE_RELATIONS_READY",
        "moving_line_count": len(chart.moving_lines),
        "moving_lines": list(chart.moving_lines),
        "lines": rows,
        "rules": [
            "動為始、變為終；明動爻與其變爻須成對審。",
            "變爻六親仍依正卦卦宮五行安定。",
            "日沖靜爻只先標候選，不自動判暗動；旺相有氣與休囚無氣須另審。",
            "伏神只在本卦缺該六親時由本宮純卦同位提出候選，不等於伏神必然有用。",
        ],
    }


def build_source_audit() -> dict[str, Any]:
    return {
        "schema_version": LIUYAO_REVIEW_VERSION,
        "status": "SOURCE_TIERED_CORE_READY",
        "primary_classical": [
            {
                "id": "LIUYAO_ZENGSHAN_BUYI",
                "title": "《增刪卜易》",
                "covers": [
                    "渾天甲子／納甲",
                    "六親",
                    "動變",
                    "月建",
                    "日辰",
                    "旬空",
                    "伏神",
                    "用神／元神／忌神／仇神",
                    "暗動與日破區分",
                ],
            },
            {
                "id": "LIUYAO_BOSHI_ZHENGZONG",
                "title": "《卜筮正宗》",
                "covers": ["世應", "六神起例", "納甲／裝卦"],
            },
            {
                "id": "LIUYAO_HUOZHULIN",
                "title": "《火珠林》",
                "covers": ["六親根源", "飛伏", "征戰占子孫／官鬼與世應"],
            },
            {
                "id": "LIUYAO_HUANGJINCE",
                "title": "《黃金策》",
                "covers": ["月建日辰", "世應", "動變", "用神綱領"],
            },
        ],
        "modern_teaching": [
            {
                "id": "MODERN_LIUYAO_VIDEO_USE_GOD_ORDER",
                "authority": "MODERN_TEACHING__DISCOVERY_ONLY",
                "rule": "影片只用來發現實務候選順序；若與古籍衝突，以 source audit 分層，不直接改核心。",
            }
        ],
        "user_video": {
            "id": "USER_VIDEO_-qgDHCHaDpo",
            "url": "https://youtu.be/-qgDHCHaDpo",
            "status": "PENDING_TRANSCRIPT__NOT_SOURCE_LOCKED",
            "rule": (
                "目前可用搜尋介面未返回該指定影片的標題／字幕／逐字稿；"
                "在能核對實際內容前，不把任何推測歸因給該影片。"
            ),
        },
    }


def build_liuyao_review(
    chart: LiuyaoChart,
    *,
    question_category: str = "GENERAL",
) -> LiuyaoReview:
    role = question_role(question_category)
    contradiction_register: list[dict[str, Any]] = []
    uncertainty_register: list[dict[str, Any]] = []

    for line in chart.lines:
        if line.month_break and line.moving:
            contradiction_register.append(
                {
                    "id": f"LINE_{line.position}_MONTH_BREAK_AND_MOVING",
                    "type": "STRENGTH_VS_MOTION",
                    "fact": "該爻月破但同時明動。",
                    "rule": "不得只因月破抹去動爻，也不得只因動而忽略月破；交由完整旺衰／生克審查。",
                }
            )
        if line.is_void and line.moving:
            contradiction_register.append(
                {
                    "id": f"LINE_{line.position}_VOID_AND_MOVING",
                    "type": "VOID_VS_MOTION",
                    "fact": "該爻旬空且明動。",
                    "rule": "空動涉及沖空填實與時機，V1 不自動下吉凶／應期。",
                }
            )
        if line.day_clash and not line.moving:
            uncertainty_register.append(
                {
                    "id": f"LINE_{line.position}_DAY_CLASH_STATIC",
                    "unknown": "此日沖靜爻究竟屬暗動或日破。",
                    "reason": "《增刪卜易》要求依旺相休囚區別；direct relation alone 不足。",
                }
            )

    if role.status.startswith("PROJECT_ADAPTATION_REQUIRED"):
        uncertainty_register.append(
            {
                "id": "QUESTION_ROLE_FOOTBALL",
                "unknown": "足球主客與世應／子孫官鬼的最佳映射。",
                "reason": "古籍有征戰法，但現代足球映射尚須同 cohort 方法比較。",
            }
        )

    return LiuyaoReview(
        schema_version=LIUYAO_REVIEW_VERSION,
        status="READY_WITH_DECLARED_GAPS",
        chart=chart.to_dict(),
        question_role={
            "schema_version": role.schema_version,
            "status": role.status,
            "question_category": role.question_category,
            "primary_use": role.primary_use,
            "secondary_uses": list(role.secondary_uses),
            "rationale": list(role.rationale),
            "authority": role.authority,
            "football_adaptation": role.football_adaptation,
        },
        use_god_review=build_use_god_review(chart, role),
        strength_review=build_strength_review(chart),
        motion_review=build_motion_review(chart),
        source_audit=build_source_audit(),
        contradiction_register=contradiction_register,
        uncertainty_register=uncertainty_register,
    )
