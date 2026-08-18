from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jarvis.yilin import yilin_entries, yilin_image_ontology, yilin_manifest  # noqa: E402


EXPECTED_HEXAGRAMS = 64
EXPECTED_PAIRS = 4096
EXPECTED_UPSTREAM_REPO = "kanripo/KR3g0029"
EXPECTED_UPSTREAM_COMMIT = "764e995ce74aa249081918ca1b0c23bbca62bec8"
SNAPSHOT_PATH = ROOT / "knowledge" / "yilin" / "source_snapshot.json"


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

    require(len(rows) == EXPECTED_PAIRS, f"stable corpus must contain exactly {EXPECTED_PAIRS} entries")
    number_pairs = {(int(row["from_number"]), int(row["to_number"])) for row in rows}
    name_pairs = {(str(row["from_name"]), str(row["to_name"])) for row in rows}
    require(len(number_pairs) == EXPECTED_PAIRS, "numeric from/to pairs must be unique")
    require(len(name_pairs) == EXPECTED_PAIRS, "canonical-name from/to pairs must be unique")
    expected_matrix = {(left, right) for left in range(1, 65) for right in range(1, 65)}
    require(number_pairs == expected_matrix, "numeric matrix must be exactly 64×64")

    require(manifest.get("materialized_pairs") == EXPECTED_PAIRS, "manifest materialized_pairs must be 4096")
    require(manifest.get("complete_from_hexagrams") == 64, "manifest complete source blocks must be 64")
    require(
        manifest.get("catalog_status") == "COMPLETE_4096_PAIR_COVERAGE__TEXTUAL_COLLATION_ONGOING",
        "catalog status must distinguish pair completeness from textual collation",
    )
    require(
        manifest.get("textual_collation_status") == "WYG_BASE_COMPLETE__MULTI_EDITION_VARIANT_COLLATION_ONGOING",
        "textual collation must remain explicitly ongoing",
    )

    from_names = {str(row["from_name"]) for row in rows}
    require(len(from_names) == 64, "must contain 64 canonical source hexagram names")
    require(
        sorted(from_names) == sorted(manifest.get("materialized_from_hexagrams", [])),
        "manifest from-hexagram list mismatch",
    )

    for from_number in range(1, 65):
        block = [row for row in rows if int(row["from_number"]) == from_number]
        require(len(block) == 64, f"source #{from_number} must contain exactly 64 targets")
        require({int(row["to_number"]) for row in block} == set(range(1, 65)), f"source #{from_number} targets must be 1..64")

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
            "transcription_raw",
            "source_id",
            "source_section",
            "source_file",
            "source_edition",
            "source_repo",
            "source_commit",
            "source_volume_file",
            "source_page_start",
            "verification_status",
            "variant_status",
            "semantic_status",
        ):
            require(row.get(field) not in (None, ""), f"{row.get('id')} missing {field}")
        require(isinstance(row.get("editorial_notes"), list), f"{row['id']} editorial_notes must be a list")
        require(isinstance(row.get("gaiji_tokens"), list), f"{row['id']} gaiji_tokens must be a list")
        require(isinstance(row.get("source_label_order_anomaly"), bool), f"{row['id']} anomaly flag must be bool")
        require(row["source_repo"] == EXPECTED_UPSTREAM_REPO, f"{row['id']} unexpected source repo")
        require(row["source_commit"] == EXPECTED_UPSTREAM_COMMIT, f"{row['id']} unexpected source commit")
        require(row["verification_status"] == "WYG_DIGITAL_TRANSCRIPTION__PAIR_COMPLETE", f"{row['id']} invalid verification status")
        require(
            row["variant_status"] == "EDITORIAL_APPARATUS_PRESERVED__MULTI_EDITION_COLLATION_ONGOING",
            f"{row['id']} invalid variant status",
        )
        require(
            row["semantic_status"] == "RAW_CLASSICAL_TEXT__PROJECT_HEURISTICS_SEPARATE",
            f"{row['id']} invalid semantic status",
        )
        for token in row["gaiji_tokens"]:
            require(token in row["transcription_raw"], f"{row['id']} gaiji token missing from raw transcription")
        serialized = json.dumps(row, ensure_ascii=False)
        require("home_win_probability" not in serialized, f"{row['id']} must not contain model probability")
        require("fixed_score" not in serialized, f"{row['id']} must not contain fixed score")

    require(SNAPSHOT_PATH.exists(), "source_snapshot.json must exist")
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    require(snapshot.get("upstream_repository") == EXPECTED_UPSTREAM_REPO, "snapshot repo mismatch")
    require(snapshot.get("upstream_commit") == EXPECTED_UPSTREAM_COMMIT, "snapshot commit mismatch")
    require(snapshot.get("parsed_from_hexagrams") == 64, "snapshot must report 64 source blocks")
    require(snapshot.get("parsed_pairs") == 4096, "snapshot must report 4096 pairs")
    files = snapshot.get("files", [])
    require(len(files) == 4, "snapshot must pin four source volume files")
    require(all(item.get("name") and item.get("sha256") and len(item["sha256"]) == 64 for item in files), "source file SHA-256 metadata invalid")
    anomalies = snapshot.get("source_label_anomalies", [])
    require(len(anomalies) == manifest.get("source_label_anomaly_count"), "source-label anomaly count mismatch")

    source = manifest.get("transcription_source", {})
    require(source.get("repository") == EXPECTED_UPSTREAM_REPO, "manifest source repo mismatch")
    require(source.get("commit") == EXPECTED_UPSTREAM_COMMIT, "manifest source commit mismatch")
    require(len(source.get("sha256", {})) == 4, "manifest must pin SHA-256 for four source files")

    require(atoms, "image ontology cannot be empty")
    ids: set[str] = set()
    for atom in atoms:
        for field in ("id", "name", "match_terms", "classical_abstraction", "football", "observable_signals", "counter_signals"):
            require(atom.get(field), f"image atom {atom.get('id')} missing {field}")
        require(atom["id"] not in ids, f"duplicate image atom id: {atom['id']}")
        ids.add(atom["id"])

    print(
        "yilin validation passed: "
        f"4096/4096 pairs, 64/64 source blocks, {len(atoms)} image atoms, "
        f"{len(anomalies)} preserved source-label anomalies"
    )


if __name__ == "__main__":
    main()
