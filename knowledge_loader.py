from __future__ import annotations

import json
import re
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
YILIN_PUNCTUATION_RE = re.compile(r"[，。；！？：、]")


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
def load_hexagram_interpretations() -> dict[str, Any]:
    payload = _load_json(KNOWLEDGE_DIR / "hexagram_interpretations.json")
    hexagrams = load_hexagrams()
    entries = payload.get("hexagrams") if isinstance(payload, dict) else None
    classical_fields = payload.get("classical_fields") if isinstance(payload, dict) else None
    football_fields = payload.get("football_fields") if isinstance(payload, dict) else None
    if not isinstance(entries, dict) or set(entries) != set(hexagrams):
        raise ValueError("hexagram_interpretations.json 必須完整包含六十四卦")
    if not isinstance(classical_fields, list) or len(classical_fields) != 6:
        raise ValueError("每卦必須固定包含六個傳統卦義欄位")
    if not isinstance(football_fields, list) or len(football_fields) != 9:
        raise ValueError("每卦必須固定包含九個足球情境欄位")
    for name, entry in entries.items():
        if int(entry.get("sequence", 0)) != int(hexagrams[name]["sequence"]):
            raise ValueError(f"{name} 的卦序與六十四卦資料庫不一致")
        classical = entry.get("classical_meaning")
        football = entry.get("football_mapping")
        if not isinstance(classical, dict) or set(classical) != set(classical_fields):
            raise ValueError(f"{name} 的傳統卦義欄位不完整")
        if not isinstance(football, dict) or set(football) != set(football_fields):
            raise ValueError(f"{name} 的足球情境欄位不完整")
        if any(not isinstance(value, str) or not value.strip() for value in classical.values()):
            raise ValueError(f"{name} 的傳統卦義含空白內容")
        if any(not isinstance(value, str) or not value.strip() for value in football.values()):
            raise ValueError(f"{name} 的足球情境含空白內容")
    if payload.get("entry_count") != 64:
        raise ValueError("六十四卦詮釋資料筆數必須為 64")
    return payload


@lru_cache(maxsize=1)
def load_conditional_trigram_meanings() -> dict[str, Any]:
    payload = _load_json(KNOWLEDGE_DIR / "conditional_trigram_meanings.json")
    trigrams = load_trigrams()
    entries = payload.get("trigrams") if isinstance(payload, dict) else None
    definitions = payload.get("signal_definitions") if isinstance(payload, dict) else None
    if not isinstance(entries, dict) or set(entries) != set(trigrams):
        raise ValueError("conditional_trigram_meanings.json 必須完整包含八個經卦")
    if not isinstance(definitions, dict) or not definitions:
        raise ValueError("條件式卦義庫必須定義可稽核判斷訊號")
    rule_ids: set[str] = set()
    for name, entry in entries.items():
        meanings = entry.get("possible_meanings")
        rules = entry.get("rules")
        if not isinstance(meanings, list) or len(meanings) < 8:
            raise ValueError(f"{name} 必須至少包含八個可能義項")
        if not isinstance(rules, list) or len(rules) < 6:
            raise ValueError(f"{name} 必須至少包含六條條件規則")
        meaning_names = {
            str(item.get("name", "")).strip()
            for item in meanings
            if isinstance(item, dict)
        }
        if len(meaning_names) != len(meanings) or "" in meaning_names:
            raise ValueError(f"{name} 的可能義項名稱重複或空白")
        if any(not str(item.get("football", "")).strip() for item in meanings):
            raise ValueError(f"{name} 的足球義項不可空白")
        for rule in rules:
            rule_id = str(rule.get("id", "")).strip()
            if not rule_id or rule_id in rule_ids:
                raise ValueError(f"條件規則 ID 重複或空白：{rule_id}")
            rule_ids.add(rule_id)
            used_signals = {
                str(signal)
                for key in ("all", "any", "none")
                for signal in rule.get(key, [])
            }
            if not used_signals.issubset(definitions):
                unknown = sorted(used_signals - set(definitions))
                raise ValueError(f"{name}/{rule_id} 使用未知訊號：{unknown}")
            preferred = set(rule.get("prefer", []))
            suppressed = set(rule.get("suppress", []))
            if not preferred or not (preferred | suppressed).issubset(meaning_names):
                raise ValueError(f"{name}/{rule_id} 的義項索引無效")
            if not str(rule.get("condition_text", "")).strip():
                raise ValueError(f"{name}/{rule_id} 缺少判斷條件文字")
            if not str(rule.get("football_reading", "")).strip():
                raise ValueError(f"{name}/{rule_id} 缺少足球閱讀說明")
    if payload.get("entry_count") != 8:
        raise ValueError("條件式經卦資料筆數必須為 8")
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
        if any(
            not YILIN_PUNCTUATION_RE.search(text) or text[-1] not in "。！？"
            for text in changed_entries.values()
        ):
            raise ValueError(f"焦氏易林「{main_name}之」章含有未完整標點的林辭")
    if payload.get("entry_count") != 4096 or payload.get("punctuated_entry_count") != 4096:
        raise ValueError("焦氏易林必須完整包含 64×64＝4,096 條林辭")
    return payload


