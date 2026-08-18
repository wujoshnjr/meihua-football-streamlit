from __future__ import annotations

import json
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
YILIN_ROOT = ROOT / "knowledge" / "yilin"
YILIN_ENTRIES_ROOT = YILIN_ROOT / "entries"
HEXAGRAM_PATH = ROOT / "knowledge" / "meihua_hexagrams.json"
YILIN_BRIDGE_VERSION = "stark-meihua-yilin-bridge-v1.2.0"

# User-facing lookup accepts a few common orthographic variants, while every
# stored corpus row keeps the project's validated King Wen canonical name and
# the source transcription keeps its original label separately.
_NAME_ALIASES = {
    "無妄": "无妄",
    "恒": "恆",
    "遁": "遯",
    "暌": "睽",
    "兊": "兌",
    "兑": "兌",
    "旣濟": "既濟",
    "旣济": "既濟",
    "既济": "既濟",
    "未济": "未濟",
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _unique_strings(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


@lru_cache(maxsize=1)
def yilin_manifest() -> dict[str, Any]:
    return _load_json(YILIN_ROOT / "manifest.json")


@lru_cache(maxsize=1)
def _hexagram_name_numbers() -> dict[str, int]:
    rows = _load_json(HEXAGRAM_PATH).get("hexagrams", [])
    mapping = {str(row["name"]): int(row["number"]) for row in rows}
    if len(mapping) != 64 or set(mapping.values()) != set(range(1, 65)):
        raise ValueError("梅花六十四卦 catalog 必須完整且號碼唯一")
    for alias, canonical in _NAME_ALIASES.items():
        if canonical in mapping:
            mapping[alias] = mapping[canonical]
    return mapping


def _canonical_name(name: str) -> str:
    return _NAME_ALIASES.get(name, name)


@lru_cache(maxsize=64)
def _block_payload(from_number: int) -> dict[str, Any]:
    number = int(from_number)
    if number not in range(1, 65):
        raise KeyError(f"焦氏易林本卦號碼超出 1..64：{number}")
    return _load_json(YILIN_ENTRIES_ROOT / f"{number:02d}.json")


@lru_cache(maxsize=64)
def _block_entries(from_number: int) -> tuple[dict[str, Any], ...]:
    payload = _block_payload(int(from_number))
    path = YILIN_ENTRIES_ROOT / f"{int(from_number):02d}.json"
    inherited = {
        "source_id": payload.get("source_id"),
        "source_section": payload.get("source_section"),
        "source_edition": payload.get("source_edition"),
        "source_repo": payload.get("source_repo"),
        "source_commit": payload.get("source_commit"),
        "source_volume_file": payload.get("source_volume_file"),
    }
    rows: list[dict[str, Any]] = []
    for row in payload.get("entries", []):
        rows.append(
            {
                **row,
                **{key: row.get(key, value) for key, value in inherited.items()},
                "source_file": str(path.relative_to(ROOT)),
            }
        )
    return tuple(rows)


@lru_cache(maxsize=64)
def _block_number_index(from_number: int) -> dict[int, dict[str, Any]]:
    index: dict[int, dict[str, Any]] = {}
    for row in _block_entries(int(from_number)):
        to_number = int(row["to_number"])
        if to_number in index:
            raise ValueError(f"焦氏易林本卦 #{from_number} 重複之卦 #{to_number}")
        index[to_number] = row
    return index


@lru_cache(maxsize=1)
def yilin_entries() -> tuple[dict[str, Any], ...]:
    """Materialize the complete corpus only when a full-corpus operation needs it.

    Ordinary Meihua casting does not call this function: the bridge reads only
    the one 64-entry source block containing the requested transformation.
    """

    return tuple(row for from_number in range(1, 65) for row in _block_entries(from_number))


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
    """Return a full name index for audit/research callers."""

    return _indexes()[0]


def yilin_number_index() -> dict[tuple[int, int], dict[str, Any]]:
    """Return a full numeric index for audit/research callers."""

    return _indexes()[1]


def yilin_entry(from_name: str, to_name: str) -> dict[str, Any] | None:
    mapping = _hexagram_name_numbers()
    left = mapping.get(_canonical_name(from_name))
    right = mapping.get(_canonical_name(to_name))
    if left is None or right is None:
        return None
    return yilin_entry_by_number(left, right)


def yilin_entry_by_number(from_number: int, to_number: int) -> dict[str, Any] | None:
    left = int(from_number)
    right = int(to_number)
    if left not in range(1, 65) or right not in range(1, 65):
        return None
    return _block_number_index(left).get(right)


@lru_cache(maxsize=1)
def yilin_image_ontology() -> tuple[dict[str, Any], ...]:
    payload = _load_json(YILIN_ROOT / "image_ontology.json")
    return tuple(payload.get("atoms", []))


def infer_image_atoms(classical_text: str) -> tuple[dict[str, Any], ...]:
    """Retrieve project-level semantic candidates from one Yilin forest verse.

    Keyword matching is deliberately only a retrieval heuristic. It is never
    presented as 焦氏原註, a reconstructed historical method, or a final result.
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
                    "domain": atom.get("domain"),
                    "specificity": atom.get("specificity"),
                    "matched_terms": hits,
                    "classical_abstraction": atom.get("classical_abstraction"),
                    "football": atom.get("football", []),
                    "observable_signals": atom.get("observable_signals", []),
                    "counter_signals": atom.get("counter_signals", []),
                    "authority": "PROJECT_HEURISTIC__NOT_CLASSICAL_COMMENTARY",
                }
            )
    return tuple(found)


def yilin_semantic_profile(classical_text: str) -> dict[str, Any]:
    atoms = list(infer_image_atoms(classical_text))
    domains = _unique_strings([str(row.get("domain") or "") for row in atoms])
    football = _unique_strings([str(item) for row in atoms for item in row.get("football", [])])
    observables = _unique_strings([str(item) for row in atoms for item in row.get("observable_signals", [])])
    counters = _unique_strings([str(item) for row in atoms for item in row.get("counter_signals", [])])
    return {
        "status": "MATCHED_IMAGE_ATOMS" if atoms else "NO_ONTOLOGY_MATCH__READ_CLASSICAL_TEXT_DIRECTLY",
        "authority": "PROJECT_HEURISTIC__NOT_CLASSICAL_COMMENTARY",
        "atom_count": len(atoms),
        "domains": domains,
        "image_atoms": atoms,
        "football_hypotheses": football,
        "observable_signals": observables,
        "counter_signals": counters,
        "ai_rule": (
            "先讀林辭原文，再把命中意象當候選語義；只保留能與梅花核心及實際問題相互支持的類比。"
            "未命中 ontology 不代表林辭沒有意義，應由 ChatGPT 直接讀古文並明示推演層。"
        ),
    }


@lru_cache(maxsize=1)
def yilin_semantic_audit() -> dict[str, Any]:
    counts: Counter[str] = Counter()
    matched = 0
    for row in yilin_entries():
        atoms = infer_image_atoms(str(row["classical_text"]))
        if atoms:
            matched += 1
        counts.update(str(atom["id"]) for atom in atoms)
    total = len(yilin_entries())
    return {
        "total_entries": total,
        "entries_with_image_atoms": matched,
        "entries_without_image_atoms": total - matched,
        "match_ratio": matched / total if total else 0.0,
        "ontology_atoms": len(yilin_image_ontology()),
        "atom_occurrences": dict(sorted(counts.items())),
        "notice": "coverage is heuristic retrieval coverage, not textual-critical or predictive accuracy coverage",
    }


@lru_cache(maxsize=1)
def yilin_catalog_stats() -> dict[str, Any]:
    """Read release-level counts from the validated manifest.

    This keeps the normal casting hot path O(1) in corpus files instead of
    parsing all 4096 entries merely to display a coverage badge.
    """

    manifest = yilin_manifest()
    expected = int(manifest["expected_pairs"])
    materialized = int(manifest.get("materialized_pairs", 0))
    source_count = int(manifest.get("complete_from_hexagrams", 0))
    return {
        "expected_pairs": expected,
        "materialized_pairs": materialized,
        "materialized_from_hexagrams": source_count,
        "coverage_ratio": materialized / expected if expected else 0.0,
        "catalog_status": manifest.get("catalog_status"),
        "coverage_claim": manifest.get("coverage_claim"),
        "bridge_mode": manifest.get("bridge_mode"),
        "textual_collation_status": manifest.get("textual_collation_status", "ONGOING"),
        "source_label_anomaly_count": manifest.get("source_label_anomaly_count", 0),
        "ontology_atoms": len(yilin_image_ontology()),
        "runtime_lookup": "DIRECT_64_ENTRY_BLOCK__NO_FULL_CORPUS_LOAD",
    }


@lru_cache(maxsize=1)
def _search_index() -> tuple[tuple[dict[str, Any], str], ...]:
    rows: list[tuple[dict[str, Any], str]] = []
    for row in yilin_entries():
        enriched = {**row, "lookup_key": f"{row['from_name']}之{row['to_name']}"}
        rows.append((enriched, json.dumps(enriched, ensure_ascii=False).lower()))
    return tuple(rows)


def search_yilin(query: str) -> list[dict[str, Any]]:
    term = query.strip().lower()
    if not term:
        return []
    results: list[dict[str, Any]] = []
    for row, haystack in _search_index():
        if term in haystack:
            results.append({"system": "JIAOSHI_YILIN", "family": "transformation", **row})
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

    # Numeric lookup is authoritative because source transcriptions contain
    # orthographic variants and one preserved WYG target-label anomaly. Only
    # the requested 64-entry source block is loaded in the ordinary cast path.
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
            "classical_text/transcription 是古籍數位轉錄層；semantic_profile 是專案 heuristic；football 是 modern application，三者不得混寫。",
            "先讀梅花核心，再讀林辭；若兩者矛盾，保留矛盾並交給 ChatGPT 合參，不得強行統一。",
            "不得把單條林辭或 image atom 直接換算成勝率、固定比分或必然勝負。",
        ],
    }
    if entry is None:
        return {
            **base,
            "status": "SOURCE_PENDING",
            "classical_entry": None,
            "semantic_profile": None,
            "image_atoms": [],
            "missing_reason": "此本卦→變卦組合尚未 materialize；禁止生成或猜測林辭。",
        }

    classical_text = str(entry["classical_text"])
    semantic_profile = yilin_semantic_profile(classical_text)
    return {
        **base,
        "status": "MATERIALIZED",
        "classical_entry": entry,
        "semantic_profile": semantic_profile,
        # Kept as a compatibility alias for existing packet/UI consumers.
        "image_atoms": semantic_profile["image_atoms"],
        "semantic_boundary": {
            "classical_text": "DIGITAL_TRANSCRIPTION_OF_PRIMARY_EDITION",
            "editorial_notes": "SOURCE_TRANSCRIPTION_APPARATUS",
            "semantic_profile": "PROJECT_HEURISTIC",
            "football": "MODERN_APPLICATION",
            "final_interpretation": "CHATGPT_SYNTHESIS",
        },
        "provenance": {
            "source_id": entry.get("source_id"),
            "edition": entry.get("source_edition"),
            "repository": entry.get("source_repo"),
            "commit": entry.get("source_commit"),
            "volume_file": entry.get("source_volume_file"),
            "source_section": entry.get("source_section"),
            "page_start": entry.get("source_page_start"),
            "source_target_label": entry.get("source_target_label"),
            "source_label_order_anomaly": entry.get("source_label_order_anomaly", False),
            "gaiji_tokens": entry.get("gaiji_tokens", []),
            "editorial_notes": entry.get("editorial_notes", []),
        },
    }
