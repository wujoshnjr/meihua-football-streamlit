from __future__ import annotations

from typing import Any

from casting_structure import build_casting_structure
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
        "casting": result.to_dict(),
        "jiaoshi_yilin": build_jiaoshi_yilin_reference(
            result.main_hexagram,
            result.changed_hexagram,
        ),
    }
    payload.update(build_casting_structure(result))
    return payload


def build_stored_casting_payload(result: HexagramResult) -> dict[str, Any]:
    """Add the Yi Lin entry while retaining the historical flat result shape."""

    payload = result.to_dict()
    payload["jiaoshi_yilin"] = build_jiaoshi_yilin_reference(
        result.main_hexagram,
        result.changed_hexagram,
    )
    payload.update(build_casting_structure(result))
    return payload


__all__ = ["build_casting_export", "build_stored_casting_payload"]
