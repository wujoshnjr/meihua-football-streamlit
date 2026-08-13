from __future__ import annotations

from qimen.knowledge import knowledge_stats, load_knowledge, search_knowledge


def test_knowledge_base_has_complete_core_sets():
    stats = knowledge_stats()
    assert stats["palaces"] == 9
    assert stats["doors"] == 8
    assert stats["stars"] == 9
    assert stats["deities"] == 8
    assert stats["stems"] == 10
    assert stats["earthly_branches"] == 12
    assert stats["solar_terms"] == 24
    assert stats["six_xun"] == 6
    assert stats["patterns"] >= 39
    assert stats["football_patterns"] == 39
    assert stats["dimensions"] == 20
    assert stats["total"] >= 380


def test_search_crosses_files_and_sections():
    assert any(row["_title"] == "值符" for row in search_knowledge("值符"))
    assert any(row["_title"] == "門迫" for row in search_knowledge("門迫", "patterns"))
    assert search_knowledge("不存在的奇門條目XYZ") == []


def test_all_knowledge_files_are_versioned():
    for payload in load_knowledge()["files"].values():
        assert payload["schema_version"].startswith("qimen-")


def test_pattern_source_ids_exist():
    files = load_knowledge()["files"]
    sources = {item["id"] for item in files["sources.json"]["sources"]}
    assert all(item["source_id"] in sources for item in files["patterns.json"]["patterns"])
