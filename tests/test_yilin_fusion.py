from jarvis.stark_vault import meihua_hexagram
from jarvis.yilin import (
    build_meihua_yilin_bridge,
    infer_image_atoms,
    search_yilin,
    yilin_catalog_stats,
    yilin_entries,
    yilin_entry,
)


def test_yilin_alpha_materializes_one_complete_from_hexagram_without_fake_completeness():
    rows = yilin_entries()
    stats = yilin_catalog_stats()

    assert len(rows) == 64
    assert len({(row["from_name"], row["to_name"]) for row in rows}) == 64
    assert {row["from_name"] for row in rows} == {"乾"}
    assert {row["to_number"] for row in rows} == set(range(1, 65))
    assert len({row["to_name"] for row in rows}) == 64
    assert all(row["classical_text"] for row in rows)
    assert all(row["variant_status"] == "PENDING_CROSSCHECK" for row in rows)

    assert stats["expected_pairs"] == 4096
    assert stats["materialized_pairs"] == 64
    assert stats["coverage_ratio"] == 64 / 4096
    assert stats["catalog_status"] == "PARTIAL_BUILD__DO_NOT_CLAIM_4096_COMPLETE"


def test_yilin_lookup_is_exact_and_never_invents_missing_classical_text():
    qian_kun = yilin_entry("乾", "坤")
    assert qian_kun is not None
    assert qian_kun["id"] == "yilin.01.02"
    assert "病傷手足" in qian_kun["classical_text"]

    assert yilin_entry("坤", "乾") is None


def test_yilin_image_atoms_are_explicit_project_heuristics_with_evidence_and_counters():
    qian_qian = yilin_entry("乾", "乾")
    assert qian_qian is not None
    atoms = infer_image_atoms(qian_qian["classical_text"])
    ids = {row["id"] for row in atoms}

    assert "path_movement" in ids
    assert "obstruction" in ids
    assert all(row["authority"] == "PROJECT_HEURISTIC__NOT_CLASSICAL_COMMENTARY" for row in atoms)
    assert all(row["observable_signals"] and row["counter_signals"] for row in atoms)


def test_meihua_yilin_bridge_uses_only_original_to_changed_pair():
    qian = meihua_hexagram("乾", "乾")
    kun = meihua_hexagram("坤", "坤")

    materialized = build_meihua_yilin_bridge(qian, kun)
    assert materialized["lookup_key"] == "乾之坤"
    assert materialized["status"] == "MATERIALIZED"
    assert materialized["classical_entry"]["from_name"] == "乾"
    assert materialized["classical_entry"]["to_name"] == "坤"
    assert materialized["image_atoms"]

    pending = build_meihua_yilin_bridge(kun, qian)
    assert pending["lookup_key"] == "坤之乾"
    assert pending["status"] == "SOURCE_PENDING"
    assert pending["classical_entry"] is None
    assert pending["image_atoms"] == []
    assert "禁止生成或猜測林辭" in pending["missing_reason"]


def test_yilin_search_finds_transformations_and_image_ontology():
    pair_results = search_yilin("乾之坤")
    image_results = search_yilin("出球受阻")

    assert any(row.get("lookup_key") == "乾之坤" for row in pair_results)
    assert any(row.get("family") == "image_ontology" and row.get("id") == "obstruction" for row in image_results)
