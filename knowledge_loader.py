from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
CLASSICS_DIR = KNOWLEDGE_DIR / "classics"
CLASSIC_FILES = {
    "文言": "wen_yan.json",
    "說卦": "shuo_gua.json",
    "繫辭": "xi_ci.json",
    "序卦": "xu_gua.json",
    "雜卦": "za_gua.json",
}


def _load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"找不到知識庫檔案：{path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def load_trigrams() -> dict[str, dict[str, Any]]:
    payload = _load_json(KNOWLEDGE_DIR / "trigrams.json")
    if not isinstance(payload, dict) or len(payload) != 8:
        raise ValueError("trigrams.json 必須完整包含八個經卦")
    return payload


@lru_cache(maxsize=1)
def load_hexagrams() -> dict[str, dict[str, Any]]:
    payload = _load_json(KNOWLEDGE_DIR / "hexagrams.json")
    if not isinstance(payload, dict) or len(payload) != 64:
        raise ValueError("hexagrams.json 必須完整包含六十四卦")
    if sum(len(item.get("lines", [])) for item in payload.values()) != 384:
        raise ValueError("hexagrams.json 必須完整包含三百八十四爻")
    return payload


@lru_cache(maxsize=1)
def load_meihua_principles() -> dict[str, Any]:
    payload = _load_json(KNOWLEDGE_DIR / "meihua_principles.json")
    if not isinstance(payload, dict):
        raise ValueError("meihua_principles.json 必須是 JSON 物件")
    return payload


@lru_cache(maxsize=1)
def load_classics() -> dict[str, Any]:
    return {title: _load_json(CLASSICS_DIR / filename) for title, filename in CLASSIC_FILES.items()}


@lru_cache(maxsize=1)
def load_jiaoshi_yilin() -> dict[str, Any]:
    payload = _load_json(CLASSICS_DIR / "jiaoshi_yilin.json")
    if not isinstance(payload, dict):
        raise ValueError("jiaoshi_yilin.json 必須是 JSON 物件")

    ordered_hexagrams = sorted(load_hexagrams().values(), key=lambda item: int(item["sequence"]))
    expected_names = [str(item["short_name"]) for item in ordered_hexagrams]
    names = payload.get("hexagram_order")
    entries = payload.get("entries")
    if names != expected_names:
        raise ValueError("焦氏易林的 64 卦次序與周易知識庫不一致")
    if not isinstance(entries, dict) or set(entries) != set(expected_names):
        raise ValueError("焦氏易林必須完整包含 64 個本卦章節")
    for main_name in expected_names:
        changed_entries = entries.get(main_name)
        if not isinstance(changed_entries, dict) or set(changed_entries) != set(expected_names):
            raise ValueError(f"焦氏易林「{main_name}之」章必須完整包含 64 個之卦")
        if any(not isinstance(text, str) or not text.strip() for text in changed_entries.values()):
            raise ValueError(f"焦氏易林「{main_name}之」章含有空白林辭")
    if payload.get("entry_count") != 4096:
        raise ValueError("焦氏易林必須完整包含 64×64＝4,096 條林辭")
    return payload


def knowledge_completeness() -> dict[str, Any]:
    trigrams = load_trigrams()
    hexagrams = load_hexagrams()
    classics = load_classics()
    yilin = load_jiaoshi_yilin()
    lines = sum(len(item.get("lines", [])) for item in hexagrams.values())
    complete_hexagrams = sum(
        int(
            bool(item.get("judgment_text"))
            and bool(item.get("tuan_text"))
            and bool(item.get("great_image_text"))
            and len(item.get("lines", [])) == 6
            and all(line.get("classic_text") and line.get("small_image_text") for line in item["lines"])
        )
        for item in hexagrams.values()
    )
    return {
        "trigrams": len(trigrams),
        "hexagrams": len(hexagrams),
        "line_records": lines,
        "complete_hexagrams": complete_hexagrams,
        "classic_appendices": len(classics),
        "yilin_main_hexagrams": len(yilin["entries"]),
        "yilin_entries": sum(len(item) for item in yilin["entries"].values()),
        "is_complete": (
            len(trigrams) == 8
            and len(hexagrams) == 64
            and lines == 384
            and complete_hexagrams == 64
            and len(yilin["entries"]) == 64
            and yilin["entry_count"] == 4096
        ),
    }


def clear_knowledge_cache() -> None:
    load_trigrams.cache_clear()
    load_hexagrams.cache_clear()
    load_meihua_principles.cache_clear()
    load_classics.cache_clear()
    load_jiaoshi_yilin.cache_clear()


__all__ = [
    "clear_knowledge_cache",
    "knowledge_completeness",
    "load_classics",
    "load_hexagrams",
    "load_jiaoshi_yilin",
    "load_meihua_principles",
    "load_trigrams",
]
