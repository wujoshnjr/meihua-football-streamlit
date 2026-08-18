from __future__ import annotations

from datetime import datetime
from typing import Any

from jarvis.provenance import sha256_payload
from meihua import build_meihua_snapshot
from qimen.engine import cast_qimen
from qimen.models import QimenBoard

from .stark_vault import meihua_context, qimen_context


DIVINATION_PACKET_VERSION = "DIVINATION_PACKET_V1"


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
) -> dict[str, Any]:
    if not question.strip():
        raise ValueError("問題不可空白")
    if event_at.tzinfo is None:
        raise ValueError("event_at 必須含時區")
    board = cast_qimen(event_at, timezone_name)
    day_stem = board.calendar.day_ganzhi[0]
    hour_stem = board.calendar.hour_ganzhi[0]
    host_guest = None
    if category == "football_match":
        if not home_team.strip() or not away_team.strip():
            raise ValueError("足球比賽必須填主隊與客隊")
        host_guest = {
            "policy": "主隊取日干、客隊取時干；甲取值符宮",
            "home_team": home_team.strip(),
            "home_stem": day_stem,
            "home_palace": _locate_visible_stem(board, day_stem),
            "away_team": away_team.strip(),
            "away_stem": hour_stem,
            "away_palace": _locate_visible_stem(board, hour_stem),
        }

    chart = board.to_dict()
    # QimenBoard.generated_at is audit metadata, not part of the deterministic chart.
    # Removing it makes the same event/method produce the same packet fingerprint.
    chart.pop("generated_at", None)

    payload: dict[str, Any] = {
        "schema_version": DIVINATION_PACKET_VERSION,
        "packet_purpose": "JARVIS_CAST_AND_RETRIEVE__CHATGPT_INTERPRETS",
        "system": "QIMEN_DUNJIA",
        "question": {"text": question.strip(), "category": category},
        "event": {"datetime": event_at.isoformat(), "timezone": timezone_name},
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
            "若是足球問題，最後可給趨勢判讀與關鍵情境，但需說明不確定性。",
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
) -> dict[str, Any]:
    if not question.strip():
        raise ValueError("問題不可空白")
    if event_at.tzinfo is None:
        raise ValueError("event_at 必須含時區")
    if category == "football_match" and (not home_team.strip() or not away_team.strip()):
        raise ValueError("足球比賽必須填主隊與客隊")

    snapshot = build_meihua_snapshot(event_at, timezone_name)
    payload: dict[str, Any] = {
        "schema_version": DIVINATION_PACKET_VERSION,
        "packet_purpose": "JARVIS_CAST_AND_RETRIEVE__CHATGPT_INTERPRETS",
        "system": "MEIHUA_YISHU",
        "question": {"text": question.strip(), "category": category},
        "event": {"datetime": event_at.isoformat(), "timezone": timezone_name},
        "football_fixture": (
            {"home_team": home_team.strip(), "away_team": away_team.strip()}
            if category == "football_match"
            else None
        ),
        "method": {
            "type": "年月日時起卦",
            "time_basis": "事件所在地民用時間",
            "engine_version": snapshot.schema_version,
        },
        "hexagram": snapshot.to_dict(),
        "knowledge_context": meihua_context(snapshot),
        "ai_interpretation_contract": [
            "不要重新起卦或修改本卦、互卦、變卦、動爻、體用。",
            "依序合參：本卦 → 體用 → 旺衰 → 互卦 → 變卦 → 動爻 → 可用外應。",
            "知識庫中的 football 欄位是現代足球類比，不是《梅花易數》古文。",
            "不可只看一條生克就直接判勝負；必須處理相互支持與相互抵銷的訊號。",
            "若是足球問題，最後可給比賽走勢、可能轉折與需觀察的場上證據，但不捏造統計勝率。",
        ],
    }
    payload["packet_sha256"] = _packet_hash(payload)
    return payload
