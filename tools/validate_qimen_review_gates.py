from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"Qimen review gate validation failed: {message}")


def main() -> None:
    golden = json.loads((KNOWLEDGE / "qimen_golden_fixture_policy.json").read_text(encoding="utf-8"))
    extended = json.loads((KNOWLEDGE / "qimen_extended_review_policy.json").read_text(encoding="utf-8"))

    require(golden.get("schema_version") == "stark-qimen-golden-fixture-policy-v1.0.0", "golden schema drift")
    require(set(golden.get("fixture_classes", {})) == {"EXTERNAL_GOLDEN", "INTERNAL_REGRESSION"}, "fixture classes incomplete")
    require(golden["fixture_classes"]["EXTERNAL_GOLDEN"]["counts_toward_engine_correctness"] is True, "external golden must count")
    require(golden["fixture_classes"]["INTERNAL_REGRESSION"]["counts_toward_engine_correctness"] is False, "internal regression must not count as correctness proof")
    external_count = int(golden.get("current_counts", {}).get("external_golden", -1))
    gate_complete = bool(golden.get("release_gate", {}).get("issue_62_qimen_golden_complete"))
    require(external_count >= 0, "external golden count invalid")
    if external_count == 0:
        require(gate_complete is False, "must not mark golden gate complete with zero external fixtures")
    require(len(golden.get("required_external_coverage", [])) >= 7, "external golden coverage contract too shallow")

    require(extended.get("schema_version") == "stark-qimen-extended-review-policy-v1.0.0", "extended schema drift")
    require(extended.get("status") == "DESIGN_READY__RELATIONS_NOT_MATERIALIZED", "extended status must remain honest")
    families = extended.get("planned_extended_families", [])
    ids = {row.get("id") for row in families}
    require({"deity_x_door", "deity_x_star", "deity_x_palace", "stem_x_door", "stem_x_star", "state_modifier_stack"} <= ids, "extended families incomplete")
    contract = extended.get("materialization_contract", {})
    require(bool(contract.get("required_fields")), "extended materialization required fields missing")
    forbidden = set(contract.get("forbidden", []))
    require("automatic_win_probability" in forbidden, "automatic probability shortcut must stay forbidden")
    require("fixed_score_from_relation" in forbidden, "fixed-score shortcut must stay forbidden")

    print(
        "Qimen review gates: PASS | "
        f"external_golden={external_count} (completion={gate_complete}) | extended_families={len(families)}"
    )


if __name__ == "__main__":
    main()
