from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HEXAGRAM_PATH = ROOT / "knowledge" / "meihua_hexagrams.json"
ZHOUYI_ROOT = ROOT / "knowledge" / "zhouyi"
CORPUS_PATH = ZHOUYI_ROOT / "corpus.json"
MANIFEST_PATH = ZHOUYI_ROOT / "manifest.json"

UPSTREAM_REPO = "kanripo/KR1a0001"
UPSTREAM_COMMIT = "8284adbf9e3435d713180e24f05bf75f8b7d1d96"
UPSTREAM_BASE = f"https://raw.githubusercontent.com/{UPSTREAM_REPO}/{UPSTREAM_COMMIT}"
UPSTREAM_EDITION = "Kanripo TLS digital transcription"
SOURCE_FILES = tuple(f"KR1a0001_{index:03d}.txt" for index in range(1, 65))

PAGE_RE = re.compile(r"^<pb:([^>]+)>¶?$")
HEADER_RE = re.compile(r"^\*\*\s*《(.+?)第([一二三四五六七八九十百]+)》")
LINE_RE = re.compile(r"^(初[六九]|[六九][二三四五]|上[六九])(?:[、：:]|\s)*(.*)$")
USE_RE = re.compile(r"^(用[六九])(?:[、：:]|\s)*(.*)$")


def _download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "JARVIS-Zhouyi-Corpus-Importer/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def _hexagrams() -> dict[int, dict[str, Any]]:
    rows = json.loads(HEXAGRAM_PATH.read_text(encoding="utf-8"))["hexagrams"]
    result = {int(row["number"]): row for row in rows}
    if set(result) != set(range(1, 65)):
        raise ValueError("梅花六十四卦 catalog 必須完整 1..64")
    return result


def _clean_piece(text: str) -> str:
    return re.sub(r"\s+", "", text.rstrip("¶").strip())


def _logical_rows(content: str) -> list[dict[str, str | None]]:
    rows: list[dict[str, str | None]] = []
    page: str | None = None
    for raw in content.splitlines():
        line = raw.strip()
        page_match = PAGE_RE.match(line)
        if page_match:
            page = page_match.group(1)
            continue
        if not line or line.startswith("#"):
            continue
        if line.startswith("#+"):
            continue
        cleaned = _clean_piece(line)
        if cleaned:
            rows.append({"text": cleaned, "page": page})
    return rows


def _join(rows: list[dict[str, str | None]], start: int, end: int) -> str:
    return "".join(str(row["text"]) for row in rows[start:end])


def _next_boundary(rows: list[dict[str, str | None]], start: int, *, allow_xiang: bool = True) -> int:
    for idx in range(start, len(rows)):
        text = str(rows[idx]["text"])
        if LINE_RE.match(text) or USE_RE.match(text) or text.startswith("《彖》曰") or text.startswith("《文言》曰"):
            return idx
        if allow_xiang and text.startswith("《象》曰"):
            return idx
    return len(rows)


def _parse_one(number: int, filename: str, content: str, project: dict[int, dict[str, Any]]) -> dict[str, Any]:
    rows = _logical_rows(content)
    header_idx = next((i for i, row in enumerate(rows) if HEADER_RE.match(str(row["text"]))), None)
    if header_idx is None:
        raise ValueError(f"{filename}: 找不到卦標題")
    header = HEADER_RE.match(str(rows[header_idx]["text"]))
    assert header is not None
    source_name = header.group(1)

    symbol_idx = header_idx + 1
    while symbol_idx < len(rows) and not str(rows[symbol_idx]["text"]).startswith(project[number]["symbol"]):
        symbol_idx += 1
    if symbol_idx >= len(rows):
        raise ValueError(f"{filename}: 找不到卦符 {project[number]['symbol']}")

    content_start = symbol_idx + 1
    guaci_idx = next(
        (i for i in range(content_start, len(rows)) if str(rows[i]["text"]).startswith(f"《{source_name}》")),
        None,
    )
    if guaci_idx is None:
        raise ValueError(f"{filename}: 找不到卦辭")
    guaci_end = _next_boundary(rows, guaci_idx + 1)
    guaci_raw = _join(rows, guaci_idx, guaci_end)
    guaci = guaci_raw.removeprefix(f"《{source_name}》")

    tuan_idx = next((i for i in range(content_start, len(rows)) if str(rows[i]["text"]).startswith("《彖》曰")), None)
    tuan = None
    tuan_page = None
    if tuan_idx is not None:
        tuan_end = _next_boundary(rows, tuan_idx + 1)
        tuan = _join(rows, tuan_idx, tuan_end).removeprefix("《彖》曰")
        tuan_page = rows[tuan_idx]["page"]

    first_line_idx = next((i for i in range(content_start, len(rows)) if LINE_RE.match(str(rows[i]["text"]))), len(rows))
    xiang_candidates = [
        i for i in range(content_start, len(rows))
        if str(rows[i]["text"]).startswith("《象》曰")
    ]
    big_xiang_idx = next((i for i in xiang_candidates if i < first_line_idx), None)
    if big_xiang_idx is None and number == 1 and xiang_candidates:
        # The received 乾 transcription groups 大象 and six 小象 in one later block.
        big_xiang_idx = xiang_candidates[0]
    big_xiang = None
    big_xiang_page = None
    if big_xiang_idx is not None:
        big_xiang_end = _next_boundary(rows, big_xiang_idx + 1, allow_xiang=False)
        big_xiang = _join(rows, big_xiang_idx, big_xiang_end).removeprefix("《象》曰")
        big_xiang_page = rows[big_xiang_idx]["page"]

    lines: list[dict[str, Any]] = []
    use_line: dict[str, Any] | None = None
    for idx in range(content_start, len(rows)):
        text = str(rows[idx]["text"])
        match = LINE_RE.match(text)
        use_match = USE_RE.match(text)
        if not match and not use_match:
            continue
        marker, inline = (match or use_match).groups()  # type: ignore[union-attr]
        end = _next_boundary(rows, idx + 1)
        body = inline + _join(rows, idx + 1, end)
        record = {
            "marker": marker,
            "classical_text": body,
            "source_page_start": rows[idx]["page"],
        }
        if use_match:
            use_line = record
        else:
            record["line"] = len(lines) + 1
            lines.append(record)

    if len(lines) != 6:
        raise ValueError(f"{filename}: 標準爻辭應為 6 條，解析得到 {len(lines)}")

    raw_classical = "".join(
        str(row["text"])
        for row in rows[content_start:]
        if not str(row["text"]).startswith("**")
    )
    source_bytes = content.encode("utf-8")
    return {
        "number": number,
        "name": project[number]["name"],
        "symbol": project[number]["symbol"],
        "upper": project[number]["upper"],
        "lower": project[number]["lower"],
        "source_name": source_name,
        "guaci": {"classical_text": guaci, "source_page_start": rows[guaci_idx]["page"]},
        "tuan": {"classical_text": tuan, "source_page_start": tuan_page},
        "xiang": {
            "classical_text": big_xiang,
            "source_page_start": big_xiang_page,
            "note": "乾卦來源把大象與六小象合在同一象傳 block；保留整段，不擅自切分。" if number == 1 else None,
        },
        "lines": lines,
        "use_line": use_line,
        "raw_classical_transcription": raw_classical,
        "source": {
            "repository": UPSTREAM_REPO,
            "commit": UPSTREAM_COMMIT,
            "edition": UPSTREAM_EDITION,
            "file": filename,
            "sha256": hashlib.sha256(source_bytes).hexdigest(),
        },
        "review_status": "SOURCE_TRANSCRIPTION_PARSED__INTERPRETATION_SEPARATE",
    }


