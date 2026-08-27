from __future__ import annotations

from datetime import datetime
from typing import Any

from jarvis.provenance import sha256_payload
from meihua import build_meihua_snapshot
from qimen.engine import cast_qimen
from qimen.models import QimenBoard

from .case_bundle import build_match_event_identity
from .event_layers import (
    build_football_event_identity,
    build_qimen_coach_participant_layer,
    empty_event_identity_layer,
    empty_participant_layer,
)
from .meihua_method import build_meihua_classical_method_audit
from .meihua_review import build_meihua_review_summary
from .meihua_timeline import build_football_temporal_audit
from .stark_vault import meihua_context, meihua_hexagram, qimen_context
from .yilin import build_meihua_yilin_bridge
from .zhouyi import build_meihua_zhouyi_review
from .zhouyi_line_review import build_zhouyi_line_meaning_review


DIVINATION_PACKET_VERSION = "DIVINATION_PACKET_V2"


def _locate_visible_stem(board: QimenBoard, stem: str) -> int:
    if stem == "甲":
        return board.chief_star_palace
    for number, state in board.palaces.items():
        if stem in state.heaven_stems:
            return number
    raise ValueError(f"天盤找不到用神：{stem}")


def _packet_hash(payload: dict[str, Any]) -> str:
    copy = dict(payload)
    copy.pop("packet_sha256", None)
    return sha256_payload(copy)


