from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "knowledge" / "divination_review_framework.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"divination review validation failed: {message}")


def main() -> None:
    payload = json.loads(PATH.read_text(encoding="utf-8"))
    require(payload.get("schema_version") == "stark-divination-review-framework-v1.0.0", "unexpected schema version")
    dimensions = payload.get("review_dimensions", [])
    require(len(dimensions) >= 12, "review framework must contain at least 12 dimensions")
    ids = [row.get("id") for row in dimensions]
    require(len(ids) == len(set(ids)), "review dimension ids must be unique")
    required_dimensions = {
        "source_integrity",
        "cast_integrity",
        "text_condition",
        "symbol_structure",
        "stage_timing",
        "meaning_depth",
        "cross_system_coherence",
        "football_translation",
        "contradiction_register",
        "uncertainty_register",
        "overreach_guard",
        "handoff_quality",
    }
    require(required_dimensions <= set(ids), "required review dimensions are incomplete")
    for row in dimensions:
        require(bool(row.get("name")), f"{row.get('id')} missing name")
        require(bool(row.get("question")), f"{row.get('id')} missing audit question")
        require(bool(row.get("required")), f"{row.get('id')} missing required fields")

    emphasis = payload.get("system_emphasis", {})
    require(set(emphasis) == {"ZHOUYI", "MEIHUA_YISHU", "JIAOSHI_YILIN", "QIMEN_DUNJIA"}, "system emphasis must cover four systems")
    for system, rows in emphasis.items():
        require(bool(rows), f"{system} needs review emphasis")
        require(set(rows) <= set(ids), f"{system} references unknown review dimensions")

    football = payload.get("football_contract", {})
    require(football.get("status") == "MODERN_APPLICATION__NOT_CLASSICAL_FORMULA", "football status boundary missing")
    required_football = {
        "source_basis",
        "abstract_meaning",
        "possible_scenario",
        "observable_signals",
        "counter_signals",
        "confidence_note",
    }
    require(required_football <= set(football.get("required_fields", [])), "football meaning contract incomplete")
    require("automatic_win_probability" in football.get("forbidden_outputs", []), "win-probability shortcut must be forbidden")
    require(bool(payload.get("completion_rule")), "completion rule is required")

    print("divination review validation passed: 12+ review dimensions / 4 systems / football evidence+counterevidence contract")


if __name__ == "__main__":
    main()
