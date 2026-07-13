"""Build the checked-in 4,096-entry Jiao Shi Yi Lin database.

The displayed text follows the punctuated Wikisource transcription.  Kanripo's
Siku Quanshu transcription remains checked in as a collation base and supplies
the three entries which the Wikisource transcription explicitly marks missing.
Runtime code never downloads or parses either corpus.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
KANRIPO_SOURCE_PATH = ROOT / "knowledge" / "sources" / "jiaoshi_yilin_kanripo.txt"
PUNCTUATED_SOURCE_PATH = (
    ROOT / "knowledge" / "sources" / "jiaoshi_yilin_wikisource_punctuated.csv"
)
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
    "歸妺": "歸妹",
    "夬1": "夬",
}
SECTION_RE = re.compile(r"^　　(?P<name>\S+)之第\S+$")
ENTRY_RE = re.compile(r"^(?P<name>\S+)　(?P<text>.*)$")
PUNCTUATION_RE = re.compile(r"[，。；！？：、]", re.UNICODE)
FOOTNOTE_RE = re.compile(r"1\. 夬 : 原作.*$")

PUNCTUATED_COMPLETIONS = {
    ("大壯", "睽"): "蒼鷹羣行，相得旅前。王孫申公，驚奪我雄。北天門開，神火飛災。如不敬信，事入塵埃。",
    ("井", "巽"): "春陽生草，夏長條枝。萬物蕃滋，充實益有。",
    ("井", "渙"): "明月照夜，使暗為晝。國有仁賢，君尊於故。",
}


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


def _parse_kanripo_source(
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


def _parse_punctuated_source(
    source: str,
    names: list[str],
    kanripo_entries: dict[str, dict[str, str]],
) -> tuple[dict[str, dict[str, str]], list[dict[str, Any]], list[dict[str, Any]]]:
    lines = [line for line in source.splitlines() if line.strip()]
    if len(lines) != 4096:
        raise ValueError(f"標點底本共有 {len(lines)} 條，不是 4,096 條")

    grouped: dict[str, list[tuple[str, str, bool]]] = {}
    for line_number, line in enumerate(lines, 1):
        if "," not in line:
            raise ValueError(f"標點底本第 {line_number} 行缺少欄位分隔逗號")
        key, text = line.split(",", 1)
        if "之" not in key:
            raise ValueError(f"標點底本第 {line_number} 行缺少本卦之卦索引")
        main_raw, changed_raw = key.split("之", 1)
        marked_missing = changed_raw.endswith("。原缺。")
        if marked_missing:
            changed_raw = changed_raw.removesuffix("。原缺。")
        main_name = _canonical_name(main_raw)
        changed_name = _canonical_name(changed_raw)
        text = FOOTNOTE_RE.sub("", text).strip()
        grouped.setdefault(main_name, []).append((changed_name, text, marked_missing))

    if set(grouped) != set(names):
        raise ValueError("標點底本的 64 個本卦章節不完整")

    entries: dict[str, dict[str, str]] = {}
    label_corrections: list[dict[str, Any]] = []
    completion_notes: list[dict[str, Any]] = []
    for main_name in names:
        source_entries = grouped[main_name]
        if len(source_entries) != 64:
            raise ValueError(f"標點底本 {main_name} 章共有 {len(source_entries)} 條，不是 64 條")
        expected_order = [main_name, *(name for name in names if name != main_name)]
        entries[main_name] = {}
        for position, (expected_name, (source_name, text, marked_missing)) in enumerate(
            zip(expected_order, source_entries, strict=True),
            start=1,
        ):
            target_name = source_name if source_name in names else expected_name
            if source_name not in names:
                label_corrections.append(
                    {
                        "main_hexagram": main_name,
                        "position": position,
                        "source_label": source_name,
                        "normalized_label": target_name,
                        "reason": "依該章固定 64 變次序校正來源索引標題；林辭原文未移位。",
                    }
                )
            if target_name in entries[main_name]:
                raise ValueError(f"標點底本 {main_name}之{target_name} 索引重複")
            pair = (main_name, target_name)
            if marked_missing:
                if text:
                    raise ValueError(f"{main_name}之{target_name} 同時標示原缺又含林辭")
                text = PUNCTUATED_COMPLETIONS.get(pair, "")
                raw_text = kanripo_entries[main_name][target_name]
                if PUNCTUATION_RE.sub("", text) != raw_text:
                    raise ValueError(f"{main_name}之{target_name} 的補足文字與 Kanripo 底本不一致")
                completion_notes.append(
                    {
                        "main_hexagram": main_name,
                        "changed_hexagram": target_name,
                        "wikisource_status": "原缺",
                        "completion_source": "Kanripo《欽定四庫全書》本",
                        "editorial_action": "依四庫本補足原文並加入句讀標點；不改動字詞。",
                    }
                )
            if not text:
                raise ValueError(f"標點底本 {main_name}之{target_name} 沒有林辭")
            if not PUNCTUATION_RE.search(text) or text[-1] not in "。！？":
                raise ValueError(f"標點底本 {main_name}之{target_name} 未通過標點完整性檢查")
            entries[main_name][target_name] = text
        if set(entries[main_name]) != set(names):
            missing = sorted(set(names) - set(entries[main_name]))
            extra = sorted(set(entries[main_name]) - set(names))
            raise ValueError(f"標點底本 {main_name}章索引不完整：missing={missing}, extra={extra}")
    return entries, label_corrections, completion_notes


def build_database() -> dict[str, Any]:
    names, hexagrams = _hexagram_index()
    kanripo_source = KANRIPO_SOURCE_PATH.read_text(encoding="utf-8")
    kanripo_entries, base_label_corrections = _parse_kanripo_source(kanripo_source, names)
    punctuated_source = PUNCTUATED_SOURCE_PATH.read_text(encoding="utf-8")
    entries, label_corrections, completion_notes = _parse_punctuated_source(
        punctuated_source,
        names,
        kanripo_entries,
    )
    return {
        "schema_version": "1.1",
        "title": "焦氏易林",
        "author": "漢・焦贛（焦延壽）",
        "edition": "維基文庫標點校對本；三條原缺林辭以《欽定四庫全書》本補足",
        "text_style": "繁體中文標點版",
        "entry_count": sum(len(item) for item in entries.values()),
        "punctuated_entry_count": sum(len(item) for item in entries.values()),
        "hexagram_order": names,
        "hexagrams": hexagrams,
        "entries": entries,
        "source_label_corrections": label_corrections,
        "source_completion_notes": completion_notes,
        "source": {
            "project": "維基文庫",
            "work_url": "https://zh.wikisource.org/wiki/焦氏易林",
            "attribution": "維基文庫編者",
            "license": "CC-BY-SA-4.0",
            "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
            "snapshot_mirror_repository": "Subiectum/Zhouyi",
            "snapshot_mirror_path": "象数/焦氏易林.csv",
            "snapshot_mirror_commit": "3ea1b1e93dc8c5dfbdf11c338f4c38a8825194a0",
            "snapshot_mirror_url": "https://github.com/Subiectum/Zhouyi/blob/3ea1b1e93dc8c5dfbdf11c338f4c38a8825194a0/%E8%B1%A1%E6%95%B0/%E7%84%A6%E6%B0%8F%E6%98%93%E6%9E%97.csv",
            "scope": "4,093 條維基文庫標點林辭；另有 3 條原缺項目由 Kanripo 四庫本補足。",
        },
        "base_source": {
            "project": "Kanripo",
            "repository": "kr-shadow/KR3",
            "path": "KR3g0029 焦氏易林-漢-焦贛.txt",
            "commit": "eca6cb15ba5ee47a4267fde608db2ecd2d5f55ac",
            "upstream_commit_noted_in_file": "764e995c",
            "license": "CC0-1.0",
            "url": "https://github.com/kr-shadow/KR3/blob/eca6cb15ba5ee47a4267fde608db2ecd2d5f55ac/KR3g0029%20%E7%84%A6%E6%B0%8F%E6%98%93%E6%9E%97-%E6%BC%A2-%E7%84%A6%E8%B4%9B.txt",
            "scope": "四庫本無標點校勘快照，並補足標點底本標示原缺的 3 條林辭。",
        },
        "base_source_label_corrections": base_label_corrections,
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
    if (
        pairs != expected_pairs
        or payload.get("entry_count") != 4096
        or payload.get("punctuated_entry_count") != 4096
    ):
        raise ValueError("焦氏易林必須完整包含 64×64＝4,096 條非空林辭")
    if any(
        not PUNCTUATION_RE.search(text) or text[-1] not in "。！？"
        for changed_entries in entries.values()
        for text in changed_entries.values()
    ):
        raise ValueError("焦氏易林 4,096 條林辭必須全部含標點並以句末標點結束")


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
