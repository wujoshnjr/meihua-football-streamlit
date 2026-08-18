from itertools import product

from jarvis.qimen_relations import all_relations
from jarvis.stark_vault import meihua_hexagram, search_vault, vault_stats


TRIGRAMS = ("乾", "兌", "離", "震", "巽", "坎", "艮", "坤")


def test_vault_has_full_core_catalogs():
    stats = vault_stats()
    assert stats["qimen_palaces"] == 9
    assert stats["qimen_doors"] == 8
    assert stats["qimen_stars"] == 9
    assert stats["qimen_deities"] == 8
    assert stats["qimen_stems"] == 10
    assert stats["qimen_patterns"] > 0
    assert stats["qimen_relations"] == 306
    assert stats["qimen_deep_layers"] == 8
    assert stats["qimen_deity_modulations"] == 8
    assert stats["meihua_trigrams"] == 8
    assert stats["meihua_hexagrams"] == 64
    assert stats["meihua_body_use_relations"] == 5
    assert stats["meihua_line_roles"] == 6
    assert stats["meihua_deep_dimensions"] == 8


def test_qimen_complete_relation_matrix_has_306_unique_slots():
    rows = all_relations()
    assert len(rows) == 306
    assert len({row.key for row in rows}) == 306
    counts = {
        relation_type: sum(row.relation_type == relation_type for row in rows)
        for relation_type in ("stem_pair", "star_door", "door_palace", "star_palace")
    }
    assert counts == {
        "stem_pair": 81,
        "star_door": 72,
        "door_palace": 72,
        "star_palace": 81,
    }
    assert all(row.football_meaning for row in rows)
    assert all(row.observable_signals and row.counter_signals for row in rows)


def test_all_64_upper_lower_hexagram_combinations_are_addressable():
    rows = [meihua_hexagram(upper, lower) for upper, lower in product(TRIGRAMS, repeat=2)]
    assert len(rows) == 64
    assert len({row["number"] for row in rows}) == 64
    assert len({row["name"] for row in rows}) == 64
    assert all(row["summary"] and row["football"] for row in rows)


def test_vault_search_covers_deep_qimen_and_meihua_semantics():
    qimen_results = search_vault("高位壓迫")
    meihua_results = search_vault("終局極限")

    assert any(
        row["system"] == "QIMEN_DUNJIA" and row["family"] == "deep:deity_modulation"
        for row in qimen_results
    )
    assert any(
        row["system"] == "MEIHUA_YISHU" and row["family"] == "deep:moving_line"
        for row in meihua_results
    )


def test_vault_search_still_covers_named_classics_and_hexagrams():
    qimen_results = search_vault("青龍返首")
    meihua_results = search_vault("未濟")

    assert any(row["system"] == "QIMEN_DUNJIA" and row.get("classical_pattern") == "青龍返首" for row in qimen_results)
    assert any(row["system"] == "MEIHUA_YISHU" and row.get("name") == "未濟" for row in meihua_results)
