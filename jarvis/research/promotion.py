from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from math import isfinite
from typing import Any, Iterable

from jarvis.provenance import sha256_payload

from .experiment import (
    VALID_MODEL_FAMILIES,
    ForecastEvaluation,
    ModelFamily,
    PrematchExperimentRecord,
    aggregate_evaluations,
)
from .stability import paired_block_bootstrap, rolling_block_stability


PROMOTION_REVIEW_VERSION = "jarvis-generic-promotion-review-v0.1.0"


@dataclass(frozen=True)
class PromotionPolicy:
    """Pre-registered thresholds for reviewing one frozen model challenger.

    ``registered_at`` must be no later than the first TEST_UNTOUCHED cutoff. This
    prevents looking at untouched outcomes and then relaxing promotion thresholds.
    The policy only controls eligibility for human review; it never activates a
    model automatically.
    """

    policy_id: str
    registered_at: datetime
    baseline_family: ModelFamily
    challenger_family: ModelFamily
    min_matches: int = 5000
    min_blocks: int = 5
    min_competitions: int = 2
    min_log_loss_relative_improvement: float = 0.005
    max_classwise_ece_degradation: float = 0.005
    min_log_loss_better_window_fraction: float = 0.80
    window_blocks: int = 3
    bootstrap_samples: int = 2000
    confidence: float = 0.95
    seed: int = 20260818

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.policy_id.strip():
            errors.append("promotion policy_id 不可空白")
        if self.registered_at.tzinfo is None:
            errors.append("promotion registered_at 必須含時區")
        if self.baseline_family not in VALID_MODEL_FAMILIES:
            errors.append("promotion baseline_family 無效")
        if self.challenger_family not in VALID_MODEL_FAMILIES:
            errors.append("promotion challenger_family 無效")
        if self.baseline_family == self.challenger_family:
            errors.append("promotion baseline/challenger family 不可相同")
        for label, value, minimum in (
            ("min_matches", self.min_matches, 1),
            ("min_blocks", self.min_blocks, 2),
            ("min_competitions", self.min_competitions, 1),
            ("window_blocks", self.window_blocks, 1),
            ("bootstrap_samples", self.bootstrap_samples, 200),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
                errors.append(f"promotion {label} 必須為 >= {minimum} 的整數")
        if isinstance(self.min_blocks, int) and isinstance(self.window_blocks, int):
            if self.window_blocks > self.min_blocks:
                errors.append("promotion window_blocks 不可大於 min_blocks")
        if (
            not isfinite(self.min_log_loss_relative_improvement)
            or self.min_log_loss_relative_improvement < 0
        ):
            errors.append("promotion min_log_loss_relative_improvement 必須為非負有限數")
        if (
            not isfinite(self.max_classwise_ece_degradation)
            or self.max_classwise_ece_degradation < 0
        ):
            errors.append("promotion max_classwise_ece_degradation 必須為非負有限數")
        if (
            not isfinite(self.min_log_loss_better_window_fraction)
            or not 0 <= self.min_log_loss_better_window_fraction <= 1
        ):
            errors.append("promotion min_log_loss_better_window_fraction 必須介於 0 與 1")
        if not isfinite(self.confidence) or not 0.5 < self.confidence < 1.0:
            errors.append("promotion confidence 必須介於 0.5 與 1")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            errors.append("promotion seed 必須為整數")
        return errors

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["registered_at"] = self.registered_at.isoformat()
        return payload

    @property
    def fingerprint_sha256(self) -> str:
        return sha256_payload({"version": PROMOTION_REVIEW_VERSION, **self.to_dict()})

    @property
    def artifact_source(self) -> str:
        return f"promotion-policy:{self.fingerprint_sha256}"


def review_model_promotion(
    records: Iterable[PrematchExperimentRecord],
    baseline: Iterable[ForecastEvaluation],
    challenger: Iterable[ForecastEvaluation],
    policy: PromotionPolicy,
) -> dict[str, Any]:
    """Review one frozen M0–M3 challenger without ever activating it.

    The function only accepts TEST_UNTOUCHED records through the stability layer.
    A policy registered after the untouched period starts is rejected rather than
    silently evaluated, because changing thresholds after seeing test outcomes is
    itself a form of leakage.
    """

    policy_errors = policy.validate()
    if policy_errors:
        raise ValueError("；".join(policy_errors))

    rows = tuple(sorted(records, key=lambda row: (row.event_at, row.match_id)))
    baseline_rows = tuple(baseline)
    challenger_rows = tuple(challenger)
    if not rows:
        raise ValueError("promotion review 至少需要一場 TEST_UNTOUCHED 比賽")

    earliest_cutoff = min(row.cutoff for row in rows)
    if policy.registered_at > earliest_cutoff:
        raise ValueError("promotion policy 必須在第一個 TEST_UNTOUCHED cutoff 前預先登記")

    bootstrap = paired_block_bootstrap(
        rows,
        baseline_rows,
        challenger_rows,
        samples=policy.bootstrap_samples,
        confidence=policy.confidence,
        seed=policy.seed,
    )
    if bootstrap["baseline_family"] != policy.baseline_family:
        raise ValueError("promotion baseline family 與預先登記 policy 不一致")
    if bootstrap["challenger_family"] != policy.challenger_family:
        raise ValueError("promotion challenger family 與預先登記 policy 不一致")

    rolling: dict[str, Any] | None = None
    if int(bootstrap["blocks"]) >= policy.window_blocks:
        rolling = rolling_block_stability(
            rows,
            baseline_rows,
            challenger_rows,
            window_blocks=policy.window_blocks,
        )

    baseline_aggregate = aggregate_evaluations(baseline_rows)
    challenger_aggregate = aggregate_evaluations(challenger_rows)
    baseline_log_loss = float(baseline_aggregate["mean_result_log_loss"])
    challenger_log_loss = float(challenger_aggregate["mean_result_log_loss"])
    relative_improvement = (
        (baseline_log_loss - challenger_log_loss) / baseline_log_loss
        if baseline_log_loss > 0
        else 0.0
    )
    ece_degradation = (
        float(challenger_aggregate["max_classwise_ece"])
        - float(baseline_aggregate["max_classwise_ece"])
    )
    log_loss_interval = bootstrap["intervals"]["result_log_loss_delta"]
    brier_interval = bootstrap["intervals"]["brier_score_delta"]
    rps_interval = bootstrap["intervals"]["ranked_probability_score_delta"]
    exact_score_interval = bootstrap["intervals"]["exact_score_nll_delta"]
    better_window_fraction = (
        float(
            rolling["metric_stability"]["result_log_loss_delta"]["better_window_fraction"]
        )
        if rolling is not None
        else 0.0
    )
    competitions = {row.competition for row in rows}

    checks = {
        "policy_registered_before_untouched": True,
        "minimum_matches": int(bootstrap["matches"]) >= policy.min_matches,
        "minimum_blocks": int(bootstrap["blocks"]) >= policy.min_blocks,
        "minimum_competitions": len(competitions) >= policy.min_competitions,
        "log_loss_relative_improvement": (
            relative_improvement >= policy.min_log_loss_relative_improvement
        ),
        "log_loss_ci_excludes_zero": float(log_loss_interval["upper"]) < 0,
        "brier_same_direction": float(brier_interval["observed_delta"]) < 0,
        "rps_same_direction": float(rps_interval["observed_delta"]) < 0,
        "exact_score_nll_same_direction": float(exact_score_interval["observed_delta"]) < 0,
        "classwise_ece_degradation_within_limit": (
            ece_degradation <= policy.max_classwise_ece_degradation
        ),
        "rolling_log_loss_stability": (
            rolling is not None
            and better_window_fraction >= policy.min_log_loss_better_window_fraction
        ),
    }
    eligible = all(checks.values())
    failed_checks = tuple(name for name, passed in checks.items() if not passed)

    core = {
        "version": PROMOTION_REVIEW_VERSION,
        "policy_sha256": policy.fingerprint_sha256,
        "experiment_id": rows[0].experiment_id,
        "baseline_family": policy.baseline_family,
        "challenger_family": policy.challenger_family,
        "status": "ELIGIBLE_FOR_HUMAN_REVIEW" if eligible else "KEEP_CHALLENGER",
        "checks": checks,
        "matches": bootstrap["matches"],
        "blocks": bootstrap["blocks"],
        "competitions": len(competitions),
        "relative_log_loss_improvement": relative_improvement,
        "max_classwise_ece_degradation": ece_degradation,
    }
    return {
        **core,
        "schema_version": PROMOTION_REVIEW_VERSION,
        "automatic_promotion": False,
        "failed_checks": failed_checks,
        "policy": policy.to_dict(),
        "policy_artifact_source": policy.artifact_source,
        "baseline_aggregate": baseline_aggregate,
        "challenger_aggregate": challenger_aggregate,
        "bootstrap": bootstrap,
        "rolling_stability": rolling,
        "report_sha256": sha256_payload(core),
        "note": (
            "ELIGIBLE_FOR_HUMAN_REVIEW 只代表可進入人工 promotion review；"
            "本函式永遠不會自動修改 live predictor。"
        ),
    }
