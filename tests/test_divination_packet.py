from datetime import datetime
from zoneinfo import ZoneInfo

from jarvis.divination_packet import (
    DIVINATION_PACKET_VERSION,
    build_meihua_packet,
    build_qimen_packet,
)


def event_at() -> datetime:
    return datetime(2026, 6, 15, 12, 0, tzinfo=ZoneInfo("America/New_York"))


def test_qimen_packet_is_deterministic_and_ai_handoff_only():
    kwargs = dict(
        question="西班牙對維德角，這場比賽整體走勢如何？",
        event_at=event_at(),
        timezone_name="America/New_York",
        category="football_match",
        home_team="西班牙",
        away_team="維德角",
    )
    first = build_qimen_packet(**kwargs)
    second = build_qimen_packet(**kwargs)

    assert first["schema_version"] == DIVINATION_PACKET_VERSION
    assert first["system"] == "QIMEN_DUNJIA"
    assert first["packet_sha256"] == second["packet_sha256"]
    assert first["chart"] == second["chart"]
    assert "generated_at" not in first["chart"]
    assert first["host_guest"]["home_team"] == "西班牙"
    assert first["event"]["normalization"] == "ACTUAL_CAST_EVENT_LOCAL_TIME"
    assert first["knowledge_context"]
    kinds = [row["kind"] for row in first["knowledge_context"]]
    assert "qimen_deep_reading_policy" in kinds
    assert kinds.count("qimen_palace_deep_profile") == 9
    deep_palaces = [row for row in first["knowledge_context"] if row["kind"] == "qimen_palace_deep_profile"]
    assert all(row["football_questions"] for row in deep_palaces)
    assert any(row["deity_detail"] for row in deep_palaces)
    serialized = str(first).lower()
    assert "home_win_probability" not in serialized
    assert "fixed_score" not in serialized


