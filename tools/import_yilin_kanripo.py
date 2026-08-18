from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HEXAGRAM_PATH = ROOT / "knowledge" / "meihua_hexagrams.json"
YILIN_ROOT = ROOT / "knowledge" / "yilin"
ENTRIES_ROOT = YILIN_ROOT / "entries"
MANIFEST_PATH = YILIN_ROOT / "manifest.json"
SNAPSHOT_PATH = YILIN_ROOT / "source_snapshot.json"

UPSTREAM_REPO = "kanripo/KR3g0029"
UPSTREAM_COMMIT = "764e995ce74aa249081918ca1b0c23bbca62bec8"
UPSTREAM_EDITION = "WYG / 文淵閣四庫全書"
UPSTREAM_BASE = f"https://raw.githubusercontent.com/{UPSTREAM_REPO}/{UPSTREAM_COMMIT}"
SOURCE_FILES = tuple(f"KR3g0029_{index:03d}.txt" for index in range(1, 5))

# These spellings are diagnostic only. Each 易林 section places its own hexagram
# first, then lists the remaining King Wen hexagrams in canonical order. Runtime
# keys are therefore reconstructed from that explicit source convention, while
# the source labels are permanently retained so glyph variants or source errors
# are visible rather than silently normalized away.
SOURCE_NAMES = (
    "乾", "坤", "屯", "蒙", "需", "訟", "師", "比", "小畜", "履", "泰", "否", "同人", "大有", "謙", "豫",
    "隨", "蠱", "臨", "觀", "噬嗑", "賁", "剝", "復", "无妄", "大畜", "頤", "大過", "坎", "離", "咸", "恒",
    "遯", "大壯", "晉", "明夷", "家人", "睽", "蹇", "解", "損", "益", "夬", "姤", "萃", "升", "困", "井",
    "革", "鼎", "震", "艮", "漸", "歸妹", "豐", "旅", "巽", "兌", "渙", "節", "中孚", "小過", "既濟", "未濟",
)
EXTRA_ALIASES = {
    "㤗": 11,
    "無妄": 25,
    "无妄": 25,
    "恆": 32,
    "恒": 32,
    "遁": 33,
    "暌": 38,
    "睽": 38,
    "㢲": 57,
    "兊": 58,
    "兑": 58,
    "兌": 58,
    "随": 17,
    "蛊": 18,
    "临": 19,
    "观": 20,
    "贲": 22,
    "剥": 23,
    "复": 24,
    "颐": 27,
    "晋": 35,
    "损": 41,
    "渐": 53,
    "归妹": 54,
    "丰": 55,
    "涣": 59,
    "节": 60,
    "旣濟": 63,
    "旣济": 63,
    "既济": 63,
    "未济": 64,
}

SECTION_RE = re.compile(r"^\s*([^\s　]+)之第([一二三四五六七八九十百]+)¶?\s*$")
ENTRY_RE = re.compile(r"^([^\s　]+)[\s　]+(.*)$")
PAGE_RE = re.compile(r"^<pb:([^>]+)>¶?$")
NOTE_RE = re.compile(r"\([^()]*\)")
GAIJI_RE = re.compile(r"&KR\d+;")


def _chinese_number(text: str) -> int:
    digit = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    if text == "十":
        return 10
    if "十" in text:
        left, right = text.split("十", 1)
        return digit.get(left, 1) * 10 + digit.get(right, 0)
    return digit[text]


def _project_hexagrams() -> dict[int, dict[str, Any]]:
    rows = json.loads(HEXAGRAM_PATH.read_text(encoding="utf-8"))["hexagrams"]
    result = {int(row["number"]): row for row in rows}
    if set(result) != set(range(1, 65)):
        raise ValueError("梅花六十四卦 catalog 必須完整 1..64")
    return result


def _alias_index() -> dict[str, int]:
    index = {name: number for number, name in enumerate(SOURCE_NAMES, 1)}
    index.update(EXTRA_ALIASES)
    return index


