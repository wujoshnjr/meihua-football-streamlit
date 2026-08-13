from __future__ import annotations

from itertools import product

import pytest

from qimen.football_ontology import (
    compose_football_meaning,
    football_ontology_stats,
    load_football_ontology,
    search_football_meanings,
)
from qimen.knowledge import load_knowledge


def test_all_atomic_qimen_units_have_football_meanings():
    ontology = load_football_ontology()
    stats = football_ontology_stats()
    assert stats["atomic_units"] == 108
    assert stats["breakdown"] == {
        "palaces": 9,
        "doors": 8,
        "stars": 9,
        "deities": 8,
        "stems": 10,
        "branches": 12,
        "seasonal_states": 5,
        "structural_states": 8,
        "patterns": 39,
    }
    for mappings in ontology["mappings"].values():
        for item in mappings:
            assert item["dimensions"]
            assert item["possible_meanings"]
            assert item["observable_signals"]
            assert item["counter_signals"]


def test_ontology_keys_match_classical_knowledge_sets():
    files = load_knowledge()["files"]
    ontology = files["football_ontology.json"]["mappings"]
    entities = files["entities.json"]
    calendar = files["calendar.json"]
    patterns = files["patterns.json"]
    for section in ("palaces", "doors", "stars", "deities", "stems"):
        assert {item["key"] for item in ontology[section]} == {item["key"] for item in entities[section]}
    assert {item["key"] for item in ontology["branches"]} == {
        item["name"] for item in calendar["earthly_branches"]
    }
    assert {item["key"] for item in ontology["patterns"]} == {
        item["name"] for item in patterns["patterns"]
    }


def test_football_terms_reverse_search_across_symbol_layers():
    pressing = search_football_meanings("高位逼搶")
    assert {item["key"] for item in pressing}.issuperset({"震三宮", "傷門", "天沖", "九天"})
    var = search_football_meanings("VAR")
    assert {item["key"] for item in var}.issuperset({"離九宮", "景門", "驚門", "辛"})
    injury = search_football_meanings("傷停")
    assert any("fitness_injury" in item["dimensions"] for item in injury)


def test_all_5184_core_combinations_are_composable():
    ontology = load_football_ontology()
    mappings = ontology["mappings"]
    combinations = product(
        (item["key"] for item in mappings["palaces"]),
        (item["key"] for item in mappings["doors"]),
        (item["key"] for item in mappings["stars"]),
        (item["key"] for item in mappings["deities"]),
    )
    count = 0
    for palace, door, star, deity in combinations:
        meaning = compose_football_meaning(
            palace=palace,
            door=door,
            stars=(star,),
            deity=deity,
        )
        assert len(meaning.symbols) == 4
        assert meaning.football_dimensions
        assert meaning.observable_signals
        assert meaning.counter_signals
        assert meaning.confidence == "應用假說／待賽前資料驗證"
        count += 1
    assert count == 5_184
    assert count == ontology["coverage_contract"]["core_combinations"]


def test_visible_heaven_and_earth_stem_extension_is_total():
    visible_stems = tuple("戊己庚辛壬癸丁丙乙")
    count = 0
    for heaven_stem, earth_stem in product(visible_stems, repeat=2):
        meaning = compose_football_meaning(
            palace=1,
            door="休門",
            stars=("天蓬",),
            deity="值符",
            heaven_stems=(heaven_stem,),
            earth_stem=earth_stem,
        )
        assert any(item.startswith("天地盤干：") for item in meaning.interactions)
        count += 1
    assert count == 81
    assert 5_184 * count == football_ontology_stats()["visible_stem_extended_combinations"]


def test_modifiers_add_hypotheses_without_outcome_claims():
    meaning = compose_football_meaning(
        palace=3,
        door="傷門",
        stars=("天沖",),
        deity="白虎",
        heaven_stems=("庚",),
        earth_stem="丙",
        seasonal_state="旺",
        states=("旬空", "驛馬"),
        patterns=("太白入熒", "星反吟"),
    )
    assert any("旬空" in item for item in meaning.symbols)
    assert any("驛馬" in item for item in meaning.symbols)
    assert any("反吟" in item for item in meaning.symbols)
    text = "".join(meaning.layer_readings)
    assert "必勝" not in text
    assert "固定比分" not in text
    assert "勝率" not in text


def test_unknown_symbol_is_rejected_instead_of_silently_guessed():
    with pytest.raises(ValueError, match="沒有 八門條目"):
        compose_football_meaning(
            palace=1,
            door="不存在門",
            stars=("天蓬",),
            deity="值符",
        )
