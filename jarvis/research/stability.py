from __future__ import annotations

from collections import defaultdict
from math import ceil, floor, isfinite
import random
from typing import Any, Iterable

from .experiment import ForecastEvaluation, PrematchExperimentRecord, paired_model_comparison


STABILITY_SCHEMA_VERSION = "jarvis-experiment-stability-v0.1.0"
_DELTA_FIELDS = (
    "result_log_loss_delta",
    "brier_score_delta",
    "ranked_probability_score_delta",
    "exact_score_nll_delta",
)


def _percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = floor(position)
    upper = ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _prepare(
    records: Iterable[PrematchExperimentRecord],
    baseline: Iterable[ForecastEvaluation],
    challenger: Iterable[ForecastEvaluation],
) -> tuple[
    tuple[PrematchExperimentRecord, ...],
    dict[str, ForecastEvaluation],
    dict[str, ForecastEvaluation],
    tuple[str, ...],
    dict[str, tuple[str, ...]],
]:
    rows = tuple(sorted(records, key=lambda row: (row.event_at, row.match_id)))
    if not rows:
        raise ValueError("stability analysis 至少需要一場 TEST_UNTOUCHED 比賽")

    errors = [error for row in rows for error in row.validate()]
    if any(row.dataset_role != "TEST_UNTOUCHED" for row in rows):
        errors.append("stability analysis 只允許 TEST_UNTOUCHED，避免用穩定性結果反向選模")
    match_ids = [row.match_id for row in rows]
    if len(set(match_ids)) != len(match_ids):
        errors.append("stability analysis records 含重複 match_id")
    if len({row.experiment_id for row in rows}) != 1:
        errors.append("stability analysis 必須來自單一 experiment_id")

    baseline_by_id = {row.match_id: row for row in baseline}
    challenger_by_id = {row.match_id: row for row in challenger}
    record_ids = set(match_ids)
    if set(baseline_by_id) != record_ids or set(challenger_by_id) != record_ids:
        errors.append("stability analysis 的 records/baseline/challenger 必須使用完全相同 match_id")

    if errors:
        raise ValueError("；".join(errors))

    # evaluation_block is the resampling unit. Reappearing non-contiguous blocks
    # would silently combine separated time periods and invalidate the time blocks.
    block_order: list[str] = []
    seen_blocks: set[str] = set()
    last_block: str | None = None
    block_matches: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        block = row.evaluation_block
        if block != last_block:
            if block in seen_blocks:
                raise ValueError("evaluation_block 必須在時間序列中連續，不可離開後再次出現")
            seen_blocks.add(block)
            block_order.append(block)
            last_block = block
        block_matches[block].append(row.match_id)

    return (
        rows,
        baseline_by_id,
        challenger_by_id,
        tuple(block_order),
        {block: tuple(ids) for block, ids in block_matches.items()},
    )


def _metric_deltas(
    match_ids: Iterable[str],
    baseline_by_id: dict[str, ForecastEvaluation],
    challenger_by_id: dict[str, ForecastEvaluation],
) -> dict[str, list[float]]:
    deltas = {field: [] for field in _DELTA_FIELDS}
    for match_id in match_ids:
        base = baseline_by_id[match_id]
        challenge = challenger_by_id[match_id]
        deltas["result_log_loss_delta"].append(challenge.result_log_loss - base.result_log_loss)
        deltas["brier_score_delta"].append(challenge.brier_score - base.brier_score)
        deltas["ranked_probability_score_delta"].append(
            challenge.ranked_probability_score - base.ranked_probability_score
        )
        deltas["exact_score_nll_delta"].append(challenge.exact_score_nll - base.exact_score_nll)
    return deltas


