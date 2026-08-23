from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from yuanling.riqimen import riqimen_60_day_table
from yuanling.stars import star_registry_audit


ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_ROOT = ROOT / "knowledge"
SOURCE_CATALOG_PATH = KNOWLEDGE_ROOT / "yuanling_source_catalog.json"
EXTENDED_SOURCE_CATALOG_PATH = KNOWLEDGE_ROOT / "yuanling_extended_source_catalog.json"
WORK_INDEX_PATH = KNOWLEDGE_ROOT / "yuanling_work_index.json"
CASTING_REFERENCE_PATH = KNOWLEDGE_ROOT / "yuanling_casting_reference.json"
CASTING_CATALOG_PATH = KNOWLEDGE_ROOT / "casting_method_catalog.json"

SEARCH_ALIASES = {
    "年月日時起卦": ("MEIHUA_YEAR_MONTH_DAY_HOUR", "年月日時先天數法"),
    "梅花起卦": ("MEIHUA_YEAR_MONTH_DAY_HOUR", "年月日時先天數法"),
    "奇門起局": ("QIMEN_SHIJIA_ZHUANPAN_CHAIBU", "時家奇門", "奇門起例"),
    "時家奇門": ("QIMEN_SHIJIA_ZHUANPAN_CHAIBU",),
    "元靈奇門起例": ("YUANLING_QIMEN_CASTING_REFERENCE", "奇門起例"),
    "演數起法": ("YUANLING_YANSHU_QIYAO_RAW", "演數七要"),
    "七要起法": ("YUANLING_YANSHU_QIYAO_RAW", "演數七要"),
    "日奇門起局": ("YUANLING_RI_QIMEN", "日奇門"),
    "截路空亡": ("TIME_VOID_RULE", "cutoff_void"),
    "八門值事": ("DOOR_SOURCE_PROFILE",),
    "十干吉凶宜忌": ("STEM_SOURCE_PROFILE",),
    "九星克應": ("NUMERIC_STAR_RESPONSE_SOURCE_PROFILE",),
    "九遁": ("SPECIAL_PATTERN_SOURCE_SECTION",),
    "占勝敗": ("占勝敗", "INDEXED_HIGH_PRIORITY_FOR_COMPETITION_RESEARCH"),
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _source_catalogs() -> tuple[dict[str, Any], dict[str, Any]]:
    return _load(SOURCE_CATALOG_PATH), _load(EXTENDED_SOURCE_CATALOG_PATH)


def yuanling_catalog_stats() -> dict[str, Any]:
    source, extended = _source_catalogs()
    work_index = _load(WORK_INDEX_PATH)
    casting = _load(CASTING_CATALOG_PATH)
    base_sections = list(source.get("sections", []))
    extended_sections = list(extended.get("sections", []))
    yuanling_methods = [
        row
        for row in casting.get("methods", [])
        if str(row.get("system", "")).startswith("YUANLING")
    ]
    unresolved = sum(len(row.get("unresolved", [])) for row in [*base_sections, *extended_sections])
    coverage = extended.get("coverage", {})
    return {
        # Backward-compatible field: existing validator treats this as the core catalog count.
        "structured_sections": len(base_sections),
        "combined_structured_sections": len(base_sections) + len(extended_sections),
        "extended_structured_sections": len(extended_sections),
        "work_volumes_indexed": len(work_index.get("volumes", [])),
        "numeric_stars": int(star_registry_audit()["count"]),
        "riqimen_day_rows": len(riqimen_60_day_table()),
        "yuanling_methods": len(yuanling_methods),
        "unresolved_source_points": unresolved,
        "preheaven_relation_markers": int(source.get("completion", {}).get("preheaven_relation_markers", 0)),
        "door_source_profiles": int(coverage.get("door_source_profiles", 0)),
        "palace_source_profiles": int(coverage.get("palace_source_profiles", 0)),
        "stem_source_profiles": int(coverage.get("stem_source_profiles", 0)),
        "response_star_profiles": int(coverage.get("response_star_profiles", 0)),
        "source_schema": source.get("schema_version"),
        "extended_source_schema": extended.get("schema_version"),
        "work_index_schema": work_index.get("schema_version"),
        "casting_reference_schema": _load(CASTING_REFERENCE_PATH).get("schema_version"),
        "casting_schema": casting.get("schema_version"),
    }


def _matches(row: dict[str, Any], query: str) -> bool:
    haystack = json.dumps(row, ensure_ascii=False).lower()
    needle = query.lower()
    if needle in haystack:
        return True
    aliases = SEARCH_ALIASES.get(query.strip(), ())
    return any(alias.lower() in haystack for alias in aliases)


def _source_result(row: dict[str, Any], catalog_tier: str) -> dict[str, Any]:
    return {
        "system": "YUANLING",
        "family": row.get("family", "source_section"),
        "key": row.get("id"),
        "name": row.get("name"),
        "volume": row.get("volume"),
        "source_locator": row.get("source_locator"),
        "authority": row.get("authority"),
        "catalog_tier": catalog_tier,
        "summary": row.get("summary"),
        "machine_facts": row.get("machine_facts"),
        "unresolved": row.get("unresolved", []),
        "caution": row.get("caution"),
    }


def search_yuanling(query: str, *, limit: int = 60) -> list[dict[str, Any]]:
    needle = query.strip()
    if not needle:
        return []

    source, extended = _source_catalogs()
    casting = _load(CASTING_CATALOG_PATH)
    casting_reference = _load(CASTING_REFERENCE_PATH)
    work_index = _load(WORK_INDEX_PATH)
    found: list[dict[str, Any]] = []

    for tier, catalog in (("CORE_SOURCE", source), ("EXTENDED_SOURCE", extended)):
        for row in catalog.get("sections", []):
            if _matches(row, needle):
                found.append(_source_result(row, tier))
            if len(found) >= limit:
                return found

    for row in casting_reference.get("methods", []):
        if _matches(row, needle):
            found.append(
                {
                    "system": "YUANLING_METHOD_REFERENCE",
                    "family": "CASTING_REFERENCE",
                    "key": row.get("id"),
                    "name": row.get("display_name"),
                    **row,
                }
            )
        if len(found) >= limit:
            return found

    for row in work_index.get("volumes", []):
        if _matches(row, needle):
            found.append(
                {
                    "system": "YUANLING",
                    "family": "WORK_TABLE_OF_CONTENTS",
                    "key": f"yuanling.work.volume.{int(row['volume']):02d}",
                    "name": f"卷{row['volume']}",
                    "authority": work_index.get("authority"),
                    **row,
                    "caution": work_index.get("boundary"),
                }
            )
        if len(found) >= limit:
            return found

    for row in casting.get("methods", []):
        if _matches(row, needle):
            found.append(
                {
                    "system": "CASTING_METHOD",
                    "family": row.get("system"),
                    "key": row.get("id"),
                    "name": row.get("display_name"),
                    "status": row.get("status"),
                    "required_inputs": row.get("required_inputs", []),
                    "casting_steps": row.get("casting_steps", []),
                    "primary_outputs": row.get("primary_outputs", []),
                    "interpretation_role": row.get("interpretation_role"),
                    "boundary": row.get("boundary"),
                }
            )
        if len(found) >= limit:
            return found

    for row in star_registry_audit()["stars"]:
        if _matches(row, needle):
            found.append(
                {
                    "system": "YUANLING",
                    "family": "NUMERIC_STAR_REGISTRY",
                    "key": f"yuanling.numeric_star.{row['number']}",
                    "name": row["color_name"],
                    **row,
                }
            )
        if len(found) >= limit:
            return found

    for row in riqimen_60_day_table():
        if _matches(row, needle):
            found.append(
                {
                    "system": "YUANLING",
                    "family": "RIQIMEN_60_DAY_REST_DOOR_TABLE",
                    "key": f"yuanling.riqimen.day.{row['day_index']:02d}",
                    "name": row["day_ganzhi"],
                    **row,
                }
            )
        if len(found) >= limit:
            return found

    return found


def casting_method(method_id: str) -> dict[str, Any]:
    catalog = _load(CASTING_CATALOG_PATH)
    for row in catalog.get("methods", []):
        if row.get("id") == method_id:
            return row
    raise KeyError(f"找不到起局/起卦方法：{method_id}")


def casting_reference(method_id: str) -> dict[str, Any]:
    catalog = _load(CASTING_REFERENCE_PATH)
    for row in catalog.get("methods", []):
        if row.get("id") == method_id:
            return row
    raise KeyError(f"找不到元靈方法參考：{method_id}")


def source_section(section_id: str) -> dict[str, Any]:
    for catalog in _source_catalogs():
        for row in catalog.get("sections", []):
            if row.get("id") == section_id:
                return row
    raise KeyError(f"找不到元靈原典條目：{section_id}")


def yuanling_packet_knowledge_context(mode: str) -> dict[str, Any]:
    # V1 packet context remains schema-compatible; richer source sections can be appended.
    section_ids = [
        "yuanling.vol1.qiyao",
        "yuanling.vol1.number_chief_song",
        "yuanling.vol2.eight_doors_affairs",
        "yuanling.vol2.ten_stem_judgments",
        "yuanling.vol3.shortcut_numeric_star_door",
        "yuanling.vol3.nine_star_response",
        "yuanling.vol3.value_day_nine_stars",
        "yuanling.vol3.shefu_numeric_associations",
    ]
    if mode == "RIQIMEN_QIYAO_EXPERIMENT":
        section_ids.extend(
            [
                "yuanling.vol1.riqimen",
                "yuanling.vol1.solar_term_ju",
                "yuanling.vol1.three_yuan_head",
                "yuanling.vol1.cutoff_void",
                "yuanling.vol2.nine_palace_chief_profiles",
            ]
        )

    return {
        "kind": "YUANLING_PACKET_KNOWLEDGE_CONTEXT_V1",
        "method": casting_method("YUANLING_YANSHU_QIYAO_RAW"),
        "source_sections": [source_section(section_id) for section_id in section_ids],
        "riqimen_method": (
            casting_method("YUANLING_RI_QIMEN")
            if mode == "RIQIMEN_QIYAO_EXPERIMENT"
            else None
        ),
        "source_catalog_schema": _load(SOURCE_CATALOG_PATH).get("schema_version"),
        "casting_catalog_schema": _load(CASTING_CATALOG_PATH).get("schema_version"),
        "boundary": (
            "此 context 是 source-aware 方法與語義資料，不是比分公式。"
            "新增卷二門干與卷三星義只作條件式 context；射覆數目、值日星吉凶與旁證候選均不得直接轉成足球進球或勝率。"
        ),
    }


def football_question_templates() -> dict[str, str]:
    catalog = _load(CASTING_CATALOG_PATH)
    return dict(catalog.get("football_question_templates", {}))