def build_corpus() -> tuple[dict[str, Any], dict[str, Any]]:
    project = _hexagrams()
    entries: list[dict[str, Any]] = []
    source_hashes: dict[str, str] = {}
    for number, filename in enumerate(SOURCE_FILES, 1):
        raw = _download(f"{UPSTREAM_BASE}/{filename}")
        source_hashes[filename] = hashlib.sha256(raw).hexdigest()
        entries.append(_parse_one(number, filename, raw.decode("utf-8"), project))

    standard_lines = [line for entry in entries for line in entry["lines"]]
    if len(entries) != 64 or len(standard_lines) != 384:
        raise ValueError("周易 corpus 必須恰為 64 卦 / 384 標準爻")

    corpus = {
        "schema_version": "stark-zhouyi-corpus-v1.0.0",
        "source_id": "zhouyi-kanripo-tls-transcription",
        "source_repository": UPSTREAM_REPO,
        "source_commit": UPSTREAM_COMMIT,
        "source_edition": UPSTREAM_EDITION,
        "textual_policy": [
            "本檔保存固定來源的數位轉錄與結構化切分，不宣稱完成所有版本校勘。",
            "古籍原文、後世注解、JARVIS 專案解析與足球 modern application 必須分層。",
            "不得用 AI 補寫缺失經文或靜默改字。",
        ],
        "hexagrams": entries,
    }
    manifest = {
        "schema_version": "stark-zhouyi-manifest-v1.0.0",
        "source_repository": UPSTREAM_REPO,
        "source_commit": UPSTREAM_COMMIT,
        "source_edition": UPSTREAM_EDITION,
        "source_files": source_hashes,
        "expected_hexagrams": 64,
        "materialized_hexagrams": len(entries),
        "expected_standard_lines": 384,
        "materialized_standard_lines": len(standard_lines),
        "use_lines": sum(entry["use_line"] is not None for entry in entries),
        "completion_status": "64_HEXAGRAMS__384_STANDARD_LINES__BASE_TRANSCRIPTION_COMPLETE",
    }
    return corpus, manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Validate generated output against committed corpus")
    args = parser.parse_args()
    corpus, manifest = build_corpus()
    encoded_corpus = json.dumps(corpus, ensure_ascii=False, indent=2) + "\n"
    encoded_manifest = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not CORPUS_PATH.exists() or CORPUS_PATH.read_text(encoding="utf-8") != encoded_corpus:
            raise SystemExit("committed Zhouyi corpus differs from reproducible import")
        if not MANIFEST_PATH.exists() or MANIFEST_PATH.read_text(encoding="utf-8") != encoded_manifest:
            raise SystemExit("committed Zhouyi manifest differs from reproducible import")
        print("Zhouyi corpus reproducibility check passed")
        return
    ZHOUYI_ROOT.mkdir(parents=True, exist_ok=True)
    CORPUS_PATH.write_text(encoded_corpus, encoding="utf-8")
    MANIFEST_PATH.write_text(encoded_manifest, encoding="utf-8")
    print("materialized Zhouyi corpus: 64 hexagrams / 384 standard lines")


if __name__ == "__main__":
    main()
