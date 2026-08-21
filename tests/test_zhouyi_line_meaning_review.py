from jarvis.zhouyi_line_review import (
    build_zhouyi_line_meaning_review,
    zhouyi_line_meaning_review_audit,
)


def test_all_384_zhouyi_lines_have_structured_meaning_review():
    audit = zhouyi_line_meaning_review_audit()
    assert audit["total_reviews"] == 384
    assert audit["expected_reviews"] == 384
    assert audit["authority"] == "PROJECT_REVIEW__NOT_CLASSICAL_COMMENTARY"

    seen = set()
    for hexagram_number in range(1, 65):
        for line_number in range(1, 7):
            review = build_zhouyi_line_meaning_review(hexagram_number, line_number)
            key = (review["hexagram"]["number"], review["line"]["number"])
            assert key not in seen
            seen.add(key)
            assert review["line"]["classical_text"]
            assert review["text_conditions"]
            assert review["conditional_outcome_tendency"]["status"]
            assert review["football"]["source_basis"]
            assert review["football"]["abstract_meaning"]
            assert review["football"]["possible_scenario"]
            assert review["football"]["observable_signals"]
            assert review["football"]["counter_signals"]
            assert review["football"]["confidence_note"]

    assert len(seen) == 384


def test_line_review_never_claims_classical_football_formula_or_result_fields():
    review = build_zhouyi_line_meaning_review(1, 1)
    serialized = str(review).lower()
    assert review["authority"] == "PROJECT_REVIEW__NOT_CLASSICAL_COMMENTARY"
    assert "win_probability" not in serialized
    assert "fixed_score" not in serialized
    assert "predicted_score" not in serialized
    assert "final_result" not in serialized
    assert "不輸出勝率或固定比分" in review["football"]["boundary"]
