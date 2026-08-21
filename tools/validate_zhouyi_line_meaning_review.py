from __future__ import annotations

from jarvis.zhouyi_line_review import (
    build_zhouyi_line_meaning_review,
    zhouyi_line_meaning_review_audit,
)


FORBIDDEN_KEYS = {
    "win_probability",
    "home_win_probability",
    "away_win_probability",
    "fixed_score",
    "predicted_score",
    "final_result",
}


def _all_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _all_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _all_keys(child)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"zhouyi line meaning review validation failed: {message}")


def main() -> None:
    audit = zhouyi_line_meaning_review_audit()
    require(audit["total_reviews"] == 384, "must build exactly 384 reviews")
    require(audit["expected_reviews"] == 384, "expected count must remain 384")
    require(audit["authority"] == "PROJECT_REVIEW__NOT_CLASSICAL_COMMENTARY", "authority boundary drift")

    seen: set[tuple[int, int]] = set()
    for hexagram_number in range(1, 65):
        for line_number in range(1, 7):
            review = build_zhouyi_line_meaning_review(hexagram_number, line_number)
            key = (review["hexagram"]["number"], review["line"]["number"])
            require(key not in seen, f"duplicate review {key}")
            seen.add(key)
            require(review["line"]["classical_text"], f"missing classical text {key}")
            require(review["line"]["source_file"], f"missing source file {key}")
            require(review["line"]["source_commit"], f"missing source commit {key}")
            require(review["text_conditions"], f"missing text conditions {key}")
            require(review["action_boundary"]["phase"], f"missing phase {key}")
            require(review["conditional_outcome_tendency"]["status"], f"missing tendency {key}")
            football = review["football"]
            for field in (
                "source_basis",
                "abstract_meaning",
                "possible_scenario",
                "observable_signals",
                "counter_signals",
                "confidence_note",
            ):
                require(football.get(field), f"missing football.{field} {key}")
            require(not (set(_all_keys(review)) & FORBIDDEN_KEYS), f"forbidden result field in {key}")

    require(len(seen) == 384, "review key coverage must be 384/384")
    print(
        "zhouyi line meaning review validation: PASS | "
        f"384/384 | raw_text_only={audit['raw_text_only_reviews']} | mixed={audit['mixed_conditional_reviews']}"
    )


if __name__ == "__main__":
    main()
