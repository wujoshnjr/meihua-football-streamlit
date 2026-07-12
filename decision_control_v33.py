"""Backward-compatible imports for the former v3.3 decision module.

The canonical implementation lives in :mod:`evaluation` as of v4. Existing
imports remain valid without maintaining a second, divergent control path.
"""

from evaluation import (
    calibration_summary_from_row,
    candidate_scores,
    controlled_final_scores,
    evaluate_predictions,
    final_scores,
    local_calibration_summary,
    normalize_score,
    outcome,
    score_tuple,
)

__all__ = [
    "normalize_score",
    "score_tuple",
    "outcome",
    "evaluate_predictions",
    "candidate_scores",
    "controlled_final_scores",
    "final_scores",
    "local_calibration_summary",
    "calibration_summary_from_row",
]
