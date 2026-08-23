from __future__ import annotations

from jarvis.yuanling_vault import casting_reference, search_yuanling, yuanling_catalog_stats


def test_expanded_yuanling_database_counts_are_visible() -> None:
    stats = yuanling_catalog_stats()
    assert stats["structured_sections"] == 18
    assert stats["extended_structured_sections"] == 9
    assert stats["combined_structured_sections"] == 27
    assert stats["work_volumes_indexed"] == 24
    assert stats["door_source_profiles"] == 8
    assert stats["palace_source_profiles"] == 9
    assert stats["stem_source_profiles"] == 10
    assert stats["response_star_profiles"] == 9


def test_expanded_yuanling_search_reaches_new_source_layers() -> None:
    cutoff = search_yuanling("截路空亡")
    assert any(row.get("key") == "yuanling.vol1.cutoff_void" for row in cutoff)

    doors = search_yuanling("八門值事")
    assert any(row.get("key") == "yuanling.vol2.eight_doors_affairs" for row in doors)

    stars = search_yuanling("九星克應")
    assert any(row.get("key") == "yuanling.vol3.nine_star_response" for row in stars)

    winloss = search_yuanling("占勝敗")
    assert any(row.get("family") == "WORK_TABLE_OF_CONTENTS" and row.get("volume") == 24 for row in winloss)


def test_yuanling_casting_reference_keeps_methods_separate() -> None:
    qimen_ref = casting_reference("YUANLING_QIMEN_CASTING_REFERENCE")
    qiyao = casting_reference("YUANLING_YANSHU_QIYAO_RAW")
    riqimen = casting_reference("YUANLING_RI_QIMEN")

    assert qimen_ref["status"] == "SOURCE_REFERENCE_NOT_SEPARATE_PRODUCTION_ENGINE"
    assert qiyao["status"] == "RESEARCH_ALPHA"
    assert qiyao["seven_factors"] == ["數宮", "數主", "飛星", "入門", "直日星", "日干", "時支"]
    assert riqimen["status"] == "PARTIAL_RESEARCH_ALPHA"
    assert "穿宮數去" in "".join(riqimen["steps"])
