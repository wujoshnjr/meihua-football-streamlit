from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
YILIN_ROOT = ROOT / "knowledge" / "yilin"
YILIN_ENTRIES_ROOT = YILIN_ROOT / "entries"
YILIN_BRIDGE_VERSION = "stark-meihua-yilin-bridge-v0.1.0"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def yilin_manifest() -> dict[str, Any]:
    return _load_json(YILIN_ROOT / "manifest.json")


def yilin_entries() -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for path in sorted(YILIN_ENTRIES_ROOT.glob("*.json")):
        payload = _load_json(path)
        source_id = payload.get("source_id")
        source_section = payload.get("source_section")
        for row in payload.get("entries", []):
            rows.append(
                {
                    **row,
                    "source_id": row.get("source_id", source_id),
                    "source_section": row.get("source_section", source_section),
                    "source_file": str(path.relative_to(ROOT)),
                }
            )
    return tuple(rows)


def yilin_index() -> dict[tuple[str, str], dict[str, Any]]:
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for row in yilin_entries():
        key = (str(row["from_name"]), str(row["to_name"]))
        if key in index:
            raise ValueError(f"重複焦氏易林條目：{key[0]}之{key[1]}")
        index[key] = row
    return index


def yilin_entry(from_name: str, to_name: str) -> dict[str, Any] | None:
    return yilin_index().get((from_name, to_name))


def yilin_catalog_stats() -> dict[str, Any]:
    manifest = yilin_manifest()
    entries = yilin_entries()
    from_names = {str(row["from_name"]) for row in entries}
    pair_count = len(entries)
    expected = int(manifest["expected_pairs"])
    return {
        "expected_pairs": expected,
        "materialized_pairs": pair_count,
        "materialized_from_hexagrams": len(from_names),
        "coverage_ratio": pair_count / expected if expected else 0.0,
        "catalog_status": manifest.get("catalog_status"),
        "bridge_mode": manifest.get("bridge_mode"),
    }


def yilin_image_ontology() -> tuple[dict[str, Any], ...]:
    payload = _load_json(YILIN_ROOT / "image_ontology.json")
    return tuple(payload.get("atoms", []))


def infer_image_atoms(classical_text: str) -> tuple[dict[str, Any], ...]:
    """Return project-level semantic hints matched from raw Yilin text.

    This is deliberately labeled heuristic. It does not claim that a keyword
    search reproduces a classical commentary, and it never generates a final
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


def build_meihua_yilin_bridge(
    original_hexagram: dict[str, Any],
    changed_hexagram: dict[str, Any],
) -> dict[str, Any]:
    manifest = yilin_manifest()
    from_name = str(original_hexagram["name"])
    to_name = str(changed_hexagram["name"])
    entry = yilin_entry(from_name, to_name)
    base = {
        "kind": "meihua_yilin_bridge",
        "schema_version": YILIN_BRIDGE_VERSION,
        "mode": "MEIHUA_YILIN_BRIDGE",
        "historical_method_notice": manifest["historical_method_notice"],
        "authority_order": manifest["authority_order"],
        "from_hexagram": {
            "number": original_hexagram.get("number"),
            "name": from_name,
            "symbol": original_hexagram.get("symbol"),
        },
        "to_hexagram": {
            "number": changed_hexagram.get("number"),
            "name": to_name,
            "symbol": changed_hexagram.get("symbol"),
        },
        "lookup_key": f"{from_name}之{to_name}",
        "catalog_stats": yilin_catalog_stats(),
        "interpretation_contract": [
            "《焦氏易林》只補充本卦到最終變卦的轉變情境，不重新起卦、不取代梅花體用旺衰。",
            "不得把互卦再套成一個焦林原始占法；若另作研究必須標成 project extension。",
            "classical_text 是古籍層；image_atoms 是專案 heuristic；football 是 modern application，三者不得混寫。",
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
            "missing_reason": "此本卦→變卦組合尚未 materialize 到本地 4096 catalog；禁止生成或猜測林辭。",
        }

    classical_text = str(entry["classical_text"])
    return {
        **base,
        "status": "MATERIALIZED",
        "classical_entry": entry,
        "image_atoms": list(infer_image_atoms(classical_text)),
        "semantic_boundary": {
            "classical_text": "PRIMARY_TRANSCRIPTION",
            "image_atoms": "PROJECT_HEURISTIC",
            "football": "MODERN_APPLICATION",
        },
    }
