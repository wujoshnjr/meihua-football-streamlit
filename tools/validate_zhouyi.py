from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ZHOUYI_ROOT = ROOT / "knowledge" / "zhouyi"
ENTRIES_ROOT = ZHOUYI_ROOT / "entries"
MANIFEST_PATH = ZHOUYI_ROOT / "manifest.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"Zhouyi validation failed: {message}")


def main() -> None:
    require(MANIFEST_PATH.exists(), "knowledge/zhouyi/manifest.json is missing")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    shard_paths = sorted(ENTRIES_ROOT.glob("*.json"))
    require(len(shard_paths) == 8, "Zhouyi corpus must contain exactly 8 shards")

    rows = []
    for expected_shard, path in enumerate(shard_paths, 1):
        payload = json.loads(path.read_text(encoding="utf-8"))
        require(payload.get("shard") == expected_shard, f"{path.name} shard index mismatch")
        require(payload.get("source_commit") == manifest.get("source_commit"), f"{path.name} source commit mismatch")
        shard_rows = payload.get("hexagrams", [])
        require(len(shard_rows) == 8, f"{path.name} must contain exactly 8 hexagrams")
        rows.extend(shard_rows)

    require(len(rows) == 64, "corpus must contain exactly 64 hexagrams")
    require({row.get("number") for row in rows} == set(range(1, 65)), "hexagram numbers must be exactly 1..64")
    require(len({row.get("name") for row in rows}) == 64, "hexagram names must be unique")

    line_keys: set[tuple[int, int]] = set()
    mapped_xiaoxiang = 0
    grouped_qian = 0
    review_required = 0
    for row in rows:
        number = int(row["number"])
        require(bool(row.get("guaci", {}).get("classical_text")), f"hexagram {number} missing guaci")
        require(bool(row.get("tuan", {}).get("classical_text")), f"hexagram {number} missing tuan")
        require(bool(row.get("xiang", {}).get("classical_text")), f"hexagram {number} missing xiang")
        lines = row.get("lines", [])
        require(len(lines) == 6, f"hexagram {number} must contain exactly six standard lines")
        for expected, line in enumerate(lines, 1):
            require(line.get("line") == expected, f"hexagram {number} line order mismatch")
            require(bool(line.get("marker")), f"hexagram {number} line {expected} missing marker")
            require(bool(line.get("classical_text")), f"hexagram {number} line {expected} missing classical text")
            require(bool(line.get("source_page_start")), f"hexagram {number} line {expected} missing source page")
            small = line.get("xiaoxiang", {})
            require(small.get("status") in {"MAPPED", "GROUPED_IN_QIAN_XIANG_BLOCK", "SOURCE_REVIEW_REQUIRED"}, f"hexagram {number} line {expected} missing Xiaoxiang status")
            if small.get("status") == "MAPPED":
                mapped_xiaoxiang += 1
                require(bool(small.get("classical_text")), f"hexagram {number} line {expected} mapped Xiaoxiang missing text")
                require(bool(small.get("source_page_start")), f"hexagram {number} line {expected} mapped Xiaoxiang missing page")
            elif small.get("status") == "GROUPED_IN_QIAN_XIANG_BLOCK":
                grouped_qian += 1
                require(number == 1, "grouped Xiaoxiang exception is only allowed for Qian in this source")
            else:
                review_required += 1
            line_keys.add((number, expected))
        source = row.get("source", {})
        require(source.get("commit") == manifest.get("source_commit"), f"hexagram {number} source commit mismatch")
        require(bool(source.get("file")) and bool(source.get("sha256")), f"hexagram {number} incomplete provenance")
        require(row.get("review_status") == "SOURCE_TRANSCRIPTION_PARSED__INTERPRETATION_SEPARATE", f"hexagram {number} review boundary missing")

    require(len(line_keys) == 384, "must contain exactly 384 unique standard line slots")
    require(manifest.get("materialized_shards") == 8, "manifest must report 8 shards")
    require(manifest.get("materialized_hexagrams") == 64, "manifest must report 64 hexagrams")
    require(manifest.get("materialized_standard_lines") == 384, "manifest must report 384 standard lines")
    require(manifest.get("mapped_xiaoxiang") == mapped_xiaoxiang, "manifest Xiaoxiang mapped count mismatch")
    require(manifest.get("grouped_qian_xiaoxiang") == grouped_qian, "manifest grouped Qian Xiaoxiang mismatch")
    require(review_required == 0, f"unexpected unmapped Xiaoxiang records: {review_required}")
    require(grouped_qian == 6, f"Qian grouped Xiaoxiang count should be 6, got {grouped_qian}")
    require(mapped_xiaoxiang == 378, f"directly mapped Xiaoxiang should be 378, got {mapped_xiaoxiang}")
    require(manifest.get("source_commit") == "8284adbf9e3435d713180e24f05bf75f8b7d1d96", "unexpected Zhouyi source commit")
    print(
        "Zhouyi validation passed: 8 shards / 64 hexagrams / 384 lines / "
        f"{mapped_xiaoxiang} mapped Xiaoxiang + 6 Qian grouped-source Xiaoxiang"
    )


if __name__ == "__main__":
    main()
