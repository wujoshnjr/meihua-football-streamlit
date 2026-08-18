from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from meihua.engine import MeihuaSnapshot


ROOT = Path(__file__).resolve().parents[1]
ZHOUYI_ROOT = ROOT / "knowledge" / "zhouyi"
ENTRIES_ROOT = ZHOUYI_ROOT / "entries"
MANIFEST_PATH = ZHOUYI_ROOT / "manifest.json"
REVIEW_POLICY_PATH = ROOT / "knowledge" / "zhouyi_review_policy.json"
LINE_ROLE_PATH = ROOT / "knowledge" / "meihua_line_roles.json"


@lru_cache(maxsize=1)
def _corpus_rows() -> tuple[dict[str, Any], ...]:
    paths = sorted(ENTRIES_ROOT.glob("*.json"))
    if len(paths) != 8:
        raise RuntimeError("缺少完整 knowledge/zhouyi/entries/01..08.json；請先執行 tools/import_zhouyi_kanripo.py")
    rows: list[dict[str, Any]] = []
    for expected_shard, path in enumerate(paths, 1):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("shard") != expected_shard:
            raise RuntimeError(f"周易 shard 順序錯誤：{path.name}")
        rows.extend(payload.get("hexagrams", []))
    if len(rows) != 64 or [int(row["number"]) for row in rows] != list(range(1, 65)):
        raise RuntimeError("周易 corpus 必須完整且依 1..64 卦序排列")
    return tuple(rows)


