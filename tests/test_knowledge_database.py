from __future__ import annotations

from knowledge_loader import (
    knowledge_completeness,
    load_classics,
    load_hexagrams,
    load_meihua_principles,
    load_trigrams,
)


def test_database_covers_all_trigrams_hexagrams_and_lines() -> None:
    trigrams = load_trigrams()
    hexagrams = load_hexagrams()
    status = knowledge_completeness()

    assert set(trigrams) == {"乾", "兌", "離", "震", "巽", "坎", "艮", "坤"}
    assert len(hexagrams) == 64
    assert {item["sequence"] for item in hexagrams.values()} == set(range(1, 65))
    assert len({item["binary_bottom_up"] for item in hexagrams.values()}) == 64
    assert sum(len(item["lines"]) for item in hexagrams.values()) == 384
    assert status == {
        "trigrams": 8,
        "hexagrams": 64,
        "line_records": 384,
        "complete_hexagrams": 64,
        "classic_appendices": 5,
        "is_complete": True,
    }


def test_every_hexagram_has_classical_and_structural_fields() -> None:
    hexagrams = load_hexagrams()
    for name, item in hexagrams.items():
        assert item["name"] == name
        assert item["unicode"]
        assert item["upper"] in load_trigrams()
        assert item["lower"] in load_trigrams()
        assert item["judgment_text"]
        assert item["tuan_text"]
        assert item["great_image_text"]
        assert item["meaning_overview"]
        assert len(item["lines"]) == 6
        for position, line in enumerate(item["lines"], 1):
            assert line["position"] == position
            assert line["label"]
            assert line["classic_text"]
            assert line["small_image_text"]
        assert set(item["related_hexagrams"]) == {"nuclear", "opposite", "reversed"}
        assert set(item["related_hexagrams"].values()).issubset(hexagrams)
        forbidden_prediction_fields = {
            "football", "score_patterns", "goal_bias", "pace", "attack_rating", "defense_rating"
        }
        assert forbidden_prediction_fields.isdisjoint(item)


def test_qian_kun_special_lines_and_wenyan_are_present() -> None:
    hexagrams = load_hexagrams()
    qian = hexagrams["乾為天"]
    kun = hexagrams["坤為地"]

    assert qian["judgment_text"] == "乾：元亨，利貞。"
    assert qian["lines"][0]["classic_text"] == "初九：潛龍，勿用。"
    assert qian["special_line"]["label"] == "用九"
    assert kun["special_line"]["label"] == "用六"
    assert qian["wenyan_text"]
    assert kun["wenyan_text"]


def test_meihua_principles_and_five_classic_appendices_load() -> None:
    principles = load_meihua_principles()
    classics = load_classics()

    assert principles["scope"].startswith("本資料只定義起卦")
    assert principles["number_system"]["mapping"]["8"] == "坤"
    assert set(classics) == {"文言", "說卦", "繫辭", "序卦", "雜卦"}
    assert all(payload.get("content") for payload in classics.values())