def test_meihua_packet_is_deterministic_and_contains_method_aware_deep_layers():
    kwargs = dict(
        question="西班牙對維德角，這場比賽整體走勢如何？",
        event_at=event_at(),
        timezone_name="America/New_York",
        category="football_match",
        home_team="西班牙",
        away_team="維德角",
    )
    first = build_meihua_packet(**kwargs)
    second = build_meihua_packet(**kwargs)

    assert first["schema_version"] == DIVINATION_PACKET_VERSION
    assert first["system"] == "MEIHUA_YISHU"
    assert first["packet_sha256"] == second["packet_sha256"]
    assert first["hexagram"] == second["hexagram"]
    assert first["meihua_method_audit"] == second["meihua_method_audit"]
    assert first["zhouyi_review"] == second["zhouyi_review"]
    assert first["yilin_bridge"] == second["yilin_bridge"]
    assert first["review_summary"] == second["review_summary"]

    method = first["meihua_method_audit"]
    assert first["method"]["class"] == "XIANTIAN_NUMBER_METHOD"
    assert method["kind"] == "meihua_classical_method_audit"
    assert method["status"] == "METHOD_AWARE_REVIEW_READY"
    assert method["method"]["class"] == "XIANTIAN_NUMBER_METHOD"
    assert method["weighting_decision"]["zhouyi_role"] == "SUPPORTING"
    assert method["external_response_audit"]["three_essentials"] == "NOT_RECORDED"
    assert method["external_response_audit"]["ten_responses"] == "NOT_RECORDED"
    assert method["external_response_audit"]["external_omens"] == "NOT_RECORDED"
    assert [row["layer"] for row in method["body_use_network"]["layers"]] == [
        "original_use",
        "mutual_upper",
        "mutual_lower",
        "changed_use",
    ]
    assert [row["relative_stage"] for row in method["body_use_network"]["layers"]] == [
        "immediate",
        "middle",
        "middle",
        "late",
    ]
    assert len(method["classical_principles"]) >= 8

    review = first["review_summary"]
    assert review["kind"] == "meihua_deep_review_summary"
    assert review["status"] == "READY_WITH_DECLARED_GAPS"
    assert review["method_weighting"]["method_class"] == "XIANTIAN_NUMBER_METHOD"
    assert review["method_weighting"]["zhouyi_role"] == "SUPPORTING"
    assert len(review["relation_signals"]) == 4
    assert {row["relative_stage"] for row in review["relation_signals"]} == {"immediate", "middle", "late"}

    coherence = review["cross_system_coherence"]
    assert coherence["schema_version"] == "stark-meihua-cross-system-coherence-v1.0.0"
    assert coherence["source_pair_alignment"]["all_match"] is True
    assert coherence["zhouyi"]["role"] == "SUPPORTING_FOR_CURRENT_XIANTIAN_NUMBER_METHOD"
    assert coherence["yilin"]["role"] == "TRANSFORMATION_CONTEXT__DOES_NOT_RECAST"
    assert isinstance(coherence["shared_domains"], list)
    assert isinstance(coherence["reinforcement"], list)
    assert isinstance(coherence["tension"], list)
    assert isinstance(coherence["independent_signal"], list)
    assert "勝率" not in coherence["interpretation_rule"]

    assert review["uncertainty_register"]
    assert {row["id"] for row in review["uncertainty_register"]} >= {
        "EXTERNAL_RESPONSES_NOT_RECORDED",
        "MULTI_EDITION_COLLATION_INCOMPLETE",
        "MODERN_FOOTBALL_MAPPING_IS_HEURISTIC",
    }
    assert review["source_coverage_audit"]["method_audit_ready"] is True
    assert review["source_coverage_audit"]["zhouyi_core_alignments_match"] is True
    assert review["source_coverage_audit"]["yilin_pair_materialized"] is True
    assert review["source_coverage_audit"]["yilin_pair_matches_zhouyi_original_changed"] is True

    assert first["yilin_bridge"]["mode"] == "MEIHUA_YILIN_BRIDGE"
    assert first["yilin_bridge"]["status"] == "MATERIALIZED"
    assert first["yilin_bridge"]["catalog_stats"]["materialized_pairs"] == 4096
    assert first["yilin_bridge"]["catalog_stats"]["expected_pairs"] == 4096
    assert first["yilin_bridge"]["catalog_stats"]["coverage_ratio"] == 1.0
    assert first["yilin_bridge"]["provenance"]["source_id"] == "yilin-kanripo-wyg-transcription"

    zhouyi = first["zhouyi_review"]
    assert zhouyi["catalog_stats"]["materialized_hexagrams"] == 64
    assert zhouyi["catalog_stats"]["materialized_standard_lines"] == 384
    assert zhouyi["source_audit"]["all_core_alignments_match"] is True
    assert zhouyi["moving_line"]["classical_text"]
    assert "method_fidelity" in {row["id"] for row in zhouyi["review_dimensions"]}
    assert zhouyi["authority_order"][1].startswith("MEIHUA_CLASSICAL_METHOD_AUDIT")

    kinds = {row["kind"] for row in first["knowledge_context"]}
    assert "meihua_original_hexagram" in kinds
    assert "meihua_mutual_hexagram" in kinds
    assert "meihua_changed_hexagram" in kinds
    assert "meihua_body_use" in kinds
    assert "meihua_moving_line_role" in kinds
    assert "meihua_deep_reading_policy" in kinds
    assert "meihua_deep_profile" in kinds
    assert "meihua_yilin_bridge" not in kinds

    deep = next(row for row in first["knowledge_context"] if row["kind"] == "meihua_deep_profile")
    assert deep["original"]["hexagram"]["name"]
    assert deep["mutual"]["hexagram"]["name"]
    assert deep["changed"]["hexagram"]["name"]
    assert deep["body_use"]["relation_detail"]["general"]
    assert deep["moving_line"]["football"]
    assert len(deep["football_dimensions"]) == 8

    serialized = str(first).lower()
    assert "home_win_probability" not in serialized
    assert "fixed_score" not in serialized


def test_football_packets_require_both_teams():
    try:
        build_meihua_packet(
            question="測試",
            event_at=event_at(),
            timezone_name="America/New_York",
            category="football_match",
            home_team="西班牙",
            away_team="",
        )
    except ValueError as exc:
        assert "主隊與客隊" in str(exc)
    else:
        raise AssertionError("football packet must reject missing teams")
