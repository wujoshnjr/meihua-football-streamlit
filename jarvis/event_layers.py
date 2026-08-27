from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import unicodedata

from jarvis.provenance import canonical_json, sha256_payload
from meihua.engine import TRIGRAM_BY_NUMBER, TRIGRAM_FROM_LINES, TRIGRAM_LINES
from qimen.constants import BRANCHES, ELEMENT_CONTROLS, ELEMENT_GENERATES, STEMS
from qimen.models import QimenBoard


FOOTBALL_EVENT_IDENTITY_VERSION = "FOOTBALL_EVENT_IDENTITY_V1"
MEIHUA_EVENT_IDENTITY_VERSION = "MEIHUA_EVENT_IDENTITY_V1"
QIMEN_PARTICIPANT_LAYER_VERSION = "QIMEN_PARTICIPANT_LAYER_V1"
FOOTBALL_DIFFERENTIATION_AUDIT_VERSION = "FOOTBALL_DIFFERENTIATION_AUDIT_V1"
FOOTBALL_COLLISION_AUDIT_VERSION = "FOOTBALL_COLLISION_AUDIT_V1"


def _clean_text(value: Any, field: str) -> str:
    cleaned = " ".join(unicodedata.normalize("NFKC", str(value)).strip().split())
    if not cleaned:
        raise ValueError(f"{field} 不可空白")
    return cleaned


def _canonical_label(value: Any, field: str) -> str:
    return _clean_text(value, field).upper()


def _aware_utc(value: Any) -> datetime:
    if isinstance(value, datetime):
        instant = value
    else:
        raw = _clean_text(value, "scheduled_kickoff_utc")
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            instant = datetime.fromisoformat(raw)
        except ValueError as exc:
            raise ValueError("scheduled_kickoff_utc 必須是 ISO-8601 datetime") from exc
    if instant.tzinfo is None:
        raise ValueError("scheduled_kickoff_utc 必須含時區")
    return instant.astimezone(timezone.utc).replace(microsecond=0)


def _digest_cast(signature: str) -> dict[str, Any]:
    upper_number = int(signature[0:8], 16) % 8 + 1
    lower_number = int(signature[8:16], 16) % 8 + 1
    moving_line = int(signature[16:24], 16) % 6 + 1

    upper = TRIGRAM_BY_NUMBER[upper_number]
    lower = TRIGRAM_BY_NUMBER[lower_number]
    lines = TRIGRAM_LINES[lower] + TRIGRAM_LINES[upper]
    changed = list(lines)
    changed[moving_line - 1] = 1 - changed[moving_line - 1]
    changed_lower = TRIGRAM_FROM_LINES[tuple(changed[:3])]
    changed_upper = TRIGRAM_FROM_LINES[tuple(changed[3:])]

    if moving_line <= 3:
        body = upper
        use = lower
    else:
        body = lower
        use = upper

    return {
        "upper_number": upper_number,
        "upper_trigram": upper,
        "lower_number": lower_number,
        "lower_trigram": lower,
        "moving_line": moving_line,
        "body_trigram": body,
        "use_trigram": use,
        "changed_upper_trigram": changed_upper,
        "changed_lower_trigram": changed_lower,
    }


