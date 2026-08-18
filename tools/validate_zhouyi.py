from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = ROOT / "knowledge" / "zhouyi" / "corpus.json"
MANIFEST_PATH = ROOT / "knowledge" / "zhouyi" / "manifest.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"Zhouyi validation failed: {message}")


def main() -> None:
    require(CORPUS_PATH.exists(), "knowledge/zhouyi/corpus.json is missing")
    require(MANIFEST_PATH.exists(), "knowledge/zhouyi/manifest.json is missing")
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    rows = corpus.get("hexagrams", [])
    require(len(rows) == 64, "corpus must contain exactly 64 hexagrams")
    require({row.get("number") for row in rows} == set(range(1, 65)), "hexagram numbers must be exactly 1..64")
    require(len({row.get("name") for row in rows}) == 64, "hexagram names must be unique")

    line_keys: set[tuple[int, int]] = set()
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
            line_keys.add((number, expected))
        source = row.get("source", {})
        require(source.get("commit") == manifest.get("source_commit"), f"hexagram {number} source commit mismatch")
        require(bool(source.get("file")) and bool(source.get("sha256")), f"hexagram {number} incomplete provenance")
        require(row.get("review_status") == "SOURCE_TRANSCRIPTION_PARSED__INTERPRETATION_SEPARATE", f"hexagram {number} review boundary missing")

    require(len(line_keys) == 384, "must contain exactly 384 unique standard line slots")
    require(manifest.get("materialized_hexagrams") == 64, "manifest must report 64 hexagrams")
    require(manifest.get("materialized_standard_lines") == 384, "manifest must report 384 standard lines")
    require(manifest.get("source_commit") == "8284adbf9e3435d713180e24f05bf75f8b7d1d96", "unexpected Zhouyi source commit")
    print("Zhouyi validation passed: 64 hexagrams / 384 standard lines / pinned provenance")


if __name__ == "__main__":
    main()
