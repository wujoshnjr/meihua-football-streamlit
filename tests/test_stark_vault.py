from itertools import product

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
    assert stats["meihua_trigrams"] == 8
    assert stats["meihua_hexagrams"] == 64
    assert stats["meihua_body_use_relations"] == 5
    assert stats["meihua_line_roles"] == 6


def test_all_64_upper_lower_hexagram_combinations_are_addressable():
    rows = [meihua_hexagram(upper, lower) for upper, lower in product(TRIGRAMS, repeat=2)]
    assert len(rows) == 64
    assert len({row["number"] for row in rows}) == 64
    assert len({row["name"] for row in rows}) == 64
    assert all(row["summary"] and row["football"] for row in rows)


def test_vault_search_covers_qimen_and_meihua_football_semantics():
    qimen_results = search_vault("高位壓迫")
    meihua_results = search_vault("未濟")

    assert any(row["system"] == "QIMEN_DUNJIA" for row in qimen_results)
    assert any(row["system"] == "MEIHUA_YISHU" and row.get("name") == "未濟" for row in meihua_results)
