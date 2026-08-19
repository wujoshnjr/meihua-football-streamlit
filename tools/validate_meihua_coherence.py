from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jarvis.divination_packet import build_meihua_packet  # noqa: E402


FORBIDDEN_RESULT_KEYS = {
    "win_probability",
    "home_win_probability",
    "draw_probability",
    "away_win_probability",
    "predicted_score",
    "fixed_score",
    "final_result",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"Meihua coherence validation failed: {message}")


def _keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _keys(child)


def main() -> None:
    packet = build_meihua_packet(
        question="JARVIS 10.2 coherence validator",
        event_at=datetime(2026, 6, 15, 12, 0, tzinfo=ZoneInfo("America/New_York")),
        timezone_name="America/New_York",
        category="general",
    )
    review = packet["review_summary"]
    coherence = review.get("cross_system_coherence") or {}

    require(
        coherence.get("schema_version") == "stark-meihua-cross-system-coherence-v1.0.0",
        "unexpected cross-system coherence schema",
    )
    alignment = coherence.get("source_pair_alignment") or {}
    require(alignment.get("all_match") is True, "Yilin from/to must match Zhouyi original/changed")
    require(all(alignment.get(key) is True for key in (
        "from_number_matches_original",
        "from_name_matches_original",
        "to_number_matches_changed",
        "to_name_matches_changed",
    )), "source pair alignment details incomplete")

    zhouyi = coherence.get("zhouyi") or {}
    yilin = coherence.get("yilin") or {}
    require(zhouyi.get("role") == "SUPPORTING_FOR_CURRENT_XIANTIAN_NUMBER_METHOD", "Zhouyi role must remain method-aware supporting")
    require(yilin.get("role") == "TRANSFORMATION_CONTEXT__DOES_NOT_RECAST", "Yilin must remain transformation context only")
    require(isinstance(coherence.get("shared_domains"), list), "shared domains must be explicit")
    require(isinstance(coherence.get("reinforcement"), list), "reinforcement register missing")
    require(isinstance(coherence.get("tension"), list), "tension register missing")
    require(isinstance(coherence.get("independent_signal"), list), "independent-signal register missing")
    require(bool(coherence.get("interpretation_rule")), "coherence interpretation boundary missing")

    coverage = review.get("source_coverage_audit") or {}
    require(coverage.get("yilin_pair_matches_zhouyi_original_changed") is True, "coverage audit must expose pair alignment")

    present_keys = set(_keys(coherence))
    require(
        not (present_keys & FORBIDDEN_RESULT_KEYS),
        f"coherence contains forbidden automatic result keys: {sorted(present_keys & FORBIDDEN_RESULT_KEYS)}",
    )
    require("投票" in coherence["interpretation_rule"] and "統計權重" in coherence["interpretation_rule"], "anti-overreach boundary is incomplete")

    print(
        "Meihua coherence validation passed: Zhouyi moving-line source + Yilin original→changed pair aligned / "
        "semantic domains compared as project heuristics / independent signals preserved / no automatic result fields"
    )


if __name__ == "__main__":
    main()