def build_football_event_identity(fixture_identity: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic pre-match event identity and event-specific Meihua cast.

    The hash-to-trigram mapping is a JARVIS project rule. It is inspired by the
    classical Meihua permission to cast from numbers, sounds and written text,
    but it is not presented as a transmitted classical formula.
    """

    required = (
        "competition",
        "season",
        "home_official_name",
        "away_official_name",
        "scheduled_kickoff_utc",
    )
    missing = [key for key in required if key not in fixture_identity]
    if missing:
        raise ValueError("fixture_identity 缺少欄位：" + ", ".join(missing))

    kickoff = _aware_utc(fixture_identity["scheduled_kickoff_utc"])
    canonical_fields = {
        "competition": _canonical_label(fixture_identity["competition"], "competition"),
        "season": _canonical_label(fixture_identity["season"], "season"),
        "home_official_name": _canonical_label(
            fixture_identity["home_official_name"], "home_official_name"
        ),
        "away_official_name": _canonical_label(
            fixture_identity["away_official_name"], "away_official_name"
        ),
        "scheduled_kickoff_utc": kickoff.isoformat().replace("+00:00", "Z"),
    }
    event_signature = sha256_payload(canonical_fields)
    event_key = canonical_json(canonical_fields)

    return {
        "schema_version": FOOTBALL_EVENT_IDENTITY_VERSION,
        "status": "CANONICAL_PREMATCH_IDENTITY_READY",
        "canonical_fields": canonical_fields,
        "event_key": event_key,
        "event_signature_sha256": event_signature,
        "normalization": "UNICODE_NFKC__TRIM_COLLAPSE_WHITESPACE__UPPERCASE__UTC_SECONDS",
        "identity_rule": (
            "competition + season + official home/away names + scheduled kickoff UTC; "
            "query order and post-match result are excluded"
        ),
        "meihua_event_cast": {
            "schema_version": MEIHUA_EVENT_IDENTITY_VERSION,
            "authority": "PROJECT_ADAPTATION__DETERMINISTIC_EVENT_HASH__NOT_CLASSICAL_FORMULA",
            "mapping_rule": (
                "SHA256 canonical event fields; hex[0:8] mod8 -> upper, "
                "hex[8:16] mod8 -> lower, hex[16:24] mod6 -> moving line"
            ),
            "cast": _digest_cast(event_signature),
            "classical_analogy": (
                "《梅花易數》允許年月日時之外，以物數、聲音、字等信息起卦；"
                "本 hash 映射只用於固定賽事 identity，屬現代可重現取數規則。"
            ),
        },
        "anti_backfill": [
            "不得以賽後比分、勝負或事件修改 canonical fields。",
            "不得依詢問順序、清單排序或人工偏好加減數。",
            "official name / competition / season / kickoff 修正必須保留資料來源與修正時間。",
        ],
    }


def empty_event_identity_layer() -> dict[str, Any]:
    return {
        "schema_version": FOOTBALL_EVENT_IDENTITY_VERSION,
        "status": "NOT_PROVIDED",
        "rule": (
            "未提供 canonical fixture identity 時，年月日時等 temporal layers "
            "不得單獨用來區分同時開賽的不同 fixture。"
        ),
    }


def _validate_ganzhi(value: Any, field: str) -> str:
    ganzhi = _clean_text(value, field)
    if len(ganzhi) != 2 or ganzhi[0] not in STEMS or ganzhi[1] not in BRANCHES:
        raise ValueError(f"{field} 必須是有效出生年干支，例如甲子")
    return ganzhi


def _visible_stem_palace(board: QimenBoard, stem: str) -> tuple[int, str]:
    if stem == "甲":
        return (
            board.chief_star_palace,
            "PROJECT_CONVENTION__HIDDEN_JIA_USES_CURRENT_CHIEF_STAR_PALACE__NOT_SOURCE_LOCKED_FOR_YEAR_LIFE",
        )
    for number, state in board.palaces.items():
        if stem in state.heaven_stems:
            return number, "VISIBLE_BIRTH_YEAR_STEM_ON_CURRENT_HEAVEN_PLATE"
    raise ValueError(f"天盤找不到年命干：{stem}")


def _participant_snapshot(board: QimenBoard, label: str, birth_ganzhi: str) -> dict[str, Any]:
    year_stem = birth_ganzhi[0]
    year_branch = birth_ganzhi[1]
    palace_number, placement_source_status = _visible_stem_palace(board, year_stem)
    palace = board.palaces[palace_number]
    return {
        "label": label,
        "birth_year_ganzhi": birth_ganzhi,
        "year_stem": year_stem,
        "year_branch": year_branch,
        "placement_basis": "BIRTH_YEAR_STEM_ON_HEAVEN_PLATE__BRANCH_RETAINED_FOR_IDENTITY_ONLY",
        "placement_source_status": placement_source_status,
        "palace": palace_number,
        "palace_name": palace.name,
        "palace_element": palace.element,
        "heaven_stems": list(palace.heaven_stems),
        "earth_stem": palace.earth_stem,
        "earth_hidden_stems": list(palace.earth_hidden_stems),
        "stars": list(palace.stars),
        "door": palace.door,
        "deity": palace.deity,
        "is_void": palace.is_void,
        "is_horse": palace.is_horse,
        "patterns": [
            {
                "name": hit.name,
                "category": hit.category,
                "condition": hit.condition,
            }
            for hit in board.patterns
            if hit.palace == palace_number
        ],
    }


def _participant_relation(home_element: str, away_element: str) -> dict[str, str]:
    if home_element == away_element:
        return {"code": "SAME_ELEMENT", "label": "比和"}
    if ELEMENT_GENERATES[home_element] == away_element:
        return {"code": "HOME_GENERATES_AWAY", "label": "A生B"}
    if ELEMENT_GENERATES[away_element] == home_element:
        return {"code": "AWAY_GENERATES_HOME", "label": "B生A"}
    if ELEMENT_CONTROLS[home_element] == away_element:
        return {"code": "HOME_CONTROLS_AWAY", "label": "A克B"}
    if ELEMENT_CONTROLS[away_element] == home_element:
        return {"code": "AWAY_CONTROLS_HOME", "label": "B克A"}
    raise AssertionError("五行關係不完整")


def build_qimen_coach_participant_layer(
    board: QimenBoard,
    coach_identity: dict[str, Any],
) -> dict[str, Any]:
    """Map coaches' birth-year ganzhi into the current Qimen chart.

    Using a person's year-life/year-stem palace has classical precedent. Treating
    the football head coach as the match actor is explicitly a project adaptation.
    """

    home_ganzhi = _validate_ganzhi(
        coach_identity.get("home_birth_ganzhi", ""), "home_birth_ganzhi"
    )
    away_ganzhi = _validate_ganzhi(
        coach_identity.get("away_birth_ganzhi", ""), "away_birth_ganzhi"
    )
    home = _participant_snapshot(board, "A_HOME_COACH", home_ganzhi)
    away = _participant_snapshot(board, "B_AWAY_COACH", away_ganzhi)
    identity = {
        "home_birth_ganzhi": home_ganzhi,
        "away_birth_ganzhi": away_ganzhi,
    }
    participant_signature = sha256_payload(identity)

    payload = {
        "schema_version": QIMEN_PARTICIPANT_LAYER_VERSION,
        "status": "READY",
        "authority": "PROJECT_ADAPTATION__COACH_AS_MATCH_ACTOR",
        "classical_basis": (
            "奇門古法可將本人年命／年干與正時盤合參；本 V1 實作只使用出生年干定位天盤宮。"
            "出生年支保留於 identity 供稽核，尚未參與落宮；把主教練視為足球賽事 actor 是 JARVIS 現代移植。"
        ),
        "method_boundary": (
            "QIMEN_PARTICIPANT_LAYER_V1 不等同完整古法年命演算法：目前 placement 只取出生年干，"
            "年支未用於宮位計算；若年干為甲，暫沿用 current chief-star palace 作隱甲 project convention，"
            "此甲處理尚未 source-lock，因此不得宣稱 full Ganzhi year-life palace 已完成。"
        ),
        "identity": identity,
        "participant_signature_sha256": participant_signature,
        "home": home,
        "away": away,
        "home_away_palace_relation": _participant_relation(
            str(home["palace_element"]), str(away["palace_element"])
        ),
        "anti_backfill": [
            "教練身份與出生年干支必須在賽前凍結。",
            "換帥時 participant identity 應改變，但不得回看結果後選用前任或代理教練。",
            "年命層只描述雙方承盤差異，不直接轉成固定比分或勝率。",
            "V1 只以出生年干定位；不得把保存的年支描述成已參與落宮。",
        ],
    }
    payload["resolved_layer_sha256"] = sha256_payload(payload)
    return payload


def empty_participant_layer() -> dict[str, Any]:
    return {
        "schema_version": QIMEN_PARTICIPANT_LAYER_VERSION,
        "status": "NOT_PROVIDED",
        "authority": "PROJECT_ADAPTATION__COACH_AS_MATCH_ACTOR",
        "rule": "未提供雙方主教練出生年干支，不得虛構 participant differentiation。",
    }


def build_temporal_signature(
    qimen_packet: dict[str, Any],
    meihua_packet: dict[str, Any],
    yuanling_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    q_event = qimen_packet.get("event") or {}
    m_event = meihua_packet.get("event") or {}
    y_event = (yuanling_packet or {}).get("event") or {}
    y_review = (yuanling_packet or {}).get("qiyao_review") or {}
    temporal_payload = {
        "qimen_event": {
            "datetime": q_event.get("datetime"),
            "timezone": q_event.get("timezone"),
        },
        "meihua_event": {
            "datetime": m_event.get("datetime"),
            "timezone": m_event.get("timezone"),
        },
        "qimen_chart": qimen_packet.get("chart"),
        "meihua_temporal_hexagram": meihua_packet.get("hexagram"),
        "yuanling_temporal": (
            {
                "event": {
                    "datetime": y_event.get("datetime"),
                    "timezone": y_event.get("timezone"),
                },
                "qiyao_event": y_review.get("event"),
                "collateral_reconstruction": y_review.get("collateral_reconstruction"),
                "star_role_resolution": y_review.get("star_role_resolution"),
            }
            if yuanling_packet is not None
            else None
        ),
    }
    return {
        "status": "READY",
        "temporal_signature_sha256": sha256_payload(temporal_payload),
        "rule": (
            "此 signature 僅代表共同時間盤／年月日時卦，以及有提供時的元靈 deterministic temporal reconstruction；"
            "不同 fixture 可以相同，因此不得單靠它製造不同賽果。"
        ),
    }


def build_differentiation_audit(
    qimen_packet: dict[str, Any],
    meihua_packet: dict[str, Any],
    yuanling_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    temporal = build_temporal_signature(qimen_packet, meihua_packet, yuanling_packet)
    q_event = qimen_packet.get("event_identity_layer") or empty_event_identity_layer()
    m_event = meihua_packet.get("event_identity_layer") or empty_event_identity_layer()

    q_sig = q_event.get("event_signature_sha256")
    m_sig = m_event.get("event_signature_sha256")
    if q_sig or m_sig:
        if not q_sig or not m_sig or q_sig != m_sig:
            raise ValueError("CASE_ALIGNMENT_FAIL: EVENT_IDENTITY_LAYER_MISMATCH")
        event_status = "READY"
        event_signature = q_sig
    else:
        event_status = "NOT_PROVIDED"
        event_signature = None

    participant = qimen_packet.get("participant_layer") or empty_participant_layer()
    participant_ready = participant.get("status") == "READY"

    if event_status == "READY" and participant_ready:
        status = "EVENT_AND_PARTICIPANT_READY"
    elif event_status == "READY":
        status = "EVENT_READY__PARTICIPANT_MISSING"
    else:
        status = "TEMPORAL_ONLY__UNSAFE_FOR_CROSS_FIXTURE_DIFFERENTIATION"

    return {
        "schema_version": FOOTBALL_DIFFERENTIATION_AUDIT_VERSION,
        "status": status,
        "temporal": temporal,
        "event": {
            "status": event_status,
            "event_signature_sha256": event_signature,
            "method": MEIHUA_EVENT_IDENTITY_VERSION if event_status == "READY" else None,
        },
        "participant": {
            "status": participant.get("status"),
            "participant_signature_sha256": participant.get(
                "participant_signature_sha256"
            ),
            "authority": participant.get("authority"),
        },
        "collision_gate_rule": (
            "若兩個 case 的 temporal signature 相同但 event signature 不同，"
            "任何不同結論必須明示來自 event/participant layer；"
            "禁止只用 temporal layer 對同時不同 fixture 輸出不同結果。"
        ),
    }


def audit_case_collision(
    left_bundle: dict[str, Any],
    right_bundle: dict[str, Any],
) -> dict[str, Any]:
    left = left_bundle.get("differentiation_audit") or {}
    right = right_bundle.get("differentiation_audit") or {}
    left_temporal = (left.get("temporal") or {}).get("temporal_signature_sha256")
    right_temporal = (right.get("temporal") or {}).get("temporal_signature_sha256")
    left_event = (left.get("event") or {}).get("event_signature_sha256")
    right_event = (right.get("event") or {}).get("event_signature_sha256")

    same_temporal = bool(left_temporal) and left_temporal == right_temporal
    same_event = bool(left_event) and left_event == right_event

    if not same_temporal:
        status = "NO_TEMPORAL_COLLISION"
    elif same_event:
        status = "SAME_TEMPORAL_AND_EVENT_IDENTITY"
    elif left_event and right_event:
        status = "TEMPORAL_COLLISION__DISTINGUISHED_BY_EVENT_LAYER"
    else:
        status = "UNSAFE_TEMPORAL_COLLISION__EVENT_IDENTITY_MISSING"

    return {
        "schema_version": FOOTBALL_COLLISION_AUDIT_VERSION,
        "status": status,
        "same_temporal_signature": same_temporal,
        "same_event_signature": same_event,
        "left_temporal_signature": left_temporal,
        "right_temporal_signature": right_temporal,
        "left_event_signature": left_event,
        "right_event_signature": right_event,
        "rule": (
            "相同 temporal input 不得靠解讀任意分叉；只有賽前固定且可重現的 "
            "event/participant input 才能提供跨 fixture differentiation。"
        ),
    }
