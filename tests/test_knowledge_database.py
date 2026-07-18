from __future__ import annotations

from knowledge_loader import (
    build_jiaoshi_yilin_reference,
    knowledge_completeness,
    load_classics,
    load_conditional_trigram_meanings,
    load_hexagrams,
    load_hexagram_interpretations,
    load_jiaoshi_yilin,
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
        "yilin_main_hexagrams": 64,
        "yilin_entries": 4096,
        "interpretation_hexagrams": 64,
        "classical_meaning_fields": 384,
        "football_mapping_fields": 576,
        "conditional_trigram_meanings": 64,
        "conditional_trigram_rules": 48,
        "is_complete": True,
    }


def test_conditional_library_covers_all_trigrams_with_meanings_and_rules() -> None:
    payload = load_conditional_trigram_meanings()
    assert set(payload["trigrams"]) == {"乾", "兌", "離", "震", "巽", "坎", "艮", "坤"}
    assert sum(len(item["possible_meanings"]) for item in payload["trigrams"].values()) == 64
    assert sum(len(item["rules"]) for item in payload["trigrams"].values()) == 48
    assert all(len(item["possible_meanings"]) == 8 for item in payload["trigrams"].values())
    assert all(len(item["rules"]) == 6 for item in payload["trigrams"].values())


def test_gen_contains_the_requested_eight_meanings_and_six_conditions() -> None:
    gen = load_conditional_trigram_meanings()["trigrams"]["艮"]
    assert [item["name"] for item in gen["possible_meanings"]] == [
        "封鎖", "停滯", "守成", "防守穩定", "攻勢中斷", "控制節奏", "單點屏障", "被困住",
    ]
    conditions = [item["condition_text"] for item in gen["rules"]]
    assert "若艮方先前已取得優勢，而且變後仍旺或受生：優先解為守成。" in conditions
    assert "若高動能卦變艮，且生剋由有利轉不利：優先解為攻勢停止。" in conditions
    assert "若艮不變且受到生扶：優先解為穩定防守。" in conditions
    assert "若艮受克、空破：優先解為被困或防線失效。" in conditions
    assert "若整條卦線缺少破門通道：提高封鎖與低比分環境。" in conditions
    assert "若另一方具強烈震、巽、離、夬、噬嗑訊號：艮可能成為被突破的屏障。" in conditions


def test_all_64_hexagrams_have_complete_meaning_and_football_fields() -> None:
    payload = load_hexagram_interpretations()
    assert len(payload["hexagrams"]) == 64
    assert sum(len(x["classical_meaning"]) for x in payload["hexagrams"].values()) == 384
    assert sum(len(x["football_mapping"]) for x in payload["hexagrams"].values()) == 576
    assert all(
        all(str(value).strip() for value in section.values())
        for item in payload["hexagrams"].values()
        for section in (item["classical_meaning"], item["football_mapping"])
    )


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


def test_jiaoshi_yilin_covers_every_main_and_changed_hexagram() -> None:
    yilin = load_jiaoshi_yilin()
    expected_names = [
        item["short_name"]
        for item in sorted(load_hexagrams().values(), key=lambda item: int(item["sequence"]))
    ]

    assert yilin["entry_count"] == 4096
    assert yilin["hexagram_order"] == expected_names
    assert set(yilin["entries"]) == set(expected_names)
    assert all(set(entries) == set(expected_names) for entries in yilin["entries"].values())
    assert all(text.strip() for entries in yilin["entries"].values() for text in entries.values())
    assert all(
        any(mark in text for mark in "，。；！？：、") and text[-1] in "。！？"
        for entries in yilin["entries"].values()
        for text in entries.values()
    )
    assert yilin["punctuated_entry_count"] == 4096
    assert yilin["entries"]["乾"]["乾"] == (
        "道陟石阪，胡言連蹇。譯瘖且聾，莫使道通。請謁不行，求事無功。"
    )
    assert yilin["entries"]["乾"]["坤"] == "招殃來螫，害我邦國；病在手足，不得安息。"
    assert yilin["source"]["license"] == "CC-BY-SA-4.0"
    assert yilin["base_source"]["license"] == "CC0-1.0"
    assert yilin["source_label_corrections"] == [
        {
            "main_hexagram": "大過",
            "position": 45,
            "source_label": "卒",
            "normalized_label": "萃",
            "reason": "依該章固定 64 變次序校正來源索引標題；林辭原文未移位。",
        },
        {
            "main_hexagram": "益",
            "position": 43,
            "source_label": "夫",
            "normalized_label": "夬",
            "reason": "依該章固定 64 變次序校正來源索引標題；林辭原文未移位。",
        },
    ]
    assert len(yilin["source_completion_notes"]) == 3
    assert yilin["entries"]["井"]["巽"] == "春陽生草，夏長條枝。萬物蕃滋，充實益有。"


def test_jiaoshi_yilin_reference_has_text_structure_and_provenance() -> None:
    reference = build_jiaoshi_yilin_reference("乾為天", "坤為地")

    assert reference["entry_key"] == "乾之坤"
    assert reference["main_hexagram"]["sequence"] == 1
    assert reference["changed_hexagram"]["sequence"] == 2
    assert reference["text"] == "招殃來螫，害我邦國；病在手足，不得安息。"
    assert reference["text_style"] == "繁體中文標點版"
    assert reference["source"]["license"] == "CC-BY-SA-4.0"
    assert reference["source_completion_note"] is None
