"""One explicit active handoff, with session-only per-system working copies."""
from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from jarvis.validation import validate_bundle, validate_packet

ACTIVE_KEY = "stark_active_artifact"


def activate_packet(state: MutableMapping[str, Any], packet: dict) -> None:
    validate_packet(packet)
    state["stark_packet"] = packet
    state["stark_packet_system"] = packet["system"]
    if packet["system"] == "YUANLING_YANSHU_QIYAO":
        state["stark_yuanling_packet"] = packet
    state[ACTIVE_KEY] = {"kind": "packet", "key": "stark_packet", "sha256": packet["packet_sha256"]}


def activate_bundle(state: MutableMapping[str, Any], bundle: dict) -> None:
    validate_bundle(bundle)
    state["stark_case_bundle"] = bundle
    for name in ("qimen", "meihua", "yuanling"):
        state[f"stark_{name}_packet"] = bundle.get(f"{name}_packet")
    state[ACTIVE_KEY] = {"kind": "bundle", "key": "stark_case_bundle", "sha256": bundle["bundle_sha256"]}


def active_artifact(state: MutableMapping[str, Any]) -> tuple[str, dict] | None:
    selection = state.get(ACTIVE_KEY)
    if not selection:
        # Legacy sessions may contain several different artifacts. Never guess.
        present = [(kind, state.get(key)) for kind, key in (
            ("bundle", "stark_case_bundle"), ("packet", "stark_packet")
        ) if state.get(key)]
        if len(present) > 1:
            raise ValueError("有多份舊工作資料，請從起卦或足球案件頁重新建立目前交付項目。")
        if not present:
            return None
        kind, payload = present[0]
    else:
        if selection.get("kind") not in {"packet", "bundle"}:
            raise ValueError("目前交付項目類型無效")
        kind = selection["kind"]
        key = "stark_case_bundle" if kind == "bundle" else "stark_packet"
        if selection.get("key") != key:
            raise ValueError("目前交付項目位置不一致")
        payload = state.get(key)
        digest_key = "bundle_sha256" if kind == "bundle" else "packet_sha256"
        if not isinstance(payload, dict) or payload.get(digest_key) != selection.get("sha256"):
            raise ValueError("目前交付項目已變更，請重新建立。")
    (validate_bundle if kind == "bundle" else validate_packet)(payload)
    return kind, payload
