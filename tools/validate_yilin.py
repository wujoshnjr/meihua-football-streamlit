from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jarvis.yilin import yilin_entries, yilin_image_ontology, yilin_manifest  # noqa: E402


EXPECTED_HEXAGRAMS = 64
EXPECTED_PAIRS = 4096


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"yilin validation failed: {message}")


def main() -> None:
    manifest = yilin_manifest()
    rows = yilin_entries()
    atoms = yilin_image_ontology()

    require(manifest.get("expected_from_hexagrams") == EXPECTED_HEXAGRAMS, "expected from hexagrams must be 64")
    require(manifest.get("expected_to_hexagrams_per_from") == EXPECTED_HEXAGRAMS, "expected targets per from must be 64")
    require(manifest.get("expected_pairs") == EXPECTED_PAIRS, "expected pairs must be 4096")
    require(manifest.get("bridge_mode") == "MEIHUA_YILIN_BRIDGE", "bridge mode must stay explicit")
    require(bool(manifest.get("historical_method_notice")), "historical method notice is required")
    require(bool(manifest.get("authority_order")), "authority order is required")

    pair_keys = {(row.get("from_name"), row.get("to_name")) for row in rows}
    require(len(pair_keys) == len(rows), "from/to pairs must be unique")
    require(len(rows) == manifest.get("materialized_pairs"), "manifest materialized_pairs must match files")
    require(len(rows) <= EXPECTED_PAIRS, "materialized pairs cannot exceed 4096")

    from_names = {str(row.get("from_name")) for row in rows}
    require(sorted(from_names) == sorted(manifest.get("materialized_from_hexagrams", [])), "manifest from-hexagram list mismatch")

    for from_name in from_names:
        block = [row for row in rows if row.get("from_name") == from_name]
        require(len(block) == 64, f"{from_name} block must be materialized as a complete 64-entry unit")
        require({row.get("to_number") for row in block} == set(range(1, 65)), f"{from_name} target numbers must be exactly 1..64")
        require(len({row.get("to_name") for row in block}) == 64, f"{from_name} target names must be unique")

    for row in rows:
        for field in (
            "id",
            "from_number",
            "from_name",
            "from_symbol",
            "to_number",
            "to_name",
            "to_symbol",
            "classical_text",
            "source_id",
            "verification_status",
            "variant_status",
            "semantic_status",
        ):
            require(row.get(field) not in (None, ""), f"{row.get('id')} missing {field}")
        require(row.get("variant_status") in {"PENDING_CROSSCHECK", "CROSSCHECKED", "VARIANT_RECORDED"}, f"{row.get('id')} invalid variant status")
        require("home_win_probability" not in json.dumps(row, ensure_ascii=False), f"{row.get('id')} must not contain model probability")
        require("fixed_score" not in json.dumps(row, ensure_ascii=False), f"{row.get('id')} must not contain fixed score")

    require(atoms, "image ontology cannot be empty")
    for atom in atoms:
        for field in ("id", "name", "match_terms", "classical_abstraction", "football", "observable_signals", "counter_signals"):
            require(atom.get(field), f"image atom {atom.get('id')} missing {field}")

    if len(rows) < EXPECTED_PAIRS:
        require(
            manifest.get("catalog_status") == "PARTIAL_BUILD__DO_NOT_CLAIM_4096_COMPLETE",
            "partial catalog must explicitly reject completeness claims",
        )
    else:
        require(len(from_names) == 64, "complete catalog must contain 64 source hexagrams")

    print(
        "yilin validation passed: "
        f"{len(rows)}/{EXPECTED_PAIRS} pairs, {len(from_names)}/64 complete source blocks, {len(atoms)} image atoms"
    )


if __name__ == "__main__":
    main()
