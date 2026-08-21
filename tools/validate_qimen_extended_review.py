from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jarvis.qimen_extended_relations import all_extended_relations, extended_relation_audit  # noqa: E402


POLICY = ROOT / "knowledge" / "qimen_extended_review_policy.json"
FORBIDDEN_KEYS = {
    "automatic_win_probability",
    "win_probability",
    "home_win_probability",
    "away_win_probability",
    "fixed_score",
    "predicted_score",
    "single_relation_final_result",
    "final_result",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"Qimen extended review validation failed: {message}")


def _keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _keys(child)


def main() -> None:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    rows = all_extended_relations()
    audit = extended_relation_audit()

    expected = {
        "deity_x_door": 64,
        "deity_x_star": 72,
        "deity_x_palace": 72,
        "stem_x_door": 80,
        "stem_x_star": 90,
    }
    require(policy.get("status") == "MATERIALIZED_WITH_PROJECT_AUTHORITY", "policy must declare materialized state")
    require(audit["families"] == expected, f"family counts drift: {audit['families']}")
    require(audit["total"] == 378, "static extended relation count must be 378")
    require(audit["unique_keys"] == 378, "extended relation keys must be unique")
    require(audit["authority"] == "PROJECT_HEURISTIC__COMPONENTS_SOURCE_BACKED", "authority boundary drift")

    required_fields = set(policy["materialization_contract"]["required_fields"])
    for row in rows:
        missing = [field for field in required_fields if not row.get(field)]
        require(not missing, f"{row.get('key')} missing {missing}")
        football = row["football_modern_application"]
        for field in (
            "source_basis",
            "abstract_meaning",
            "possible_scenario",
            "observable_signals",
            "counter_signals",
            "confidence_note",
        ):
            require(football.get(field), f"{row['key']} missing football.{field}")
        present = set(_keys(row))
        require(not (present & FORBIDDEN_KEYS), f"{row['key']} contains forbidden result keys")

    print(
        "Qimen extended review validation passed: "
        "378 static relations (64 deity×door / 72 deity×star / 72 deity×palace / 80 stem×door / 90 stem×star) "
        "+ runtime modifier stack; project-authority boundary preserved"
    )


if __name__ == "__main__":
    main()