def rolling_block_stability(
    records: Iterable[PrematchExperimentRecord],
    baseline: Iterable[ForecastEvaluation],
    challenger: Iterable[ForecastEvaluation],
    *,
    window_blocks: int = 3,
) -> dict[str, Any]:
    """Measure paired challenger deltas through consecutive untouched time blocks.

    ``evaluation_block`` is the atomic time unit, so matches from the same
    registered block are never split across windows. Negative loss deltas mean the
    challenger is better than the baseline.
    """

    _, baseline_by_id, challenger_by_id, block_order, block_matches = _prepare(
        records, baseline, challenger
    )
    if isinstance(window_blocks, bool) or not isinstance(window_blocks, int) or window_blocks < 1:
        raise ValueError("window_blocks 必須為正整數")
    if window_blocks > len(block_order):
        raise ValueError("window_blocks 不可大於可用 evaluation_block 數")

    windows: list[dict[str, Any]] = []
    for start in range(len(block_order) - window_blocks + 1):
        selected_blocks = block_order[start : start + window_blocks]
        ids = tuple(match_id for block in selected_blocks for match_id in block_matches[block])
        comparison = paired_model_comparison(
            (baseline_by_id[match_id] for match_id in ids),
            (challenger_by_id[match_id] for match_id in ids),
        )
        windows.append(
            {
                "start_block": selected_blocks[0],
                "end_block": selected_blocks[-1],
                "blocks": selected_blocks,
                "matches": len(ids),
                **{field: comparison[field] for field in _DELTA_FIELDS},
            }
        )

    metric_stability: dict[str, dict[str, float | bool]] = {}
    for field in _DELTA_FIELDS:
        values = [float(window[field]) for window in windows]
        metric_stability[field] = {
            "better_window_fraction": sum(value < 0 for value in values) / len(values),
            "mean_window_delta": sum(values) / len(values),
            "best_window_delta": min(values),
            "worst_window_delta": max(values),
            "better_in_every_window": all(value < 0 for value in values),
        }

    return {
        "schema_version": STABILITY_SCHEMA_VERSION,
        "blocks": len(block_order),
        "window_blocks": window_blocks,
        "windows": tuple(windows),
        "metric_stability": metric_stability,
        "note": "delta < 0 代表 challenger 較佳；rolling windows 僅使用 TEST_UNTOUCHED。",
    }


def paired_block_bootstrap(
    records: Iterable[PrematchExperimentRecord],
    baseline: Iterable[ForecastEvaluation],
    challenger: Iterable[ForecastEvaluation],
    *,
    samples: int = 2000,
    confidence: float = 0.95,
    seed: int = 20260818,
) -> dict[str, Any]:
    """Paired cluster bootstrap over registered untouched evaluation blocks.

    Resampling whole ``evaluation_block`` clusters preserves within-block pairing
    and short-range dependence better than independently resampling matches. The
    result is descriptive uncertainty for the already-untouched test, never a
    hyperparameter-selection signal.
    """

    _, baseline_by_id, challenger_by_id, block_order, block_matches = _prepare(
        records, baseline, challenger
    )
    if len(block_order) < 2:
        raise ValueError("paired block bootstrap 至少需要 2 個 evaluation_block")
    if isinstance(samples, bool) or not isinstance(samples, int) or samples < 200:
        raise ValueError("samples 至少需要 200")
    if not isfinite(confidence) or not 0.5 < confidence < 1.0:
        raise ValueError("confidence 必須介於 0.5 與 1.0")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed 必須為整數")

    all_ids = tuple(match_id for block in block_order for match_id in block_matches[block])
    observed = paired_model_comparison(
        (baseline_by_id[match_id] for match_id in all_ids),
        (challenger_by_id[match_id] for match_id in all_ids),
    )
    per_block_deltas = {
        block: _metric_deltas(block_matches[block], baseline_by_id, challenger_by_id)
        for block in block_order
    }

    rng = random.Random(seed)
    distributions = {field: [] for field in _DELTA_FIELDS}
    for _ in range(samples):
        selected = [rng.choice(block_order) for _ in block_order]
        for field in _DELTA_FIELDS:
            values = [
                value
                for block in selected
                for value in per_block_deltas[block][field]
            ]
            distributions[field].append(sum(values) / len(values))

    tail = (1.0 - confidence) / 2.0
    intervals: dict[str, dict[str, float | bool]] = {}
    for field in _DELTA_FIELDS:
        distribution = distributions[field]
        lower = _percentile(distribution, tail)
        upper = _percentile(distribution, 1.0 - tail)
        intervals[field] = {
            "observed_delta": float(observed[field]),
            "lower": lower,
            "upper": upper,
            "challenger_better_probability": sum(value < 0 for value in distribution) / samples,
            "interval_excludes_zero_in_favor_of_challenger": upper < 0,
        }

    return {
        "schema_version": STABILITY_SCHEMA_VERSION,
        "bootstrap_unit": "evaluation_block",
        "blocks": len(block_order),
        "matches": len(all_ids),
        "samples": samples,
        "confidence": confidence,
        "seed": seed,
        "baseline_family": observed["baseline_family"],
        "challenger_family": observed["challenger_family"],
        "intervals": intervals,
        "note": "confidence interval 僅描述 TEST_UNTOUCHED paired delta；不可回頭用來選 feature/L2/alpha/model。",
    }
