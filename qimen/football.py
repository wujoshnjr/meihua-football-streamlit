from __future__ import annotations

from dataclasses import asdict, dataclass

from .constants import (
    ELEMENT_CONTROLS,
    ELEMENT_GENERATES,
    PALACES,
    SEASON_BY_TERM,
    SEASON_ELEMENT,
    STAR_ELEMENT,
)
from .models import PalaceState, QimenBoard


GATE_SIGNAL = {"休門": 1, "生門": 2, "傷門": -1, "杜門": 0, "景門": 1, "死門": -2, "驚門": -1, "開門": 2}
STAR_SIGNAL = {"天蓬": -1, "天任": 2, "天沖": 1, "天輔": 2, "天英": 0, "天芮": -2, "天禽": 2, "天柱": -1, "天心": 2}
DEITY_SIGNAL = {"值符": 2, "螣蛇": -1, "太陰": 1, "六合": 2, "白虎": -2, "玄武": -1, "九地": 1, "九天": 1}


@dataclass(frozen=True)
class TeamProfile:
    role: str
    stem: str
    palace: int
    palace_name: str
    door: str | None
    stars: tuple[str, ...]
    deity: str | None
    seasonal_state: str
    signal_index: int
    strengths: tuple[str, ...]
    risks: tuple[str, ...]


@dataclass(frozen=True)
class Scenario:
    rank: int
    title: str
    signal_index: int
    basis: tuple[str, ...]
    boundary: str


@dataclass(frozen=True)
class FootballReading:
    mapping_version: str
    home: TeamProfile
    away: TeamProfile
    scenarios: tuple[Scenario, ...]
    event_signals: tuple[str, ...]
    disclaimer: str

    def to_dict(self):
        return asdict(self)


def _visible_stem(stem: str, board: QimenBoard) -> str:
    return board.xun_head_instrument if stem == "甲" else stem


def locate_use_stem(board: QimenBoard, stem: str) -> int:
    if stem == "甲":
        return board.chief_star_palace
    for number, state in board.palaces.items():
        if stem in state.heaven_stems:
            return number
    raise ValueError(f"天盤找不到用神：{stem}")


def seasonal_state(element: str, term: str) -> tuple[str, int]:
    season_element = SEASON_ELEMENT[SEASON_BY_TERM[term]]
    if element == season_element:
        return "旺", 2
    if ELEMENT_GENERATES[season_element] == element:
        return "相", 1
    if ELEMENT_GENERATES[element] == season_element:
        return "休", 0
    if ELEMENT_CONTROLS[element] == season_element:
        return "囚", -1
    return "廢", -2


def _profile(role: str, stem: str, board: QimenBoard) -> TeamProfile:
    palace_number = locate_use_stem(board, stem)
    state: PalaceState = board.palaces[palace_number]
    strength: list[str] = []
    risks: list[str] = []
    index = 0

    if state.door:
        index += GATE_SIGNAL[state.door]
        (strength if GATE_SIGNAL[state.door] > 0 else risks).append(f"{state.door}臨宮")
    for star in state.stars:
        index += STAR_SIGNAL[star]
        (strength if STAR_SIGNAL[star] > 0 else risks).append(f"{star}同宮")
    if state.deity:
        index += DEITY_SIGNAL[state.deity]
        (strength if DEITY_SIGNAL[state.deity] > 0 else risks).append(f"{state.deity}同宮")

    star_element = STAR_ELEMENT[state.stars[0]] if state.stars else PALACES[palace_number]["element"]
    season_name, season_score = seasonal_state(star_element, board.calendar.solar_term)
    index += season_score
    (strength if season_score > 0 else risks if season_score < 0 else strength).append(f"主星季節狀態：{season_name}")

    if state.is_void:
        index -= 2
        risks.append("旬空：訊號可能延遲或名實不符")
    if state.is_horse:
        strength.append("驛馬：移動、速度或變陣訊號")
    local_patterns = [p for p in board.patterns if p.palace == palace_number]
    for pattern in local_patterns:
        if pattern.category in {"吉格", "三遁", "三詐", "五假"}:
            index += 1
            strength.append(pattern.name)
        elif pattern.category in {"凶格", "庚格"}:
            index -= 1
            risks.append(pattern.name)
        else:
            risks.append(pattern.name)

    return TeamProfile(
        role=role,
        stem=_visible_stem(stem, board),
        palace=palace_number,
        palace_name=state.name,
        door=state.door,
        stars=tuple(state.stars),
        deity=state.deity,
        seasonal_state=season_name,
        signal_index=index,
        strengths=tuple(dict.fromkeys(strength)),
        risks=tuple(dict.fromkeys(risks)),
    )


def _scenario_candidates(home: TeamProfile, away: TeamProfile, board: QimenBoard) -> list[tuple[str, int, tuple[str, ...]]]:
    diff = home.signal_index - away.signal_index
    risk_patterns = tuple(p.name for p in board.patterns if p.category in {"凶格", "庚格", "戰格"})
    candidates = [
        ("主隊結構較能發用", diff, (f"主隊訊號索引 {home.signal_index}", f"客隊訊號索引 {away.signal_index}", *home.strengths[:2])),
        ("客隊結構較能發用", -diff, (f"客隊訊號索引 {away.signal_index}", f"主隊訊號索引 {home.signal_index}", *away.strengths[:2])),
        ("攻守膠著、先看失誤觸發", 3 - abs(diff), (f"雙方索引差 {abs(diff)}", f"值使為{board.chief_door}", "索引接近時不強行分勝負")),
        ("高波動與牌傷風險", len(risk_patterns), ("、".join(risk_patterns[:4]) or "未見主要戰凶格", "白虎／傷門／驚門需與賽前傷停核對")),
        ("速度或陣型變動成為關鍵", 1 + int(board.palaces[board.horse_palace].door in {"開門", "傷門", "驚門"}), (f"驛馬在{board.palaces[board.horse_palace].name}", f"值符在{board.chief_star_palace}宮", f"值使在{board.chief_door_palace}宮")),
    ]
    return candidates


def interpret_football(board: QimenBoard) -> FootballReading:
    home = _profile("主隊／日干", board.calendar.day_ganzhi[0], board)
    away = _profile("客隊／時干", board.calendar.hour_ganzhi[0], board)
    candidates = sorted(_scenario_candidates(home, away, board), key=lambda row: row[1], reverse=True)
    scenarios = tuple(
        Scenario(
            rank=index,
            title=title,
            signal_index=score,
            basis=basis,
            boundary="只排序候選解讀；不是勝率、進球數或投注信心。",
        )
        for index, (title, score, basis) in enumerate(candidates, 1)
    )
    event_signals = (
        f"值符：{board.chief_star}落{board.chief_star_palace}宮",
        f"值使：{board.chief_door}落{board.chief_door_palace}宮",
        f"旬空：{'、'.join(board.void_branches)}",
        f"驛馬：{board.horse_branch}／{board.horse_palace}宮",
    )
    return FootballReading(
        mapping_version="football-day-hour-v1.0.0",
        home=home,
        away=away,
        scenarios=scenarios,
        event_signals=event_signals,
        disclaimer="奇門索引只用於同一張盤內排序候選情境；不自動產生 1X2、固定比分、勝率、期望進球或投注建議。",
    )
