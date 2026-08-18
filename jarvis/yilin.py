from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
YILIN_ROOT = ROOT / "knowledge" / "yilin"
YILIN_ENTRIES_ROOT = YILIN_ROOT / "entries"
YILIN_BRIDGE_VERSION = "stark-meihua-yilin-bridge-v1.0.0"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def yilin_manifest() -> dict[str, Any]:
    return _load_json(YILIN_ROOT / "manifest.json")


@lru_cache(maxsize=1)
def yilin_entries() -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for path in sorted(YILIN_ENTRIES_ROOT.glob("*.json")):
        payload = _load_json(path)
        source_id = payload.get("source_id")
        source_section = payload.get("source_section")
        source_edition = payload.get("source_edition")
        source_repo = payload.get("source_repo")
        source_commit = payload.get("source_commit")
        source_volume_file = payload.get("source_volume_file")
        for row in payload.get("entries", []):
            rows.append(
                {
                    **row,
                    "source_id": row.get("source_id", source_id),
                    "source_section": row.get("source_section", source_section),
                    "source_edition": row.get("source_edition", source_edition),
                    "source_repo": row.get("source_repo", source_repo),
                    "source_commit": row.get("source_commit", source_commit),
                    "source_volume_file": row.get("source_volume_file", source_volume_file),
                    "source_file": str(path.relative_to(ROOT)),
                }
            )
    return tuple(rows)


@lru_cache(maxsize=1)
def _indexes() -> tuple[dict[tuple[str, str], dict[str, Any]], dict[tuple[int, int], dict[str, Any]]]:
    by_name: dict[tuple[str, str], dict[str, Any]] = {}
    by_number: dict[tuple[int, int], dict[str, Any]] = {}
    for row in yilin_entries():
        name_key = (str(row["from_name"]), str(row["to_name"]))
        number_key = (int(row["from_number"]), int(row["to_number"]))
        if name_key in by_name or number_key in by_number:
            raise ValueError(f"重複焦氏易林條目：{name_key[0]}之{name_key[1]} / {number_key}")
        by_name[name_key] = row
        by_number[number_key] = row
    return by_name, by_number


def yilin_index() -> dict[tuple[str, str], dict[str, Any]]:
    return _indexes()[0]


def yilin_number_index() -> dict[tuple[int, int], dict[str, Any]]:
    return _indexes()[1]


def yilin_entry(from_name: str, to_name: str) -> dict[str, Any] | None:
    return yilin_index().get((from_name, to_name))


def yilin_entry_by_number(from_number: int, to_number: int) -> dict[str, Any] | None:
    return yilin_number_index().get((int(from_number), int(to_number)))


@lru_cache(maxsize=1)
def yilin_catalog_stats() -> dict[str, Any]:
    manifest = yilin_manifest()
    entries = yilin_entries()
    from_numbers = {int(row["from_number"]) for row in entries}
    pair_count = len(entries)
    expected = int(manifest["expected_pairs"])
    return {
        "expected_pairs": expected,
        "materialized_pairs": pair_count,
        "materialized_from_hexagrams": len(from_numbers),
        "coverage_ratio": pair_count / expected if expected else 0.0,
        "catalog_status": manifest.get("catalog_status"),
        "coverage_claim": manifest.get("coverage_claim"),
        "bridge_mode": manifest.get("bridge_mode"),
        "textual_collation_status": manifest.get("textual_collation_status", "ONGOING"),
    }


@lru_cache(maxsize=1)
def yilin_image_ontology() -> tuple[dict[str, Any], ...]:
    payload = _load_json(YILIN_ROOT / "image_ontology.json")
    return tuple(payload.get("atoms", []))


def infer_image_atoms(classical_text: str) -> tuple[dict[str, Any], ...]:
    """Return project-level semantic hints matched from raw Yilin text.

    This is deliberately labeled heuristic. It does not claim that keyword
    matching reproduces a classical commentary, and it never generates a final
    divination result.
    """

    found: list[dict[str, Any]] = []
    for atom in yilin_image_ontology():
        terms = [str(term) for term in atom.get("match_terms", [])]
        hits = [term for term in terms if term and term in classical_text]
        if hits:
            found.append(
                {
                    "id": atom["id"],
                    "name": atom["name"],
                    "matched_terms": hits,
                    "classical_abstraction": atom.get("classical_abstraction"),
                    "football": atom.get("football", []),
                    "observable_signals": atom.get("observable_signals", []),
                    "counter_signals": atom.get("counter_signals", []),
                    "authority": "PROJECT_HEURISTIC__NOT_CLASSICAL_COMMENTARY",
                }
            )
    return tuple(found)


