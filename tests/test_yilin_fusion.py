from jarvis.stark_vault import meihua_hexagram
from jarvis.yilin import (
    build_meihua_yilin_bridge,
    infer_image_atoms,
    search_yilin,
    yilin_catalog_stats,
    yilin_entries,
    yilin_entry,
    yilin_semantic_audit,
    yilin_semantic_profile,
)


def test_yilin_materializes_complete_64_by_64_matrix():
    rows = yilin_entries()
    stats = yilin_catalog_stats()

    assert len(rows) == 4096
    assert len({(row["from_number"], row["to_number"]) for row in rows}) == 4096
    assert {row["from_number"] for row in rows} == set(range(1, 65))
    assert {row["to_number"] for row in rows} == set(range(1, 65))
    for from_number in range(1, 65):
        targets = {row["to_number"] for row in rows if row["from_number"] == from_number}
        assert targets == set(range(1, 65))
    assert all(row["classical_text"] for row in rows)
    assert all(row["source_page_start"] for row in rows)
    assert all(row["verification_status"] == "WYG_DIGITAL_TRANSCRIPTION__PAIR_COMPLETE" for row in rows)

    assert stats["expected_pairs"] == 4096
    assert stats["materialized_pairs"] == 4096
    assert stats["coverage_ratio"] == 1.0
    assert stats["materialized_from_hexagrams"] == 64
    assert stats["catalog_status"] == "COMPLETE_4096_PAIR_COVERAGE__TEXTUAL_COLLATION_ONGOING"


def test_yilin_lookup_is_exact_across_first_middle_and_last_blocks():
    qian_kun = yilin_entry("乾", "坤")
    kun_qian = yilin_entry("坤", "乾")
    weiji_weiji = yilin_entry("未濟", "未濟")

    assert qian_kun is not None and qian_kun["id"] == "yilin.01.02"
    assert "病傷手足" in qian_kun["classical_text"]
    assert kun_qian is not None and kun_qian["id"] == "yilin.02.01"
    assert weiji_weiji is not None and weiji_weiji["id"] == "yilin.64.64"
    assert weiji_weiji["classical_text"]


def test_yilin_image_atoms_are_explicit_project_heuristics_with_evidence_and_counters():
    qian_qian = yilin_entry("乾", "乾")
    assert qian_qian is not None
    atoms = infer_image_atoms(qian_qian["classical_text"])
    ids = {row["id"] for row in atoms}

    # Do not hard-code a vague one-character keyword expectation. The ontology
    # deliberately favors more specific phrases to reduce false positives.
    assert "obstruction" in ids
    assert atoms
    assert all(row["authority"] == "PROJECT_HEURISTIC__NOT_CLASSICAL_COMMENTARY" for row in atoms)
    assert all(row["domain"] and row["specificity"] for row in atoms)
    assert all(row["observable_signals"] and row["counter_signals"] for row in atoms)

    profile = yilin_semantic_profile(qian_qian["classical_text"])
    assert profile["atom_count"] == len(atoms)
    assert profile["domains"]
    assert profile["observable_signals"]
    assert profile["counter_signals"]


def test_yilin_semantic_audit_is_transparent_and_non_predictive():
    audit = yilin_semantic_audit()
    assert audit["total_entries"] == 4096
    assert audit["ontology_atoms"] >= 30
    assert audit["entries_with_image_atoms"] > 0
    assert audit["entries_with_image_atoms"] + audit["entries_without_image_atoms"] == 4096
    assert 0.0 <= audit["match_ratio"] <= 1.0
    assert "not textual-critical or predictive accuracy" in audit["notice"]


def test_meihua_yilin_bridge_uses_only_original_to_changed_pair_and_has_no_pending_pair():
    qian = meihua_hexagram("乾", "乾")
    kun = meihua_hexagram("坤", "坤")

    forward = build_meihua_yilin_bridge(qian, kun)
    reverse = build_meihua_yilin_bridge(kun, qian)

    assert forward["lookup_key"] == "乾之坤"
    assert forward["status"] == "MATERIALIZED"
    assert forward["classical_entry"]["from_number"] == 1
    assert forward["classical_entry"]["to_number"] == 2
    assert forward["semantic_profile"]
    assert forward["provenance"]["page_start"]

    assert reverse["lookup_key"] == "坤之乾"
    assert reverse["status"] == "MATERIALIZED"
    assert reverse["classical_entry"]["from_number"] == 2
    assert reverse["classical_entry"]["to_number"] == 1


def test_yilin_lookup_normalizes_project_name_variants_by_number():
    # Runtime lookup must follow the project's Meihua canonical names even when
    # the source transcription uses a variant form such as 无/無, 恒/恆 or 兊/兌.
    hexagrams = [
        meihua_hexagram("乾", "震"),  # 無妄 / project canonical spelling
        meihua_hexagram("震", "巽"),  # 恆
        meihua_hexagram("兌", "兌"),  # 兌
    ]
    for row in hexagrams:
        assert yilin_entry("乾", row["name"]) is not None


def test_yilin_search_finds_transformations_classical_text_and_image_ontology():
    pair_results = search_yilin("坤之乾")
    text_results = search_yilin("病傷手足")
    image_results = search_yilin("出球受阻")

    assert any(row.get("lookup_key") == "坤之乾" for row in pair_results)
    assert any(row.get("family") == "transformation" for row in text_results)
    assert any(row.get("family") == "image_ontology" and row.get("id") == "obstruction" for row in image_results)
