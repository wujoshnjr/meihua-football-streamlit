"""Build the checked-in 4,096-entry Jiao Shi Yi Lin database.

The source text is the Kanripo transcription of the Siku Quanshu edition.
Runtime code never downloads or parses the source corpus; this script turns
the reviewed snapshot under ``knowledge/sources`` into deterministic JSON.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "knowledge" / "sources" / "jiaoshi_yilin_kanripo.txt"
HEXAGRAM_PATH = ROOT / "knowledge" / "hexagrams.json"
OUTPUT_PATH = ROOT / "knowledge" / "classics" / "jiaoshi_yilin.json"

NAME_ALIASES = {
    "剥": "剝",
    "无妄": "無妄",
    "恒": "恆",
    "㤗": "泰",
    "㢲": "巽",
    "兑": "兌",
    "兊": "兌",
    "暌": "睽",
}
SECTION_RE = re.compile(r"^　　(?P<name>\S+)之第\S+$")
ENTRY_RE = re.compile(r"^(?P<name>\S+)　(?P<text>.*)$")


def _canonical_name(value: str) -> str:
    return NAME_ALIASES.get(value, value)


def _hexagram_index() -> tuple[list[str], dict[str, dict[str, Any]]]:
    payload = json.loads(HEXAGRAM_PATH.read_text(encoding="utf-8"))
    ordered = sorted(payload.values(), key=lambda item: int(item["sequence"]))
    names = [str(item["short_name"]) for item in ordered]
    if len(names) != 64 or len(set(names)) != 64:
        raise ValueError("hexagrams.json 必須提供 64 個不重複短卦名")
    index = {
        str(item["short_name"]): {
            "sequence": int(item["sequence"]),
            "full_name": str(item["name"]),
            "unicode": str(item["unicode"]),
            "binary_bottom_up": str(item["binary_bottom_up"]),
        }
        for item in ordered
    }
    return names, index


def _parse_source(
    source: str, names: list[str]
) -> tuple[dict[str, dict[str, str]], list[dict[str, Any]]]:
    valid_names = set(names)
    parsed_sections: dict[str, list[tuple[str, str]]] = {}
    section: str | None = None
    changed: str | None = None
    text_parts: list[str] = []

    def finish_entry() -> None:
        nonlocal changed, text_parts
        if section is None or changed is None:
            return
        text = "".join(text_parts).strip()
        if not text:
            raise ValueError(f"{section}之{changed} 沒有林辭")
        parsed_sections.setdefault(section, []).append((changed, text))
        changed = None
        text_parts = []

    for line_number, raw_line in enumerate(source.splitlines(), 1):
        section_match = SECTION_RE.match(raw_line)
        if section_match:
            finish_entry()
            section = _canonical_name(section_match.group("name"))
            if section not in valid_names:
                raise ValueError(f"第 {line_number} 行出現未知本卦：{section}")
            if section in parsed_sections:
                raise ValueError(f"重複本卦章節：{section}")
            parsed_sections[section] = []
            continue

        if section is None or not raw_line.strip():
            continue
        if raw_line == "欽定四庫全書" or "焦氏易林卷" in raw_line:
            continue

        entry_match = ENTRY_RE.match(raw_line)
        candidate = _canonical_name(entry_match.group("name")) if entry_match else ""
        if entry_match and candidate in valid_names:
            finish_entry()
            changed = candidate
            text_parts = [entry_match.group("text").strip()]
            continue

        if changed is not None:
            text_parts.append(raw_line.lstrip("　 ").strip())

    finish_entry()

    if set(parsed_sections) != valid_names:
        missing = sorted(valid_names - set(parsed_sections))
        extra = sorted(set(parsed_sections) - valid_names)
        raise ValueError(f"本卦章節不完整：missing={missing}, extra={extra}")
    entries: dict[str, dict[str, str]] = {}
    corrections: list[dict[str, Any]] = []
    for main_name, source_entries in parsed_sections.items():
        if len(source_entries) != 64:
            raise ValueError(f"{main_name}章共有 {len(source_entries)} 林辭，不是 64 條")
        expected_order = [main_name, *(name for name in names if name != main_name)]
        entries[main_name] = {}
        for position, (expected_name, (source_name, text)) in enumerate(
            zip(expected_order, source_entries, strict=True),
            start=1,
        ):
            entries[main_name][expected_name] = text
            if source_name != expected_name:
                corrections.append(
                    {
                        "main_hexagram": main_name,
                        "position": position,
                        "source_label": source_name,
                        "normalized_label": expected_name,
                        "reason": "依該章固定 64 變次序校正來源標題；林辭原文未改。",
                    }
                )
    return entries, corrections


def build_database() -> dict[str, Any]:
    names, hexagrams = _hexagram_index()
    source = SOURCE_PATH.read_text(encoding="utf-8")
    entries, label_corrections = _parse_source(source, names)
    return {
        "schema_version": "1.0",
        "title": "焦氏易林",
        "author": "漢・焦贛（焦延壽）",
        "edition": "《欽定四庫全書》本",
        "entry_count": sum(len(item) for item in entries.values()),
        "hexagram_order": names,
        "hexagrams": hexagrams,
        "entries": entries,
        "source_label_corrections": label_corrections,
        "source": {
            "project": "Kanripo",
            "repository": "kr-shadow/KR3",
            "path": "KR3g0029 焦氏易林-漢-焦贛.txt",
            "commit": "eca6cb15ba5ee47a4267fde608db2ecd2d5f55ac",
            "upstream_commit_noted_in_file": "764e995c",
            "license": "CC0-1.0",
            "url": "https://github.com/kr-shadow/KR3/blob/eca6cb15ba5ee47a4267fde608db2ecd2d5f55ac/KR3g0029%20%E7%84%A6%E6%B0%8F%E6%98%93%E6%9E%97-%E6%BC%A2-%E7%84%A6%E8%B4%9B.txt",
            "scope": "64 本卦各含 64 之卦，共 4,096 林辭；保留四庫本原文、異文與校注括註。",
        },
    }


def validate_database(payload: dict[str, Any]) -> None:
    names = payload.get("hexagram_order")
    entries = payload.get("entries")
    if not isinstance(names, list) or len(names) != 64 or len(set(names)) != 64:
        raise ValueError("焦氏易林卦序必須完整包含 64 卦")
    if not isinstance(entries, dict) or set(entries) != set(names):
        raise ValueError("焦氏易林本卦索引不完整")
    pairs = {
        (main_name, changed_name)
        for main_name, changed_entries in entries.items()
        for changed_name, text in changed_entries.items()
        if isinstance(text, str) and text.strip()
    }
    expected_pairs = {(main_name, changed_name) for main_name in names for changed_name in names}
    if pairs != expected_pairs or payload.get("entry_count") != 4096:
        raise ValueError("焦氏易林必須完整包含 64×64＝4,096 條非空林辭")


def main() -> None:
    payload = build_database()
    validate_database(payload)
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT_PATH} with {payload['entry_count']} entries")


if __name__ == "__main__":
    main()
