from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from meihua.engine import MeihuaSnapshot


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "knowledge" / "meihua_classical_method_audit.json"


@lru_cache(maxsize=1)
def _policy() -> dict[str, Any]:
    if not POLICY_PATH.exists():
        raise RuntimeError("缺少 knowledge/meihua_classical_method_audit.json")
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def meihua_classical_method_policy() -> dict[str, Any]:
    """Return the frozen JARVIS policy used to classify Meihua casting methods."""

    return _policy()


def build_meihua_classical_method_audit(snapshot: MeihuaSnapshot) -> dict[str, Any]:
    """Build a method-aware audit without changing the deterministic cast."""

    policy = _policy()
    engine = policy["current_engine_contract"]
    method_class = str(engine["method_class"])
    profile = policy["method_profiles"][method_class]

    body_is_upper = snapshot.body_trigram == snapshot.upper_trigram
    upper_identity = "body_mutual" if body_is_upper else "use_mutual"
    lower_identity = "use_mutual" if body_is_upper else "body_mutual"

    relation_network = [
        {
            "layer": "original_use",
            "classical_identity": "original_use",
            "relative_stage": "immediate",
            "source_position": "original_use",
            "trigram": snapshot.use_trigram,
            "relation_to_body": snapshot.body_use_relation,
            "role": "本卦用層；目前最直接作用於體。",
        },
        {
            "layer": "mutual_upper",
            "classical_identity": upper_identity,
            "relative_stage": "middle",
            "source_position": "upper",
            "trigram": snapshot.mutual_upper_trigram,
            "relation_to_body": snapshot.mutual_upper_relation_to_body,
            "role": (
                "互卦上層；依本卦體位判為體互。體互在互層中優先審查。"
                if upper_identity == "body_mutual"
                else "互卦上層；依本卦體位判為用互。用互次於體互審查。"
            ),
        },
        {
            "layer": "mutual_lower",
            "classical_identity": lower_identity,
            "relative_stage": "middle",
            "source_position": "lower",
            "trigram": snapshot.mutual_lower_trigram,
            "relation_to_body": snapshot.mutual_lower_relation_to_body,
            "role": (
                "互卦下層；依本卦體位判為體互。體互在互層中優先審查。"
                if lower_identity == "body_mutual"
                else "互卦下層；依本卦體位判為用互。用互次於體互審查。"
            ),
        },
        {
            "layer": "changed_use",
            "classical_identity": "changed_use",
            "relative_stage": "late",
            "source_position": "changed_use",
            "trigram": snapshot.changed_use_trigram,
            "relation_to_body": snapshot.changed_use_relation_to_body,
            "role": "變卦用層；作轉折後／較後段作用。",
        },
    ]

    return {
        "kind": "meihua_classical_method_audit",
        "schema_version": policy["schema_version"],
        "status": "METHOD_AWARE_REVIEW_READY",
        "method": {
            "name": engine["method"],
            "class": method_class,
            "profile_name": profile["name"],
            "implementation_status": profile["status"],
            "classification_rule": profile["classification_rule"],
        },
        "weighting_decision": {
            "zhouyi_role": profile["zhouyi_role"],
            "zhouyi_rule": profile["zhouyi_rule"],
            "primary_review_order": list(profile["primary_review_order"]),
            "body_use_rule": profile["body_use_rule"],
            "time_layer_rule": profile["time_layer_rule"],
        },
        "body_use_network": {
            "body_trigram": snapshot.body_trigram,
            "body_season_state": snapshot.body_season_state,
            "body_position": "upper" if body_is_upper else "lower",
            "body_mutual_source_position": "upper" if body_is_upper else "lower",
            "use_mutual_source_position": "lower" if body_is_upper else "upper",
            "mutual_priority_rule": "體互最緊，用互次之；同時保留互卦原始 upper/lower 位置以便稽核。",
            "layers": relation_network,
            "rule": "體用、生克與旺衰必須連讀；不得只取單一 relation 作最後結論。",
        },
        "external_response_audit": {
            "three_essentials": "NOT_RECORDED",
            "ten_responses": "NOT_RECORDED",
            "external_omens": "NOT_RECORDED",
            "source_lock": "NOT_AVAILABLE_IN_CURRENT_UI",
            "rule": profile["external_response_rule"],
            "anti_backfill": "不得用賽後或事後才知道的事件補造成起卦當時外應。",
        },
        "classical_principles": list(policy["core_classical_principles"]),
        "source_ids": list(policy["source_ids"]),
        "unimplemented_classical_layers": list(engine["unimplemented_classical_layers"]),
        "completion_note": engine["completion_note"],
        "boundary": (
            "此 audit 只決定方法分類與解讀權重，不改變 deterministic 本卦、互卦、變卦、動爻或體用；"
            "工程分類與 football modern application 不冒充《梅花易數》原文。"
        ),
    }
