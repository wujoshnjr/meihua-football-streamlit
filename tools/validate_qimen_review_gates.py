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
    fixtures = json.loads((KNOWLEDGE / "qimen_source_golden_fixtures.json").read_text(encoding="utf-8"))
    extended = json.loads((KNOWLEDGE / "qimen_extended_review_policy.json").read_text(encoding="utf-8"))

    require(golden.get("schema_version") == "stark-qimen-golden-fixture-policy-v1.1.0", "golden schema drift")
    classes = set(golden.get("fixture_classes", {}))
    require(
        classes == {"SOURCE_DERIVED_METHOD_GOLDEN", "END_TO_END_EXTERNAL_CHART", "INTERNAL_REGRESSION"},
        "fixture classes incomplete",
    )
    source_count = int(golden.get("current_counts", {}).get("source_derived_method_golden", -1))
    end_to_end_count = int(golden.get("current_counts", {}).get("end_to_end_external_chart", -1))
    gate = golden.get("release_gate", {})
    require(source_count == len(fixtures.get("fixtures", [])) == 4, "source-derived golden count must be exactly four")
    require(gate.get("issue_62_qimen_golden_complete") is True, "Issue #62 reconstructable golden gate must be complete")
    require(gate.get("full_end_to_end_engine_certified") is False, "must not overclaim full end-to-end certification")
    require(end_to_end_count == 0, "end-to-end external chart count is expected to remain explicitly zero in 10.2")
    require(
        golden["fixture_classes"]["SOURCE_DERIVED_METHOD_GOLDEN"]["counts_toward_full_end_to_end_engine_certification"] is False,
        "source-derived fixtures must not masquerade as end-to-end certification",
    )
    require(
        golden["fixture_classes"]["END_TO_END_EXTERNAL_CHART"]["counts_toward_full_end_to_end_engine_certification"] is True,
        "end-to-end class must remain the stronger certification class",
    )

    require(extended.get("schema_version") == "stark-qimen-extended-review-policy-v1.1.0", "extended schema drift")
    require(extended.get("status") == "MATERIALIZED_WITH_PROJECT_AUTHORITY", "extended relation materialization incomplete")
    families = extended.get("materialized_extended_families", [])
    ids = {row.get("id") for row in families}
    require(
        {"deity_x_door", "deity_x_star", "deity_x_palace", "stem_x_door", "stem_x_star", "state_modifier_stack"} <= ids,
        "extended families incomplete",
    )
    require(extended.get("static_materialized_count") == 378, "static extended relation count must be 378")
    contract = extended.get("materialization_contract", {})
    require(contract.get("authority") == "PROJECT_HEURISTIC__COMPONENTS_SOURCE_BACKED", "extended authority boundary drift")
    forbidden = set(contract.get("forbidden", []))
    require("automatic_win_probability" in forbidden, "automatic probability shortcut must stay forbidden")
    require("fixed_score_from_relation" in forbidden, "fixed-score shortcut must stay forbidden")
    require("postmatch_backfill" in forbidden, "postmatch backfill must stay forbidden")

    print(
        "Qimen review gates: PASS | "
        f"source-derived-golden={source_count} | issue62-golden={gate['issue_62_qimen_golden_complete']} | "
        f"full-end-to-end-certified={gate['full_end_to_end_engine_certified']} | extended-static=378"
    )


if __name__ == "__main__":
    main()