def search_yilin(query: str) -> list[dict[str, Any]]:
    term = query.strip().lower()
    if not term:
        return []
    results: list[dict[str, Any]] = []
    for row in yilin_entries():
        enriched = {**row, "lookup_key": f"{row['from_name']}之{row['to_name']}"}
        if term in json.dumps(enriched, ensure_ascii=False).lower():
            results.append({"system": "JIAOSHI_YILIN", "family": "transformation", **enriched})
            if len(results) >= 100:
                return results
    for atom in yilin_image_ontology():
        if term in json.dumps(atom, ensure_ascii=False).lower():
            results.append({"system": "JIAOSHI_YILIN", "family": "image_ontology", **atom})
            if len(results) >= 100:
                break
    return results


def build_meihua_yilin_bridge(
    original_hexagram: dict[str, Any],
    changed_hexagram: dict[str, Any],
) -> dict[str, Any]:
    manifest = yilin_manifest()
    from_number = int(original_hexagram["number"])
    to_number = int(changed_hexagram["number"])
    from_name = str(original_hexagram["name"])
    to_name = str(changed_hexagram["name"])

    # Number lookup is authoritative because historical/digital sources contain
    # orthographic variants of hexagram names. Display names remain those of the
    # project's validated King Wen catalog.
    entry = yilin_entry_by_number(from_number, to_number)
    base = {
        "kind": "meihua_yilin_bridge",
        "schema_version": YILIN_BRIDGE_VERSION,
        "mode": "MEIHUA_YILIN_BRIDGE",
        "historical_method_notice": manifest["historical_method_notice"],
        "authority_order": manifest["authority_order"],
        "from_hexagram": {
            "number": from_number,
            "name": from_name,
            "symbol": original_hexagram.get("symbol"),
        },
        "to_hexagram": {
            "number": to_number,
            "name": to_name,
            "symbol": changed_hexagram.get("symbol"),
        },
        "lookup_key": f"{from_name}之{to_name}",
        "catalog_stats": yilin_catalog_stats(),
        "interpretation_contract": [
            "《焦氏易林》只補充本卦到最終變卦的轉變情境，不重新起卦、不取代梅花體用旺衰。",
            "不得把互卦再套成一個焦林原始占法；若另作研究必須標成 project extension。",
            "classical_text/transcription 是古籍數位轉錄層；image_atoms 是專案 heuristic；football 是 modern application，三者不得混寫。",
            "若易林情境與梅花核心矛盾，保留矛盾並交給 ChatGPT 合參，不得強行統一。",
            "不得把單條林辭直接換算成勝率、固定比分或必然勝負。",
        ],
    }
    if entry is None:
        return {
            **base,
            "status": "SOURCE_PENDING",
            "classical_entry": None,
            "image_atoms": [],
            "missing_reason": "此本卦→變卦組合尚未 materialize；禁止生成或猜測林辭。",
        }

    classical_text = str(entry["classical_text"])
    return {
        **base,
        "status": "MATERIALIZED",
        "classical_entry": entry,
        "image_atoms": list(infer_image_atoms(classical_text)),
        "semantic_boundary": {
            "classical_text": "DIGITAL_TRANSCRIPTION_OF_PRIMARY_EDITION",
            "editorial_notes": "SOURCE_TRANSCRIPTION_APPARATUS",
            "image_atoms": "PROJECT_HEURISTIC",
            "football": "MODERN_APPLICATION",
        },
        "provenance": {
            "source_id": entry.get("source_id"),
            "edition": entry.get("source_edition"),
            "repository": entry.get("source_repo"),
            "commit": entry.get("source_commit"),
            "volume_file": entry.get("source_volume_file"),
            "page_start": entry.get("source_page_start"),
        },
    }