@lru_cache(maxsize=1)
def _manifest() -> dict[str, Any]:
    if not MANIFEST_PATH.exists():
        raise RuntimeError("缺少 knowledge/zhouyi/manifest.json")
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _policy() -> dict[str, Any]:
    return json.loads(REVIEW_POLICY_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _line_roles() -> dict[int, dict[str, Any]]:
    rows = json.loads(LINE_ROLE_PATH.read_text(encoding="utf-8"))["line_roles"]
    return {int(row["line"]): row for row in rows}


def zhouyi_catalog_stats() -> dict[str, Any]:
    manifest = _manifest()
    return {
        "materialized_shards": int(manifest["materialized_shards"]),
        "expected_shards": int(manifest["expected_shards"]),
        "materialized_hexagrams": int(manifest["materialized_hexagrams"]),
        "expected_hexagrams": int(manifest["expected_hexagrams"]),
        "materialized_standard_lines": int(manifest["materialized_standard_lines"]),
        "expected_standard_lines": int(manifest["expected_standard_lines"]),
        "mapped_xiaoxiang": int(manifest["mapped_xiaoxiang"]),
        "grouped_qian_xiaoxiang": int(manifest["grouped_qian_xiaoxiang"]),
        "use_lines": int(manifest["use_lines"]),
        "source_repository": manifest["source_repository"],
        "source_commit": manifest["source_commit"],
        "source_edition": manifest["source_edition"],
        "completion_status": manifest["completion_status"],
    }


def zhouyi_hexagram(number: int) -> dict[str, Any]:
    if number not in range(1, 65):
        raise ValueError("周易卦序必須為 1..64")
    row = _corpus_rows()[number - 1]
    if int(row["number"]) != number:
        raise RuntimeError("周易 corpus 卦序索引不一致")
    return row


def search_zhouyi(query: str, *, limit: int = 100) -> list[dict[str, Any]]:
    term = query.strip().lower()
    if not term:
        return []
    results: list[dict[str, Any]] = []
    for row in _corpus_rows():
        core_haystack = json.dumps(
            {
                "number": row["number"],
                "name": row["name"],
                "source_name": row.get("source_name"),
                "guaci": row["guaci"],
                "tuan": row["tuan"],
                "xiang": row["xiang"],
            },
            ensure_ascii=False,
        ).lower()
        if term in core_haystack:
            results.append(
                {
                    "system": "ZHOUYI",
                    "family": "hexagram_source",
                    "number": row["number"],
                    "name": row["name"],
                    "symbol": row["symbol"],
                    "upper": row["upper"],
                    "lower": row["lower"],
                    "guaci": row["guaci"],
                    "tuan": row["tuan"],
                    "xiang": row["xiang"],
                    "source": row["source"],
                }
            )
        for line in row["lines"]:
            line_haystack = json.dumps(
                {
                    "name": row["name"],
                    "marker": line["marker"],
                    "classical_text": line["classical_text"],
                    "xiaoxiang": line.get("xiaoxiang"),
                },
                ensure_ascii=False,
            ).lower()
            if term in line_haystack:
                results.append(
                    {
                        "system": "ZHOUYI",
                        "family": "line_source",
                        "number": row["number"],
                        "name": row["name"],
                        "symbol": row["symbol"],
                        "line": line["line"],
                        "marker": line["marker"],
                        "classical_text": line["classical_text"],
                        "xiaoxiang": line.get("xiaoxiang"),
                        "source_page_start": line["source_page_start"],
                        "source": row["source"],
                    }
                )
        if len(results) >= limit:
            return results[:limit]
    return results[:limit]


def _classical_core(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "number": row["number"],
        "name": row["name"],
        "symbol": row["symbol"],
        "upper": row["upper"],
        "lower": row["lower"],
        "guaci": row["guaci"],
        "tuan": row["tuan"],
        "xiang": row["xiang"],
        "source": row["source"],
        "review_status": row["review_status"],
    }


def _catalog_alignment(classical: dict[str, Any], catalog: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "number": int(classical["number"]) == int(catalog["number"]),
        "name": classical["name"] == catalog["name"],
        "symbol": classical["symbol"] == catalog["symbol"],
        "upper": classical["upper"] == catalog["upper"],
        "lower": classical["lower"] == catalog["lower"],
    }
    return {"checks": checks, "all_match": all(checks.values())}


def build_meihua_zhouyi_review(
    snapshot: MeihuaSnapshot,
    *,
    original_catalog: dict[str, Any],
    mutual_catalog: dict[str, Any],
    changed_catalog: dict[str, Any],
) -> dict[str, Any]:
    """Build a source-aware Zhouyi layer without making the final divinatory judgment."""

    original_source = zhouyi_hexagram(int(original_catalog["number"]))
    mutual_source = zhouyi_hexagram(int(mutual_catalog["number"]))
    changed_source = zhouyi_hexagram(int(changed_catalog["number"]))
    moving_line = original_source["lines"][snapshot.moving_line - 1]
    role = _line_roles()[snapshot.moving_line]
    policy = _policy()

    source_audit = {
        "original_alignment": _catalog_alignment(original_source, original_catalog),
        "mutual_alignment": _catalog_alignment(mutual_source, mutual_catalog),
        "changed_alignment": _catalog_alignment(changed_source, changed_catalog),
        "moving_line_matches_snapshot": int(moving_line["line"]) == snapshot.moving_line,
        "moving_line_xiaoxiang_status": moving_line["xiaoxiang"]["status"],
        "pinned_source_commit": original_source["source"]["commit"],
        "all_core_alignments_match": all(
            _catalog_alignment(source, catalog)["all_match"]
            for source, catalog in (
                (original_source, original_catalog),
                (mutual_source, mutual_catalog),
                (changed_source, changed_catalog),
            )
        ),
    }

    return {
        "kind": "zhouyi_source_review",
        "schema_version": "stark-meihua-zhouyi-review-v1.1.0",
        "status": "SOURCE_AWARE_REVIEW_READY",
        "scope_note": (
            "《周易》固定底本經文用來加深本／互／變與動爻審查；"
            "JARVIS 不把經文自動變成吉凶、勝率或比分。"
        ),
        "catalog_stats": zhouyi_catalog_stats(),
        "source_audit": source_audit,
        "original": _classical_core(original_source),
        "mutual": _classical_core(mutual_source),
        "changed": _classical_core(changed_source),
        "moving_line": {
            "line": snapshot.moving_line,
            "marker": moving_line["marker"],
            "classical_text": moving_line["classical_text"],
            "source_page_start": moving_line["source_page_start"],
            "xiaoxiang": moving_line["xiaoxiang"],
            "source_file": original_source["source"]["file"],
            "phase": role["phase"],
            "project_general": role["general"],
            "football_modern_application": role["football"],
            "boundary": "爻辭／可直接映射的小象是古籍轉錄；phase/general/football 為 JARVIS 分層解析。",
        },
        "meihua_crosscheck": {
            "body": snapshot.body_trigram,
            "use": snapshot.use_trigram,
            "body_use_relation": snapshot.body_use_relation,
            "body_season_state": snapshot.body_season_state,
            "mutual_upper_relation_to_body": snapshot.mutual_upper_relation_to_body,
            "mutual_lower_relation_to_body": snapshot.mutual_lower_relation_to_body,
            "changed_use_relation_to_body": snapshot.changed_use_relation_to_body,
        },
        "review_dimensions": policy["review_dimensions"],
        "football_meaning_contract": policy["football_meaning_contract"],
        "ai_review_order": policy["ai_review_order"],
        "authority_order": policy["authority_order"],
    }