def _target_order(from_number: int) -> list[int]:
    return [from_number, *[number for number in range(1, 65) if number != from_number]]


def _download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "JARVIS-Yilin-Corpus-Importer/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def _clean_text(parts: list[str]) -> tuple[str, str, list[str], list[str]]:
    raw = "".join(part.rstrip("¶") for part in parts)
    raw = re.sub(r"\s+", "", raw)
    notes = NOTE_RE.findall(raw)
    classical = NOTE_RE.sub("", raw)
    gaiji = sorted(set(GAIJI_RE.findall(classical)))
    return classical, raw, notes, gaiji


def _parse_volume(filename: str, content: str, project: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    aliases = _alias_index()
    sections: list[dict[str, Any]] = []
    current_section: dict[str, Any] | None = None
    current_entry: dict[str, Any] | None = None
    current_page: str | None = None

    def flush_entry() -> None:
        nonlocal current_entry
        if current_section is None or current_entry is None:
            return
        classical, raw, notes, gaiji = _clean_text(current_entry.pop("parts"))
        current_entry["classical_text"] = classical
        current_entry["transcription_raw"] = raw
        current_entry["editorial_notes"] = notes
        current_entry["gaiji_tokens"] = gaiji
        current_section["entries"].append(current_entry)
        current_entry = None

    def flush_section() -> None:
        nonlocal current_section
        flush_entry()
        if current_section is not None:
            sections.append(current_section)
            current_section = None

    for original_line in content.splitlines():
        line = original_line.rstrip("\n\r")
        page_match = PAGE_RE.match(line.strip())
        if page_match:
            current_page = page_match.group(1)
            continue

        section_match = SECTION_RE.match(line)
        if section_match:
            flush_section()
            source_label, ordinal_text = section_match.groups()
            from_number = _chinese_number(ordinal_text)
            label_number = aliases.get(source_label)
            current_section = {
                "from_number": from_number,
                "from_name": project[from_number]["name"],
                "from_symbol": project[from_number]["symbol"],
                "source_label": source_label,
                "source_label_number": label_number,
                "source_label_order_anomaly": label_number != from_number,
                "source_section": f"{source_label}之第{ordinal_text}",
                "source_volume_file": filename,
                "entries": [],
            }
            continue

        if current_section is None:
            continue
        stripped = line.rstrip("¶")
        if not stripped.strip():
            continue
        if stripped.startswith("焦氏易林卷") or stripped.startswith("欽定四庫全書"):
            continue

        starts_indented = bool(line[:1].isspace() or line.startswith("　"))
        entry_match = ENTRY_RE.match(stripped)
        if entry_match and not starts_indented:
            flush_entry()
            target_label, text = entry_match.groups()
            order = _target_order(int(current_section["from_number"]))
            position = len(current_section["entries"])
            if position >= 64:
                raise ValueError(f"{current_section['source_section']} 出現超過 64 個非縮排行")
            to_number = order[position]
            label_number = aliases.get(target_label)
            current_entry = {
                "to_number": to_number,
                "to_name": project[to_number]["name"],
                "to_symbol": project[to_number]["symbol"],
                "source_target_label": target_label,
                "source_target_label_number": label_number,
                "source_label_order_anomaly": label_number != to_number,
                "source_page_start": current_page,
                "parts": [text],
            }
        elif current_entry is not None:
            current_entry["parts"].append(stripped.lstrip("　 \t"))

    flush_section()
    return sections


def _validate_sections(sections: list[dict[str, Any]]) -> None:
    if len(sections) != 64:
        raise ValueError(f"焦氏易林應有 64 個本卦 section，解析得到 {len(sections)}")
    seen_from = [int(section["from_number"]) for section in sections]
    if seen_from != list(range(1, 65)):
        raise ValueError(f"本卦 section 順序或完整性錯誤：{seen_from}")
    for section in sections:
        rows = section["entries"]
        expected = _target_order(int(section["from_number"]))
        targets = [int(row["to_number"]) for row in rows]
        if targets != expected:
            raise ValueError(f"{section['source_section']} 之卦順序不符合『本卦先列，其餘依文王序』：{targets}")
        if set(targets) != set(range(1, 65)):
            raise ValueError(f"{section['source_section']} 必須完整覆蓋 64 之卦")
        if any(not row.get("classical_text") for row in rows):
            raise ValueError(f"{section['source_section']} 存在空白林辭")
        if any(not row.get("source_page_start") for row in rows):
            raise ValueError(f"{section['source_section']} 存在缺失頁碼定位的林辭")


def _source_anomalies(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    anomalies: list[dict[str, Any]] = []
    for section in sections:
        if section["source_label_order_anomaly"]:
            anomalies.append(
                {
                    "level": "source_section_label",
                    "from_number": section["from_number"],
                    "source_label": section["source_label"],
                    "mapped_number": section["source_label_number"],
                }
            )
        for row in section["entries"]:
            if row["source_label_order_anomaly"]:
                anomalies.append(
                    {
                        "level": "target_label",
                        "from_number": section["from_number"],
                        "to_number": row["to_number"],
                        "source_label": row["source_target_label"],
                        "mapped_number": row["source_target_label_number"],
                        "page": row["source_page_start"],
                    }
                )
    return anomalies


def _write_entries(sections: list[dict[str, Any]], project: dict[int, dict[str, Any]]) -> None:
    if ENTRIES_ROOT.exists():
        shutil.rmtree(ENTRIES_ROOT)
    ENTRIES_ROOT.mkdir(parents=True, exist_ok=True)

    for section in sections:
        from_number = int(section["from_number"])
        rows: list[dict[str, Any]] = []
        for source_row in section["entries"]:
            to_number = int(source_row["to_number"])
            rows.append(
                {
                    "id": f"yilin.{from_number:02d}.{to_number:02d}",
                    "from_number": from_number,
                    "from_name": project[from_number]["name"],
                    "from_symbol": project[from_number]["symbol"],
                    "to_number": to_number,
                    "to_name": project[to_number]["name"],
                    "to_symbol": project[to_number]["symbol"],
                    "classical_text": source_row["classical_text"],
                    "transcription_raw": source_row["transcription_raw"],
                    "editorial_notes": source_row["editorial_notes"],
                    "gaiji_tokens": source_row["gaiji_tokens"],
                    "source_target_label": source_row["source_target_label"],
                    "source_target_label_number": source_row["source_target_label_number"],
                    "source_label_order_anomaly": source_row["source_label_order_anomaly"],
                    "source_page_start": source_row["source_page_start"],
                    "verification_status": "WYG_DIGITAL_TRANSCRIPTION__PAIR_COMPLETE",
                    "variant_status": "EDITORIAL_APPARATUS_PRESERVED__MULTI_EDITION_COLLATION_ONGOING",
                    "semantic_status": "RAW_CLASSICAL_TEXT__PROJECT_HEURISTICS_SEPARATE",
                }
            )
        payload = {
            "schema_version": "stark-yilin-entries-v1.0.0",
            "source_id": "yilin-kanripo-wyg-transcription",
            "source_edition": UPSTREAM_EDITION,
            "source_repo": UPSTREAM_REPO,
            "source_commit": UPSTREAM_COMMIT,
            "source_volume_file": section["source_volume_file"],
            "source_section": section["source_section"],
            "source_label": section["source_label"],
            "source_label_order_anomaly": section["source_label_order_anomaly"],
            "from_number": from_number,
            "from_name": project[from_number]["name"],
            "entries": rows,
        }
        (ENTRIES_ROOT / f"{from_number:02d}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def _write_manifest(source_hashes: dict[str, str], sections: list[dict[str, Any]], project: dict[int, dict[str, Any]]) -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    anomalies = _source_anomalies(sections)
    manifest.update(
        {
            "schema_version": "stark-yilin-corpus-v1.0.0",
            "materialized_pairs": 4096,
            "complete_from_hexagrams": 64,
            "materialized_from_hexagrams": [project[number]["name"] for number in range(1, 65)],
            "catalog_status": "COMPLETE_4096_PAIR_COVERAGE__TEXTUAL_COLLATION_ONGOING",
            "coverage_claim": (
                "64×64=4096 個本卦→之卦槽位已全部 materialize，且每條都有非空林辭。"
                "這代表 pair coverage 完整，不代表所有版本異文、標點與後世注解已完成校勘。"
            ),
            "textual_collation_status": "WYG_BASE_COMPLETE__MULTI_EDITION_VARIANT_COLLATION_ONGOING",
            "target_order_policy": "各本卦 section 先列本卦自身，其餘之卦依文王六十四卦序排列。",
            "source_label_anomaly_count": len(anomalies),
            "source_label_policy": (
                "轉錄中的卦名異體或疑似誤標不被靜默修正；section ordinal + 易林 target-order convention 決定 lookup number，"
                "原 source label、可辨識映射與 anomaly flag 全部保留。"
            ),
            "transcription_source": {
                "id": "yilin-kanripo-wyg-transcription",
                "repository": UPSTREAM_REPO,
                "commit": UPSTREAM_COMMIT,
                "edition": UPSTREAM_EDITION,
                "role": "DIGITAL_TRANSCRIPTION_OF_PRIMARY_EDITION",
                "files": list(SOURCE_FILES),
                "sha256": source_hashes,
            },
            "source_blocks": {
                "complete": 64,
                "expected": 64,
                "note": "四庫 WYG 數位轉錄已解析全部 64 本卦區塊；多版本異文校勘另行追蹤。",
            },
        }
    )
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_snapshot(source_hashes: dict[str, str], sections: list[dict[str, Any]]) -> None:
    anomalies = _source_anomalies(sections)
    payload = {
        "schema_version": "stark-yilin-source-snapshot-v1.0.0",
        "upstream_repository": UPSTREAM_REPO,
        "upstream_commit": UPSTREAM_COMMIT,
        "edition": UPSTREAM_EDITION,
        "files": [{"name": name, "sha256": source_hashes[name]} for name in SOURCE_FILES],
        "parsed_from_hexagrams": len(sections),
        "parsed_pairs": sum(len(section["entries"]) for section in sections),
        "target_order_policy": "SELF_FIRST__THEN_KING_WEN_ORDER_EXCLUDING_SELF",
        "source_label_anomalies": anomalies,
        "normalization_policy": [
            "頁碼標記不進 classical_text，但每條保留 source_page_start。",
            "括號校語從 classical_text 分離，完整保存在 editorial_notes 與 transcription_raw。",
            "Kanripo gaiji token 不猜字，保留於 classical_text/transcription_raw，另列 gaiji_tokens。",
            "卦名 lookup 依 section ordinal 與『本卦先列、其餘依文王序』映射到專案 canonical name；原轉錄 label 永久保留。",
            "source label 與預期位置不一致時只記錄 anomaly，不以 label 靜默改寫 64×64 matrix。",
            "不以 AI 生成、補寫或改寫任何缺漏林辭。",
        ],
    }
    SNAPSHOT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def import_corpus() -> None:
    project = _project_hexagrams()
    sections: list[dict[str, Any]] = []
    source_hashes: dict[str, str] = {}
    for filename in SOURCE_FILES:
        raw = _download(f"{UPSTREAM_BASE}/{filename}")
        source_hashes[filename] = hashlib.sha256(raw).hexdigest()
        sections.extend(_parse_volume(filename, raw.decode("utf-8"), project))

    _validate_sections(sections)
    _write_entries(sections, project)
    _write_manifest(source_hashes, sections, project)
    _write_snapshot(source_hashes, sections)
    print(
        "Yilin corpus materialized: "
        f"{len(sections)} source blocks / {sum(len(section['entries']) for section in sections)} pairs / "
        f"{len(_source_anomalies(sections))} preserved source-label anomalies"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Materialize the complete 64×64 焦氏易林 corpus from pinned WYG transcription."
    )
    parser.parse_args()
    import_corpus()


if __name__ == "__main__":
    main()
