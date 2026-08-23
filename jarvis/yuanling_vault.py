from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from yuanling.riqimen import riqimen_60_day_table
from yuanling.stars import star_registry_audit


ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_ROOT = ROOT / "knowledge"
SOURCE_CATALOG_PATH = KNOWLEDGE_ROOT / "yuanling_source_catalog.json"
CASTING_CATALOG_PATH = KNOWLEDGE_ROOT / "casting_method_catalog.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def yuanling_catalog_stats() -> dict[str, Any]:
    source = _load(SOURCE_CATALOG_PATH)
    casting = _load(CASTING_CATALOG_PATH)
    sections = list(source.get("sections", []))
    yuanling_methods = [
        row
        for row in casting.get("methods", [])
        if str(row.get("system", "")).startswith("YUANLING")
    ]
    unresolved = sum(len(row.get("unresolved", [])) for row in sections)
    return {
        "structured_sections": len(sections),
        "numeric_stars": int(star_registry_audit()["count"]),
        "riqimen_day_rows": len(riqimen_60_day_table()),
        "yuanling_methods": len(yuanling_methods),
        "unresolved_source_points": unresolved,
        "source_schema": source.get("schema_version"),
        "casting_schema": casting.get("schema_version"),
    }


def _matches(row: dict[str, Any], query: str) -> bool:
    haystack = json.dumps(row, ensure_ascii=False).lower()
    return query.lower() in haystack


def search_yuanling(query: str, *, limit: int = 40) -> list[dict[str, Any]]:
    needle = query.strip()
    if not needle:
        return []

    source = _load(SOURCE_CATALOG_PATH)
    casting = _load(CASTING_CATALOG_PATH)
    found: list[dict[str, Any]] = []

    for row in source.get("sections", []):
        if _matches(row, needle):
            found.append(
                {
                    "system": "YUANLING",
                    "family": row.get("family", "source_section"),
                    "key": row.get("id"),
                    "name": row.get("name"),
                    "volume": row.get("volume"),
                    "source_locator": row.get("source_locator"),
                    "authority": row.get("authority"),
                    "summary": row.get("summary"),
                    "machine_facts": row.get("machine_facts"),
                    "unresolved": row.get("unresolved", []),
                    "caution": row.get("caution"),
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


def source_section(section_id: str) -> dict[str, Any]:
    catalog = _load(SOURCE_CATALOG_PATH)
    for row in catalog.get("sections", []):
        if row.get("id") == section_id:
            return row
    raise KeyError(f"找不到元靈原典條目：{section_id}")


def yuanling_packet_knowledge_context(mode: str) -> dict[str, Any]:
    section_ids = [
        "yuanling.vol1.qiyao",
        "yuanling.vol1.number_chief_song",
        "yuanling.vol3.value_day_nine_stars",
        "yuanling.vol3.shefu_numeric_associations",
    ]
    method_id = "YUANLING_YANSHU_QIYAO_RAW"
    if mode == "RIQIMEN_QIYAO_EXPERIMENT":
        section_ids.extend(
            [
                "yuanling.vol1.riqimen",
                "yuanling.vol1.solar_term_ju",
                "yuanling.vol1.three_yuan_head",
            ]
        )

    return {
        "kind": "YUANLING_PACKET_KNOWLEDGE_CONTEXT_V1",
        "method": casting_method(method_id),
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
            "射覆數目關聯、值日星吉凶與旁證候選均不得直接轉成足球進球或勝率。"
        ),
    }


def football_question_templates() -> dict[str, str]:
    catalog = _load(CASTING_CATALOG_PATH)
    return dict(catalog.get("football_question_templates", {}))
