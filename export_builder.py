from __future__ import annotations

from typing import Any

from casting_structure import build_casting_structure
from input_protocol import build_input_protocol_audit
from knowledge_loader import build_jiaoshi_yilin_reference
from models import CastingInput, HexagramResult
from version import APP_VERSION, KNOWLEDGE_VERSION, SCHEMA_VERSION


def build_casting_export(casting: CastingInput, result: HexagramResult) -> dict[str, Any]:
    """Build the complete downloadable JSON payload for one casting."""

    payload = {
        "schema_version": SCHEMA_VERSION,
        "system_version": APP_VERSION,
        "knowledge_version": KNOWLEDGE_VERSION,
        "input": casting.to_dict(),
        "input_protocol": build_input_protocol_audit(
            casting.body_name,
            casting.use_name,
            casting.body_text,
            casting.use_text,
            casting.full_text,
        ),
        "casting": result.to_dict(),
        "jiaoshi_yilin": build_jiaoshi_yilin_reference(
            result.main_hexagram,
            result.changed_hexagram,
        ),
    }
    payload.update(build_casting_structure(result))
    return payload


def build_stored_casting_payload(casting: CastingInput, result: HexagramResult) -> dict[str, Any]:
    """Add the Yi Lin entry while retaining the historical flat result shape."""

    payload = result.to_dict()
    payload["input"] = casting.to_dict()
    payload["input_protocol"] = build_input_protocol_audit(
        casting.body_name,
        casting.use_name,
        casting.body_text,
        casting.use_text,
        casting.full_text,
    )
    payload["jiaoshi_yilin"] = build_jiaoshi_yilin_reference(
        result.main_hexagram,
        result.changed_hexagram,
    )
    payload.update(build_casting_structure(result))
    return payload


__all__ = ["build_casting_export", "build_stored_casting_payload"]