def build_qimen_packet(
    *,
    question: str,
    event_at: datetime,
    timezone_name: str,
    category: str = "general",
    home_team: str = "",
    away_team: str = "",
    fixture_identity: dict[str, Any] | None = None,
    coach_identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not question.strip():
        raise ValueError("問題不可空白")
    if event_at.tzinfo is None:
        raise ValueError("event_at 必須含時區")
    if category != "football_match" and (fixture_identity or coach_identity):
        raise ValueError("fixture_identity / coach_identity 只適用 football_match")
    board = cast_qimen(event_at, timezone_name)
    day_stem = board.calendar.day_ganzhi[0]
    hour_stem = board.calendar.hour_ganzhi[0]
    host_guest = None
    football_fixture = None
    match_event = None
    event_identity_layer = None
    participant_layer = None
    if category == "football_match":
        if not home_team.strip() or not away_team.strip():
            raise ValueError("足球比賽必須填主隊與客隊")
        football_fixture = {
            "home_team": home_team.strip(),
            "away_team": away_team.strip(),
        }
        host_guest = {
            "policy": "主隊取日干、客隊取時干；甲取值符宮",
            "home_team": home_team.strip(),
            "home_stem": day_stem,
            "home_palace": _locate_visible_stem(board, day_stem),
            "away_team": away_team.strip(),
            "away_stem": hour_stem,
            "away_palace": _locate_visible_stem(board, hour_stem),
        }
        match_event = build_match_event_identity(
            home_team=home_team,
            away_team=away_team,
            event_datetime=board.calendar.local_datetime,
            timezone_name=board.calendar.timezone_name,
        )
        event_identity_layer = (
            build_football_event_identity(fixture_identity)
            if fixture_identity is not None
            else empty_event_identity_layer()
        )
        participant_layer = (
            build_qimen_coach_participant_layer(board, coach_identity)
            if coach_identity is not None
            else empty_participant_layer()
        )

    chart = board.to_dict()
    chart.pop("generated_at", None)

    event_identity_layer = (
        build_football_event_identity(fixture_identity)
        if category == "football_match" and fixture_identity is not None
        else (empty_event_identity_layer() if category == "football_match" else None)
    )
    interpretation_role = (
        {
            "role": "RESULT_ENGINE_INPUT",
            "scope": "REGULATION_TIME_RESULT_AND_SCORE_CANDIDATES_FOR_CHATGPT",
            "rule": (
                "奇門是 ChatGPT 判斷正規時間勝負與候選比分的主要術數證據層；"
                "JARVIS 只提供盤象與知識，不自動輸出勝負、比分或統計機率。"
            ),
        }
        if category == "football_match"
        else {
            "role": "QIMEN_INTERPRETATION_INPUT",
            "scope": "GENERAL_DIVINATION",
            "rule": "JARVIS 提供奇門盤象與知識，最後判讀由 ChatGPT 完成。",
        }
    )

    payload: dict[str, Any] = {
        "schema_version": DIVINATION_PACKET_VERSION,
        "packet_purpose": "JARVIS_CAST_AND_RETRIEVE__CHATGPT_INTERPRETS",
        "system": "QIMEN_DUNJIA",
        "question": {"text": question.strip(), "category": category},
        "event": {
            "datetime": board.calendar.local_datetime.isoformat(),
            "timezone": board.calendar.timezone_name,
            "normalization": "ACTUAL_CAST_EVENT_LOCAL_TIME",
        },
        "football_fixture": football_fixture,
        "match_event": match_event,
        "event_identity_layer": event_identity_layer,
        "participant_layer": participant_layer,
        "interpretation_role": interpretation_role,
        "method": {
            "family": board.method.family,
            "plate_method": board.method.plate_method,
            "ju_method": board.method.ju_method,
            "time_basis": board.method.time_basis,
            "zi_hour_boundary": board.method.zi_hour_boundary,
            "center_policy": board.method.center_policy,
            "deity_policy": board.method.deity_policy,
            "version": board.method.version,
        },
        "host_guest": host_guest,
        "chart": chart,
        "knowledge_context": qimen_context(board),
        "ai_interpretation_contract": [
            "不要重新起局或修改盤面；以 chart 為唯一盤象事實。",
            "先區分盤面事實、古典／知識庫材料、現代足球類比，再做綜合推演。",
            "足球類比不是古籍原文，不可把單一門、星、神、格局直接轉成勝率或固定比分。",
            "同時列出支持與反證，遇到盤象矛盾要明示，不得強行統一。",
            "足球若 participant_layer.status=READY，年命落宮只作雙方承盤差異；主教練映射屬 PROJECT_ADAPTATION，不是古籍足球規則。",
            "足球若 event_identity_layer.status=NOT_PROVIDED，禁止只因隊名不同而從同一時間盤硬分叉出不同結論。",
            (
                "足球問題中，奇門是 RESULT_ENGINE_INPUT：ChatGPT 可由完整盤局提出正規時間主勝／和局／客勝與有限候選比分；"
                "這是最終 AI 判讀，不是 JARVIS 自動規則。"
                if category == "football_match"
                else "一般問題由 ChatGPT 依完整奇門盤局做最後判讀。"
            ),
        ],
    }
    payload["packet_sha256"] = _packet_hash(payload)
    return payload


def build_meihua_packet(
    *,
    question: str,
    event_at: datetime,
    timezone_name: str,
    category: str = "general",
    home_team: str = "",
    away_team: str = "",
    timeline_horizon_minutes: int = 180,
    match_clock_events: list[dict[str, Any]] | None = None,
    fixture_identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not question.strip():
        raise ValueError("問題不可空白")
    if event_at.tzinfo is None:
        raise ValueError("event_at 必須含時區")
    if category == "football_match" and (not home_team.strip() or not away_team.strip()):
        raise ValueError("足球比賽必須填主隊與客隊")
    if category != "football_match" and match_clock_events:
        raise ValueError("match_clock_events 只適用 football_match")
    if category != "football_match" and fixture_identity:
        raise ValueError("fixture_identity 只適用 football_match")

    snapshot = build_meihua_snapshot(event_at, timezone_name)
    knowledge_context = meihua_context(snapshot)
    original = meihua_hexagram(snapshot.upper_trigram, snapshot.lower_trigram)
    mutual = meihua_hexagram(snapshot.mutual_upper_trigram, snapshot.mutual_lower_trigram)
    changed = meihua_hexagram(snapshot.changed_upper_trigram, snapshot.changed_lower_trigram)
    method_audit = build_meihua_classical_method_audit(snapshot)
    zhouyi_review = build_meihua_zhouyi_review(
        snapshot,
        original_catalog=original,
        mutual_catalog=mutual,
        changed_catalog=changed,
    )
    zhouyi_review["moving_line"]["meaning_review"] = build_zhouyi_line_meaning_review(
        int(original["number"]), snapshot.moving_line
    )
    yilin_bridge = build_meihua_yilin_bridge(original, changed)
    temporal_precision_audit = (
        build_football_temporal_audit(
            snapshot,
            horizon_minutes=timeline_horizon_minutes,
            match_clock_events=match_clock_events,
        )
        if category == "football_match"
        else None
    )
    review_summary = build_meihua_review_summary(
        snapshot,
        method_audit=method_audit,
        zhouyi_review=zhouyi_review,
        yilin_bridge=yilin_bridge,
        temporal_precision_audit=temporal_precision_audit,
    )

    football_fixture = (
        {"home_team": home_team.strip(), "away_team": away_team.strip()}
        if category == "football_match"
        else None
    )
    match_event = (
        build_match_event_identity(
            home_team=home_team,
            away_team=away_team,
            event_datetime=snapshot.event_local_at,
            timezone_name=snapshot.timezone_name,
        )
        if category == "football_match"
        else None
    )
    interpretation_role = (
        {
            "role": "STRUCTURE_STRESS_TEST",
            "scope": "OPENING_MIDDLE_LATE_STRUCTURE_AND_QIMEN_VALIDATION",
            "rule": (
                "梅花負責開局／中段／後段機制、轉折條件、支持與反證；"
                "不得再獨立產生第二套勝負或比分與奇門投票。"
            ),
        }
        if category == "football_match"
        else {
            "role": "MEIHUA_INTERPRETATION_INPUT",
            "scope": "GENERAL_DIVINATION",
            "rule": "JARVIS 提供梅花結構、周易與易林來源，最後判讀由 ChatGPT 完成。",
        }
    )

    payload: dict[str, Any] = {
        "schema_version": DIVINATION_PACKET_VERSION,
        "packet_purpose": "JARVIS_CAST_AND_RETRIEVE__CHATGPT_INTERPRETS",
        "system": "MEIHUA_YISHU",
        "question": {"text": question.strip(), "category": category},
        "event": {
            "datetime": snapshot.event_local_at.isoformat(),
            "timezone": snapshot.timezone_name,
            "normalization": "ACTUAL_CAST_EVENT_LOCAL_TIME",
        },
        "football_fixture": football_fixture,
        "match_event": match_event,
        "event_identity_layer": event_identity_layer,
        "interpretation_role": interpretation_role,
        "method": {
            "type": "年月日時起卦",
            "class": "XIANTIAN_NUMBER_METHOD",
            "time_basis": "事件所在地民用時間",
            "engine_version": snapshot.schema_version,
        },
        "hexagram": snapshot.to_dict(),
        "meihua_method_audit": method_audit,
        "temporal_precision_audit": temporal_precision_audit,
        "zhouyi_review": zhouyi_review,
        "yilin_bridge": yilin_bridge,
        "review_summary": review_summary,
        "knowledge_context": knowledge_context,
        "ai_interpretation_contract": [
            "不要重新起卦或修改本卦、互卦、變卦、動爻、體用；以 hexagram 為梅花盤象事實。",
            "先讀 meihua_method_audit：本 packet 的 hexagram 是 XIANTIAN_NUMBER_METHOD 時勢卦，體用、旺衰、互變與內外作用網是共同時間結構。",
            "足球若 event_identity_layer.status=CANONICAL_PREMATCH_IDENTITY_READY，再讀其 MEIHUA_EVENT_IDENTITY_V1 作每場事件卦；hash 映射是 PROJECT_ADAPTATION，不冒充古籍公式。",
            "event_identity_layer 只負責區分 fixture 的作用鏈，不得把 hash、卦數或 digest 直接轉成比分。",
            "body_use_network 同時保存互卦 upper/lower 的機械位置與 body_mutual/use_mutual 古法身份；體互優先於用互審查。",
            "足球問題再讀 temporal_precision_audit：開賽 anchor cast 永遠不變；時支/日界/DST交界只作 SECONDARY_DIAGNOSTIC，不得自動解讀為逆轉。",
            "temporal_precision_audit 的 elapsed_real_minutes_from_kickoff 是 wall-clock 真實經過時間，不等同官方比賽分鐘。",
            "若提供 temporal_precision_audit.match_clock_audit.events，只用 timestamped event log 定位實際賽事階段；不得在事件之間線性插值出虛構官方分鐘。",
            "若 temporal_precision_audit 有 diagnostic_recast，只比較它相對 anchor 哪些欄位改變；禁止用 secondary recast 取代主卦或投票生成勝率/比分。",
            "對目前年月日時法，zhouyi_review 的卦辭／彖／象／動爻爻辭是 source-aware SUPPORTING review；不得讓單句爻辭自動凌駕體用、旺衰與互變。",
            "先核對 zhouyi_review.source_audit；古籍文字不得由 AI 改寫、補造或用後見資料修正。",
            "真正動爻的 meaning_review 是 PROJECT_REVIEW__NOT_CLASSICAL_COMMENTARY：先讀原文，再讀 text_conditions、risk_boundary、turning_point、misread_warnings 與 football evidence/counter-evidence。",
            "固定合參順序：方法審查 → anchor 本卦／體用 → 旺衰 → 體互／用互 → 變卦作用 → 時間邊界／match-clock 審查 → 動靜／內外／已記錄外應 → 周易 supporting review → 焦氏易林本卦之變卦 → 支持／反證。",
            "meihua_method_audit.body_use_network 要連同體卦旺衰閱讀；不可只看單一 body_use_relation。",
            "三要、十應、外應若標記 NOT_RECORDED，就視為缺失資料，不得由 AI 或賽後事件補造。",
            "先讀 review_summary.contradiction_register 與 uncertainty_register；矛盾和缺口必須保留，不可為了單一結論刪除。",
            "review_summary.relation_signals 是中性的結構分類，不等於吉凶投票或統計權重。",
            "zhouyi_review 中 classical_text 是固定來源數位轉錄；project_general、football_modern_application、semantic_profile 與 meaning_review 是 JARVIS 專案層，必須分開陳述。",
            "焦氏易林在此是 MEIHUA_YILIN_BRIDGE：只補充本卦到最終變卦的情境，不宣稱等同焦林直日占法，也不可重起一套卦。",
            "若周易經文、梅花體用與易林情境彼此矛盾，保留矛盾、解釋成立條件，不得強行統一。",
            "不可只看一條生克、單一卦象、單句爻辭、單條林辭、image atom 或一次時辰交界就直接判勝負。",
            (
                "足球問題中，梅花是 STRUCTURE_STRESS_TEST：只輸出結構、轉折、支持與反證，"
                "不得再獨立產生第二套勝負或比分。"
                if category == "football_match"
                else "一般問題由 ChatGPT 依完整梅花結構與原典來源做最後判讀。"
            ),
        ],
    }
    payload["packet_sha256"] = _packet_hash(payload)
    return payload