def build_jiaoshi_yilin_reference(main_name: str, changed_name: str) -> dict[str, Any]:
    """Return the exact punctuated Yi Lin entry and its auditable provenance."""

    hexagrams = load_hexagrams()
    yilin = load_jiaoshi_yilin()
    main = hexagrams[main_name]
    changed = hexagrams[changed_name]
    main_short = str(main["short_name"])
    changed_short = str(changed["short_name"])
    completion_note = next(
        (
            note
            for note in yilin.get("source_completion_notes", [])
            if note.get("main_hexagram") == main_short
            and note.get("changed_hexagram") == changed_short
        ),
        None,
    )
    return {
        "title": yilin["title"],
        "author": yilin["author"],
        "edition": yilin["edition"],
        "text_style": yilin["text_style"],
        "entry_key": f"{main_short}之{changed_short}",
        "main_hexagram": {
            "name": main_name,
            "short_name": main_short,
            "sequence": int(main["sequence"]),
            "unicode": str(main["unicode"]),
            "binary_bottom_up": str(main["binary_bottom_up"]),
        },
        "changed_hexagram": {
            "name": changed_name,
            "short_name": changed_short,
            "sequence": int(changed["sequence"]),
            "unicode": str(changed["unicode"]),
            "binary_bottom_up": str(changed["binary_bottom_up"]),
        },
        "text": yilin["entries"][main_short][changed_short],
        "source": yilin["source"],
        "base_source": yilin["base_source"],
        "source_completion_note": completion_note,
    }


def knowledge_completeness() -> dict[str, Any]:
    trigrams = load_trigrams()
    hexagrams = load_hexagrams()
    classics = load_classics()
    yilin = load_jiaoshi_yilin()
    interpretations = load_hexagram_interpretations()
    conditional = load_conditional_trigram_meanings()
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
        "interpretation_hexagrams": len(interpretations["hexagrams"]),
        "classical_meaning_fields": sum(
            len(item["classical_meaning"])
            for item in interpretations["hexagrams"].values()
        ),
        "football_mapping_fields": sum(
            len(item["football_mapping"])
            for item in interpretations["hexagrams"].values()
        ),
        "conditional_trigram_meanings": sum(
            len(item["possible_meanings"])
            for item in conditional["trigrams"].values()
        ),
        "conditional_trigram_rules": sum(
            len(item["rules"])
            for item in conditional["trigrams"].values()
        ),
        "is_complete": (
            len(trigrams) == 8
            and len(hexagrams) == 64
            and lines == 384
            and complete_hexagrams == 64
            and len(yilin["entries"]) == 64
            and yilin["entry_count"] == 4096
            and len(interpretations["hexagrams"]) == 64
            and all(
                len(item["classical_meaning"]) == 6
                and len(item["football_mapping"]) == 9
                for item in interpretations["hexagrams"].values()
            )
            and len(conditional["trigrams"]) == 8
            and all(
                len(item["possible_meanings"]) >= 8
                and len(item["rules"]) >= 6
                for item in conditional["trigrams"].values()
            )
        ),
    }


def clear_knowledge_cache() -> None:
    load_trigrams.cache_clear()
    load_hexagrams.cache_clear()
    load_hexagram_interpretations.cache_clear()
    load_conditional_trigram_meanings.cache_clear()
    load_meihua_principles.cache_clear()
    load_classics.cache_clear()
    load_jiaoshi_yilin.cache_clear()


__all__ = [
    "build_jiaoshi_yilin_reference",
    "clear_knowledge_cache",
    "knowledge_completeness",
    "load_classics",
    "load_conditional_trigram_meanings",
    "load_hexagrams",
    "load_hexagram_interpretations",
    "load_jiaoshi_yilin",
    "load_meihua_principles",
    "load_trigrams",
]
