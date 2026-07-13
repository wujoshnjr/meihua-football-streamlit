"""Build the checked-in Zhouyi knowledge database from public-domain source text.

The runtime never calls the network.  This maintenance script is intentionally
separate so a curator can refresh and validate the classical text before a
reviewed JSON file is committed.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import time
import urllib.parse
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HEXAGRAM_PATH = ROOT / "knowledge" / "hexagrams.json"
CLASSICS_DIR = ROOT / "knowledge" / "classics"
USER_AGENT = "meihua-complete-casting/5.0 (knowledge database builder)"
WIKISOURCE_API = "https://zh.wikisource.org/w/api.php"

SHORT_NAMES = [
    "乾", "坤", "屯", "蒙", "需", "訟", "師", "比", "小畜", "履", "泰", "否", "同人", "大有", "謙", "豫",
    "隨", "蠱", "臨", "觀", "噬嗑", "賁", "剝", "復", "無妄", "大畜", "頤", "大過", "坎", "離", "咸", "恆",
    "遯", "大壯", "晉", "明夷", "家人", "睽", "蹇", "解", "損", "益", "夬", "姤", "萃", "升", "困", "井",
    "革", "鼎", "震", "艮", "漸", "歸妹", "豐", "旅", "巽", "兌", "渙", "節", "中孚", "小過", "既濟", "未濟",
]

# Wikisource has a few historical page-title variants.
PAGE_NAMES = {"無妄": "无妄", "恆": "恒"}

TRIGRAM_LINES = {
    "乾": "111",
    "兌": "110",
    "離": "101",
    "震": "100",
    "巽": "011",
    "坎": "010",
    "艮": "001",
    "坤": "000",
}


def _request_wikitext(page_name: str) -> str:
    params = urllib.parse.urlencode(
        {
            "action": "parse",
            "page": f"周易/{PAGE_NAMES.get(page_name, page_name)}",
            "prop": "wikitext",
            "format": "json",
            "formatversion": "2",
        }
    )
    request = urllib.request.Request(f"{WIKISOURCE_API}?{params}", headers={"User-Agent": USER_AGENT})
    payload: dict[str, Any] | None = None
    for attempt in range(6):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.load(response)
            break
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == 5:
                raise
            retry_after = float(exc.headers.get("Retry-After", 0) or 0)
            time.sleep(max(retry_after, 1.5 * (attempt + 1)))
    if payload is None:
        raise ValueError(f"No response for 周易/{page_name}")
    if "parse" not in payload:
        raise ValueError(f"Wikisource page unavailable: 周易/{page_name}: {payload}")
    return str(payload["parse"]["wikitext"])


def _clean_markup(value: str) -> str:
    value = re.sub(r"-\{([^{}]+)\}-", r"\1", value)
    value = re.sub(r"<[^>]+>", "", value)
    value = value.replace("'''", "").replace("''", "")
    value = re.sub(r"\[\[(?:[^\]|]+\|)?([^\]]+)\]\]", r"\1", value)
    value = re.sub(r"^[*#:;\s]+", "", value)
    value = html.unescape(value)
    value = value.replace("无", "無").replace("恒", "恆").replace("兑", "兌")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _parse_page(wikitext: str) -> dict[str, Any]:
    section = "header"
    judgment_parts: list[str] = []
    line_texts: list[str] = []
    tuan_parts: list[str] = []
    great_image_parts: list[str] = []
    small_images: list[str] = []
    wenyan_parts: list[str] = []

    for raw_line in wikitext.splitlines():
        cleaned = _clean_markup(raw_line)
        if not cleaned:
            continue
        if cleaned == "易經：":
            section = "classic"
            continue
        if cleaned == "彖曰：":
            section = "tuan"
            continue
        if cleaned == "象曰：":
            section = "image"
            continue
        if cleaned == "文言曰：":
            section = "wenyan"
            continue

        numbered = raw_line.lstrip().startswith("*#")
        nested = raw_line.lstrip().startswith("**") or raw_line.lstrip().startswith("***")
        if section == "classic":
            if numbered:
                line_texts.append(cleaned)
            elif nested:
                judgment_parts.append(cleaned)
        elif section == "tuan" and (numbered or nested):
            tuan_parts.append(cleaned)
        elif section == "image":
            if numbered:
                small_images.append(cleaned)
            elif nested:
                great_image_parts.append(cleaned)
        elif section == "wenyan" and (numbered or nested):
            wenyan_parts.append(cleaned)

    if len(line_texts) not in {6, 7}:
        raise ValueError(f"Expected six lines (plus optional special line), got {len(line_texts)}")
    if len(small_images) not in {6, 7}:
        raise ValueError(f"Expected six small images (plus optional special line), got {len(small_images)}")

    lines: list[dict[str, Any]] = []
    for position in range(1, 7):
        classic = line_texts[position - 1]
        label, separator, body = classic.partition("：")
        lines.append(
            {
                "position": position,
                "label": label if separator else "",
                "text": body if separator else classic,
                "classic_text": classic,
                "small_image_text": small_images[position - 1],
            }
        )

    special_line: dict[str, str] | None = None
    if len(line_texts) == 7:
        label, separator, body = line_texts[6].partition("：")
        special_line = {
            "label": label if separator else "",
            "text": body if separator else line_texts[6],
            "classic_text": line_texts[6],
            "small_image_text": small_images[6],
        }

    return {
        "judgment_text": "".join(judgment_parts),
        "tuan_text": "".join(tuan_parts),
        "great_image_text": "".join(great_image_parts),
        "lines": lines,
        "special_line": special_line,
        "wenyan_text": "\n".join(wenyan_parts),
    }


def _parse_package_entry(entry: dict[str, Any]) -> dict[str, Any]:
    line_texts = [str(value).strip() for value in entry.get("yao_ci", [])]
    small_images = [str(value).strip() for value in entry.get("xiao_xiang", [])]
    if len(line_texts) not in {6, 7} or len(small_images) != len(line_texts):
        raise ValueError(f"Invalid line corpus for {entry.get('name', '')}")
    lines: list[dict[str, Any]] = []
    for position, (classic, small_image) in enumerate(zip(line_texts[:6], small_images[:6], strict=True), 1):
        match = re.match(r"^(初[六九]|[六九][二三四五]|上[六九])[：，,](.*)$", classic)
        label = match.group(1) if match else ""
        body = match.group(2).strip() if match else classic
        lines.append(
            {
                "position": position,
                "label": label,
                "text": body,
                "classic_text": classic,
                "small_image_text": small_image,
            }
        )
    special_line: dict[str, str] | None = None
    if len(line_texts) == 7:
        match = re.match(r"^(用[六九])[：，,](.*)$", line_texts[6])
        label = match.group(1) if match else ""
        body = match.group(2).strip() if match else line_texts[6]
        special_line = {
            "label": label,
            "text": body,
            "classic_text": line_texts[6],
            "small_image_text": small_images[6],
        }
    return {
        "judgment_text": str(entry.get("gua_ci", "")).strip(),
        "tuan_text": str(entry.get("tuan_ci", "")).strip(),
        "great_image_text": str(entry.get("da_xiang", "")).strip(),
        "lines": lines,
        "special_line": special_line,
        "wenyan_text": "",
    }


def _keywords(overview: str) -> list[str]:
    return [
        part.strip("。；，、 ")
        for part in re.split(r"[、，；]|與", overview)
        if part.strip("。；，、 ")
    ]


def build_database(package_json: Path | None = None) -> dict[str, dict[str, Any]]:
    previous = json.loads(HEXAGRAM_PATH.read_text(encoding="utf-8"))
    ordered_previous = sorted(previous.items(), key=lambda item: int(item[1]["sequence"]))
    if len(ordered_previous) != 64:
        raise ValueError("Existing structural index must contain 64 hexagrams")

    page_results: dict[str, dict[str, Any]] = {}
    source_name = "Wikisource 周易 pages"
    if package_json is not None:
        raw_entries = _normalize_traditional(
            json.loads(package_json.read_text(encoding="utf-8"))
        )
        if not isinstance(raw_entries, list) or len(raw_entries) != 64:
            raise ValueError("@freizl/yijing corpus must contain 64 entries")
        by_short_name = {str(item["name"]).replace("恒", "恆").replace("无", "無"): item for item in raw_entries}
        page_results = {
            short_name: _parse_package_entry(by_short_name[short_name])
            for short_name in SHORT_NAMES
        }
        source_name = "@freizl/yijing 2.1.0 zh-TW/64gua.json (MIT)"
    else:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
                executor.submit(_request_wikitext, short_name): short_name
                for short_name in SHORT_NAMES
            }
            for future in as_completed(futures):
                short_name = futures[future]
                page_results[short_name] = _parse_page(future.result())

    database: dict[str, dict[str, Any]] = {}
    for sequence, ((full_name, previous_item), short_name) in enumerate(
        zip(ordered_previous, SHORT_NAMES, strict=True),
        start=1,
    ):
        if int(previous_item["sequence"]) != sequence:
            raise ValueError(f"Sequence gap at {full_name}")
        upper = str(previous_item["upper"])
        lower = str(previous_item["lower"])
        bottom_up = TRIGRAM_LINES[lower] + TRIGRAM_LINES[upper]
        overview = str(previous_item.get("meaning_overview") or previous_item.get("core") or "").strip()
        database[full_name] = {
            "sequence": sequence,
            "unicode": chr(0x4DC0 + sequence - 1),
            "name": full_name,
            "short_name": short_name,
            "upper": upper,
            "lower": lower,
            "binary_bottom_up": bottom_up,
            "line_types_bottom_up": ["陽" if value == "1" else "陰" for value in bottom_up],
            "meaning_overview": overview,
            "keywords": _keywords(overview),
            **page_results[short_name],
            "source": {
                "title": source_name,
                "url": "https://github.com/freizl/yijing"
                if package_json is not None
                else "https://zh.wikisource.org/wiki/"
                + urllib.parse.quote(f"周易/{PAGE_NAMES.get(short_name, short_name)}"),
                "text_scope": "卦辭、彖傳、大象、六爻爻辭、小象；乾坤另含用九／用六與文言",
            },
        }

    by_bits = {item["binary_bottom_up"]: name for name, item in database.items()}
    for item in database.values():
        bits = str(item["binary_bottom_up"])
        mutual = bits[1:4] + bits[2:5]
        item["related_hexagrams"] = {
            "nuclear": by_bits[mutual],
            "opposite": by_bits["".join("0" if bit == "1" else "1" for bit in bits)],
            "reversed": by_bits[bits[::-1]],
        }
    return database


def validate_database(database: dict[str, dict[str, Any]]) -> None:
    if len(database) != 64:
        raise ValueError(f"Expected 64 hexagrams, got {len(database)}")
    sequences = {int(item["sequence"]) for item in database.values()}
    binaries = {str(item["binary_bottom_up"]) for item in database.values()}
    if sequences != set(range(1, 65)) or len(binaries) != 64:
        raise ValueError("Sequence or six-line coverage is incomplete")
    for name, item in database.items():
        if len(item["lines"]) != 6:
            raise ValueError(f"{name} does not have six lines")
        required = ["judgment_text", "tuan_text", "great_image_text", "meaning_overview"]
        if any(not str(item.get(field, "")).strip() for field in required):
            raise ValueError(f"{name} is missing a required text field")
        for line in item["lines"]:
            if not line["classic_text"] or not line["small_image_text"]:
                raise ValueError(f"{name} line {line['position']} is incomplete")


def _normalize_traditional(value: Any) -> Any:
    if isinstance(value, str):
        replacements = {
            "无": "無",
            "恒": "恆",
            "兑": "兌",
            "鹹": "咸",
            "誌": "志",
            "兇": "凶",
            "禦": "御",
            "贲": "賁",
            "複": "復",
        }
        for source, target in replacements.items():
            value = value.replace(source, target)
        return value
    if isinstance(value, list):
        return [_normalize_traditional(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize_traditional(item) for key, item in value.items()}
    return value


def import_classics(source_dir: Path, database: dict[str, dict[str, Any]]) -> None:
    CLASSICS_DIR.mkdir(parents=True, exist_ok=True)
    file_map = {
        "wen-yan.json": "wen_yan.json",
        "shuo-gua.json": "shuo_gua.json",
        "xi-ci.json": "xi_ci.json",
        "xu-gua.json": "xu_gua.json",
        "za-gua.json": "za_gua.json",
    }
    normalized_payloads: dict[str, Any] = {}
    for source_name, target_name in file_map.items():
        payload = _normalize_traditional(
            json.loads((source_dir / source_name).read_text(encoding="utf-8"))
        )
        normalized_payloads[target_name] = payload
        (CLASSICS_DIR / target_name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    wenyan = normalized_payloads["wen_yan.json"]
    for section in wenyan.get("content", []):
        subtitle = str(section.get("subtitle", ""))
        target = "乾為天" if subtitle == "乾" else "坤為地" if subtitle == "坤" else ""
        if target:
            database[target]["wenyan_text"] = "\n".join(str(item) for item in section.get("content", []))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--package-json",
        type=Path,
        help="Optional @freizl/yijing zh-TW/64gua.json; avoids live network refresh.",
    )
    parser.add_argument(
        "--classics-dir",
        type=Path,
        help="Optional @freizl/yijing zh-TW directory for 文言、說卦、繫辭、序卦、雜卦.",
    )
    args = parser.parse_args()
    database = build_database(args.package_json)
    if args.classics_dir is not None:
        import_classics(args.classics_dir, database)
    validate_database(database)
    HEXAGRAM_PATH.write_text(
        json.dumps(database, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    line_count = sum(len(item["lines"]) for item in database.values())
    print(f"Wrote {len(database)} hexagrams and {line_count} line records to {HEXAGRAM_PATH}")


if __name__ == "__main__":
    main()
