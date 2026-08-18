from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import product
from typing import Any

from qimen.constants import (
    DOOR_ELEMENT,
    ELEMENT_CONTROLS,
    ELEMENT_GENERATES,
    NAMED_STEM_PAIRS,
    PALACES,
    STAR_ELEMENT,
    STEM_ELEMENT,
    VISIBLE_STEMS,
)
from qimen.models import PalaceState


RELATION_ENGINE_VERSION = "stark-qimen-relations-v1.0.0"
RELATION_TYPES = {
    "stem_pair": "天地盤干",
    "star_door": "星門",
    "door_palace": "門宮",
    "star_palace": "星宮",
}


@dataclass(frozen=True)
class QimenRelation:
    schema_version: str
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
    general_interpretation: str
    classical_pattern: str | None
    classical_category: str | None
    authority: str
    source_id: str
    caution: str
    football_meaning: str
    observable_signals: tuple[str, ...]
    counter_signals: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _element_relation(
    first_element: str,
    second_element: str,
    first_role: str,
    second_role: str,
) -> tuple[str, str]:
    if first_element == second_element:
        return "比和", f"{first_role}與{second_role}同氣，訊號容易重複或放大，也要防功能單一化。"
    if ELEMENT_GENERATES[first_element] == second_element:
        return "前生後", f"{first_role}生{second_role}：前層投入並支援後層，同時存在耗洩。"
    if ELEMENT_GENERATES[second_element] == first_element:
        return "後生前", f"{second_role}生{first_role}：前層有根與支援，後層承擔輸出。"
    if ELEMENT_CONTROLS[first_element] == second_element:
        return "前剋後", f"{first_role}剋{second_role}：前層主動限制後層，功能可能以壓制方式發用。"
    return "後剋前", f"{second_role}剋{first_role}：前層受環境或底層限制，作用可能延遲、變形或費力。"


def _football_semantics(
    relation_type: str,
    relation_code: str,
    first_role: str,
    second_role: str,
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    layer = {
        "stem_pair": "外顯觸發與底層條件",
        "star_door": "能力／節奏與行動通道",
        "door_palace": "戰術行動與場上環境",
        "star_palace": "能力／節奏與場上環境",
    }[relation_type]
    if relation_code == "比和":
        meaning = f"{layer}同氣，可能形成連續、穩定或重複的比賽模式；也要防止戰術過於單一。"
        observable = ("相同進攻／防守模式反覆成功", "節奏與站位長時間維持一致")
        counter = ("場上很快改變打法且原模式無法延續", "相同配置反覆被對手破解")
    elif relation_code == "前生後":
        meaning = f"{first_role}向{second_role}輸出，可能讓戰術執行更順，但前層也承擔體能或資源消耗。"
        observable = ("前層行動持續為後續創造空間或接應", "優勢建立同時出現明顯體能／人力投入")
        counter = ("前層投入沒有轉化成後續有效行動", "資源投入很低卻仍長時間維持相同強度")
    elif relation_code == "後生前":
        meaning = f"{second_role}為{first_role}提供根基，可能呈現環境／通道支援能力發揮。"
        observable = ("隊形或空間為核心能力提供穩定支援", "球員能力在合適區域反覆被放大")
        counter = ("環境與配置持續破壞核心能力發揮", "主要能力始終孤立、缺乏接應")
    elif relation_code == "前剋後":
        meaning = f"{first_role}主動限制{second_role}，足球上常對應壓迫、封鎖、強制改變對方或自身通道。"
        observable = ("明確壓迫／封線使原有通道失效", "對位優勢迫使對手改變出球或站位")
        counter = ("被限制的一層仍持續自由運作", "壓迫／封鎖沒有造成節奏或路線變化")
    else:
        meaning = f"{first_role}受到{second_role}限制，可能出現延遲、繞行、低效率或被迫改變方案。"
        observable = ("原定戰術被環境／對位壓制而改道", "推進或終結需要更多觸球與額外動作")
        counter = ("受制層仍直接高效運作", "外部限制沒有造成任何可見代價")
    return meaning, observable, counter


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


def build_relation(relation_type: str, first: str, second: str | int) -> QimenRelation:
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
        authority = "古籍有逐組合參傳統＋五行組合推導"
        caution = "生成摘要不冒充古籍逐句斷例；仍須加入所在宮、旺衰、神與問題。"
    elif relation_type == "door_palace":
        first_name = _require_key(first, DOOR_ELEMENT, "八門")
        palace_number = _require_palace(second)
        second_name = PALACES[palace_number]["name"]
        first_role, second_role = "八門功能", "九宮環境"
        first_element, second_element = DOOR_ELEMENT[first_name], PALACES[palace_number]["element"]
        preliminary, _ = _element_relation(first_element, second_element, first_role, second_role)
        if preliminary == "前剋後":
            classical = ("門迫", "宮門關係")
        elif preliminary == "後剋前":
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
        caution = "星的基礎象義會受宮、門、神、時令及結構狀態改變，不作單符號結論。"

    relation_code, general = _element_relation(first_element, second_element, first_role, second_role)
    classical_pattern = classical[0] if classical else None
    classical_category = classical[1] if classical else None
    if classical_pattern:
        general = f"{classical_pattern}（{classical_category}）；{general}"
    football, observable, counter = _football_semantics(
        relation_type,
        relation_code,
        first_role,
        second_role,
    )
    return QimenRelation(
        schema_version=RELATION_ENGINE_VERSION,
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
        general_interpretation=general,
        classical_pattern=classical_pattern,
        classical_category=classical_category,
        authority=authority,
        source_id=source_id,
        caution=caution,
        football_meaning=football,
        observable_signals=observable,
        counter_signals=counter,
    )


def all_relations() -> tuple[QimenRelation, ...]:
    """Return the complete 306-slot relation matrix used by Operation STARK."""
    rows: list[QimenRelation] = []
    rows.extend(build_relation("stem_pair", heaven, earth) for heaven, earth in product(VISIBLE_STEMS, repeat=2))
    rows.extend(build_relation("star_door", star, door) for star, door in product(STAR_ELEMENT, DOOR_ELEMENT))
    rows.extend(build_relation("door_palace", door, palace) for door, palace in product(DOOR_ELEMENT, PALACES))
    rows.extend(build_relation("star_palace", star, palace) for star, palace in product(STAR_ELEMENT, PALACES))
    return tuple(rows)


def relations_for_palace(state: PalaceState) -> tuple[QimenRelation, ...]:
    rows: list[QimenRelation] = []
    earth_stems = (state.earth_stem, *state.earth_hidden_stems)
    for heaven, earth in product(state.heaven_stems, earth_stems):
        rows.append(build_relation("stem_pair", heaven, earth))
    if state.door:
        rows.append(build_relation("door_palace", state.door, state.number))
    for star in state.stars:
        rows.append(build_relation("star_palace", star, state.number))
        if state.door:
            rows.append(build_relation("star_door", star, state.door))
    unique = {row.key: row for row in rows}
    return tuple(unique.values())
