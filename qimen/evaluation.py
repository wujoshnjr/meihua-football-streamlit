from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from math import ceil, log
import random
from typing import Iterable

from .football import FootballReading
from .integrity import sha256_payload
from .prediction import (
    PredictionResult,
    data_snapshot_payload,
    football_feature_payload,
    model_spec_payload,
)
from .runtime import is_formal_git_commit


@dataclass(frozen=True)
class LockedScenarios:
    match_id: str
    event_at: datetime
    locked_at: datetime
    scenario_titles: tuple[str, ...]
    fingerprint_sha256: str

    def to_dict(self):
        data = asdict(self)
        data["event_at"] = self.event_at.isoformat()
        data["locked_at"] = self.locked_at.isoformat()
        return data


@dataclass(frozen=True)
class LockedPrediction:
    """Immutable fields required to score a genuinely pre-match forecast."""

    match_id: str
    event_at: datetime
    locked_at: datetime
    data_as_of: datetime
    forecast_horizon: str
    lineup_status: str
    competition: str
    evaluation_block: str
    dataset_role: str
    experiment_id: str
    model_version: str
    score_model: str
    qimen_feature_version: str
    qimen_mode: str
    expected_home_goals: float
    expected_away_goals: float
    home_win_probability: float
    draw_probability: float
    away_win_probability: float
    predicted_result: str
    top_scorelines: tuple[tuple[int, int, float], ...]
    prediction_payload: dict[str, object]
    fingerprint_sha256: str

    def to_dict(self):
        data = asdict(self)
        data["event_at"] = self.event_at.isoformat()
        data["locked_at"] = self.locked_at.isoformat()
        data["data_as_of"] = self.data_as_of.isoformat()
        return data


def lock_scenarios(
    match_id: str,
    event_at: datetime,
    locked_at: datetime,
    reading: FootballReading,
) -> LockedScenarios:
    if event_at.tzinfo is None or locked_at.tzinfo is None:
        raise ValueError("event_at 與 locked_at 必須含時區")
    if locked_at >= event_at:
        raise ValueError("情境必須在開賽前鎖定")
    titles = tuple(item.title for item in reading.scenarios)
    fingerprint = sha256_payload({
        "match_id": match_id,
        "event_at": event_at.isoformat(),
        "locked_at": locked_at.isoformat(),
        "scenario_titles": titles,
    })
    return LockedScenarios(match_id, event_at, locked_at, titles, fingerprint)


def evaluate_scenarios(
    locked: LockedScenarios,
    observed_tags: Iterable[str],
    *,
    top_k: int = 3,
) -> dict[str, object]:
    """Evaluate pre-locked qualitative scenarios without inventing probabilities."""

    observed = {tag.strip() for tag in observed_tags if tag.strip()}
    selected = locked.scenario_titles[:top_k]
    hits = tuple(title for title in selected if title in observed)
    return {
        "match_id": locked.match_id,
        "top_k": top_k,
        "selected": selected,
        "observed": tuple(sorted(observed)),
        "hits": hits,
        "precision_at_k": len(hits) / len(selected) if selected else 0.0,
        "note": "只評估賽前鎖定情境與人工標註事件的一致性，不回推出勝率。",
    }


def lock_prediction(
    match_id: str,
    event_at: datetime,
    locked_at: datetime,
    prediction: PredictionResult,
    *,
    competition: str = "",
    evaluation_block: str = "",
    dataset_role: str = "PROSPECTIVE",
    experiment_id: str = "",
) -> LockedPrediction:
    if not match_id.strip():
        raise ValueError("match_id 不可空白")
    if event_at.tzinfo is None or locked_at.tzinfo is None:
        raise ValueError("event_at 與 locked_at 必須含時區")
    if locked_at >= event_at:
        raise ValueError("預測必須在開賽前鎖定")
    valid_dataset_roles = {"PROSPECTIVE", "TRAIN", "VALIDATION", "CALIBRATION", "TEST_UNTOUCHED"}
    if dataset_role not in valid_dataset_roles:
        raise ValueError("dataset_role 必須為 PROSPECTIVE、TRAIN、VALIDATION、CALIBRATION 或 TEST_UNTOUCHED")
    if dataset_role == "TEST_UNTOUCHED" and not experiment_id.strip():
        raise ValueError("TEST_UNTOUCHED 預測鎖必須保存 experiment_id")
    if dataset_role == "TEST_UNTOUCHED" and (not competition.strip() or not evaluation_block.strip()):
        raise ValueError("TEST_UNTOUCHED 預測鎖必須保存 competition 與 evaluation_block")

    data_as_of_raw = prediction.model_input.get("data_as_of")
    if not isinstance(data_as_of_raw, str) or not data_as_of_raw:
        raise ValueError("可計入盲測的預測必須保存統計資料截至時間")
    try:
        data_as_of = datetime.fromisoformat(data_as_of_raw)
    except ValueError as exc:
        raise ValueError("統計資料截至時間必須為 ISO 8601") from exc
    if data_as_of.tzinfo is None:
        raise ValueError("統計資料截至時間必須含時區")
    if data_as_of > locked_at:
        raise ValueError("統計資料截至時間不可晚於預測鎖定時間")

    horizon = prediction.forecast_horizon
    if horizon == "EARLY":
        horizon_cutoff = event_at - timedelta(hours=6)
    elif horizon == "LINEUP":
        horizon_cutoff = event_at - timedelta(minutes=30)
        if prediction.lineup_status != "OFFICIAL_BOTH":
            raise ValueError("LINEUP 預測必須確認雙方官方先發")
    else:
        raise ValueError("預測時點必須為 EARLY 或 LINEUP")
    if data_as_of > horizon_cutoff:
        raise ValueError(f"{horizon} 資料截至時間晚於註冊封盤界線")
    if locked_at > horizon_cutoff:
        raise ValueError(f"{horizon} 預測鎖定時間晚於註冊封盤界線")

    probabilities = (
        prediction.home_win_probability,
        prediction.draw_probability,
        prediction.away_win_probability,
    )
    if any(value < 0 or value > 1 for value in probabilities):
        raise ValueError("1X2 機率必須介於 0 與 1")
    if abs(sum(probabilities) - 1.0) > 1e-9:
        raise ValueError("1X2 機率總和必須為 1")

    required_hashes = {
        "source_manifest_sha256",
        "data_snapshot_sha256",
        "football_feature_sha256",
        "qimen_feature_sha256",
        "model_spec_sha256",
    }
    missing_hashes = required_hashes - prediction.provenance.keys()
    if missing_hashes:
        raise ValueError("預測 provenance 缺少必要指紋：" + "、".join(sorted(missing_hashes)))
    for key in required_hashes:
        value = prediction.provenance[key]
        if not isinstance(value, str) or len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            raise ValueError(f"預測 provenance 的 {key} 不是有效 SHA-256")
    source_manifest = prediction.provenance.get("source_manifest", ())
    if sha256_payload(source_manifest) != prediction.provenance["source_manifest_sha256"]:
        raise ValueError("來源清單與 source_manifest_sha256 不一致")
    if sha256_payload(
        data_snapshot_payload(prediction.model_input, source_manifest)
    ) != prediction.provenance["data_snapshot_sha256"]:
        raise ValueError("模型輸入或來源清單在建立預測後已被修改")
    if sha256_payload(
        football_feature_payload(prediction.model_input)
    ) != prediction.provenance["football_feature_sha256"]:
        raise ValueError("足球特徵在建立預測後已被修改")
    if sha256_payload(prediction.qimen_features) != prediction.provenance["qimen_feature_sha256"]:
        raise ValueError("奇門特徵在建立預測後已被修改")
    if sha256_payload(
        model_spec_payload(prediction.model_input, prediction.model_version)
    ) != prediction.provenance["model_spec_sha256"]:
        raise ValueError("模型規格在建立預測後已被修改")

    top_scorelines = tuple(
        (item.home_goals, item.away_goals, item.probability)
        for item in prediction.top_scorelines
    )
    prediction_payload = prediction.to_dict()
    core = {
        "match_id": match_id.strip(),
        "event_at": event_at.isoformat(),
        "locked_at": locked_at.isoformat(),
        "competition": competition.strip(),
        "evaluation_block": evaluation_block.strip(),
        "dataset_role": dataset_role,
        "experiment_id": experiment_id.strip(),
        "prediction": prediction_payload,
    }
    fingerprint = sha256_payload(core)
    return LockedPrediction(
        match_id=match_id.strip(),
        event_at=event_at,
        locked_at=locked_at,
        data_as_of=data_as_of,
        forecast_horizon=horizon,
        lineup_status=prediction.lineup_status,
        competition=competition.strip(),
        evaluation_block=evaluation_block.strip(),
        dataset_role=dataset_role,
        experiment_id=experiment_id.strip(),
        model_version=prediction.model_version,
        score_model=prediction.score_model,
        qimen_feature_version=prediction.qimen_feature_version,
        qimen_mode=prediction.qimen_mode,
        expected_home_goals=prediction.expected_home_goals,
        expected_away_goals=prediction.expected_away_goals,
        home_win_probability=prediction.home_win_probability,
        draw_probability=prediction.draw_probability,
        away_win_probability=prediction.away_win_probability,
        predicted_result=prediction.predicted_result,
        top_scorelines=top_scorelines,
        prediction_payload=prediction_payload,
        fingerprint_sha256=fingerprint,
    )


def evaluate_prediction(
    locked: LockedPrediction,
    actual_home_goals: int,
    actual_away_goals: int,
) -> dict[str, object]:
    """Score a locked 1X2 distribution and exact-score candidate set."""

    if (
        isinstance(actual_home_goals, bool)
        or isinstance(actual_away_goals, bool)
        or not isinstance(actual_home_goals, int)
        or not isinstance(actual_away_goals, int)
        or actual_home_goals < 0
        or actual_away_goals < 0
    ):
        raise ValueError("實際進球必須為非負整數")

    actual_result = (
        "主勝"
        if actual_home_goals > actual_away_goals
        else "客勝"
        if actual_home_goals < actual_away_goals
        else "和局"
    )
    probability_by_result = {
        "主勝": locked.home_win_probability,
        "和局": locked.draw_probability,
        "客勝": locked.away_win_probability,
    }
    outcome_order = ("主勝", "和局", "客勝")
    probability_vector = [probability_by_result[item] for item in outcome_order]
    observation_vector = [1.0 if item == actual_result else 0.0 for item in outcome_order]
    brier_score = sum(
        (probability - observation) ** 2
        for probability, observation in zip(probability_vector, observation_vector)
    )
    ranked_probability_score = sum(
        (
            sum(probability_vector[: index + 1])
            - sum(observation_vector[: index + 1])
        ) ** 2
        for index in range(len(outcome_order) - 1)
    ) / (len(outcome_order) - 1)

    actual_score = (actual_home_goals, actual_away_goals)
    ranked_scores = tuple((home, away) for home, away, _ in locked.top_scorelines)
    provenance = locked.prediction_payload.get("provenance", {})
    if not isinstance(provenance, dict):
        provenance = {}
    return {
        "match_id": locked.match_id,
        "competition": locked.competition,
        "evaluation_block": locked.evaluation_block,
        "dataset_role": locked.dataset_role,
        "experiment_id": locked.experiment_id,
        "model_version": locked.model_version,
        "score_model": locked.score_model,
        "qimen_mode": locked.qimen_mode,
        "forecast_horizon": locked.forecast_horizon,
        "calibration_status": locked.prediction_payload.get("calibration_status", ""),
        "actual_result": actual_result,
        "predicted_result": locked.predicted_result,
        "home_win_probability": locked.home_win_probability,
        "draw_probability": locked.draw_probability,
        "away_win_probability": locked.away_win_probability,
        "raw_home_win_probability": locked.prediction_payload.get("raw_home_win_probability", ""),
        "raw_draw_probability": locked.prediction_payload.get("raw_draw_probability", ""),
        "raw_away_win_probability": locked.prediction_payload.get("raw_away_win_probability", ""),
        "top1_result_correct": locked.predicted_result == actual_result,
        "actual_result_probability": probability_by_result[actual_result],
        "log_loss": -log(max(probability_by_result[actual_result], 1e-15)),
        "brier_score": brier_score,
        "ranked_probability_score": ranked_probability_score,
        "actual_score": actual_score,
        "exact_score_top1_hit": bool(ranked_scores and ranked_scores[0] == actual_score),
        "exact_score_top3_hit": actual_score in ranked_scores[:3],
        "lock_fingerprint_sha256": locked.fingerprint_sha256,
        "data_snapshot_sha256": provenance.get("data_snapshot_sha256", ""),
        "football_feature_sha256": provenance.get("football_feature_sha256", ""),
        "qimen_feature_sha256": provenance.get("qimen_feature_sha256", ""),
        "model_spec_sha256": provenance.get("model_spec_sha256", ""),
        "git_commit": provenance.get("git_commit", ""),
        "source_manifest_entries": len(provenance.get("source_manifest", ())),
        "note": "只評估賽前鎖定輸出；低 log loss、Brier 與 RPS 較佳。",
    }


def aggregate_prediction_evaluations(
    evaluations: Iterable[dict[str, object]],
    *,
    total_matches: int | None = None,
    calibration_bins: int = 10,
) -> dict[str, float | int]:
    rows = list(evaluations)
    if not rows:
        raise ValueError("至少需要一筆評估結果")
    if calibration_bins < 2:
        raise ValueError("校準分箱至少需要 2 箱")
    count = len(rows)
    if total_matches is not None and total_matches < count:
        raise ValueError("total_matches 不可小於已評估場次")

    labels = ("主勝", "和局", "客勝")
    f1_by_label: dict[str, float] = {}
    recall_by_label: dict[str, float] = {}
    for label in labels:
        true_positive = sum(
            row["actual_result"] == label and row["predicted_result"] == label
            for row in rows
        )
        false_positive = sum(
            row["actual_result"] != label and row["predicted_result"] == label
            for row in rows
        )
        false_negative = sum(
            row["actual_result"] == label and row["predicted_result"] != label
            for row in rows
        )
        denominator = 2 * true_positive + false_positive + false_negative
        f1_by_label[label] = 2 * true_positive / denominator if denominator else 0.0
        recall_denominator = true_positive + false_negative
        recall_by_label[label] = true_positive / recall_denominator if recall_denominator else 0.0

    def binned_gap(probabilities: list[float], observations: list[float]) -> float:
        weighted_gap = 0.0
        for bin_index in range(calibration_bins):
            lower = bin_index / calibration_bins
            upper = (bin_index + 1) / calibration_bins
            members = [
                index
                for index, probability in enumerate(probabilities)
                if lower <= probability < upper
                or (bin_index == calibration_bins - 1 and probability == 1.0)
            ]
            if not members:
                continue
            mean_probability = sum(probabilities[index] for index in members) / len(members)
            mean_observation = sum(observations[index] for index in members) / len(members)
            weighted_gap += len(members) / count * abs(mean_probability - mean_observation)
        return weighted_gap

    probability_keys = {
        "主勝": "home_win_probability",
        "和局": "draw_probability",
        "客勝": "away_win_probability",
    }
    top_confidences = [
        max(float(row[key]) for key in probability_keys.values())
        for row in rows
    ]
    top_correct = [1.0 if bool(row["top1_result_correct"]) else 0.0 for row in rows]
    classwise_ece = sum(
        binned_gap(
            [float(row[probability_keys[label]]) for row in rows],
            [1.0 if row["actual_result"] == label else 0.0 for row in rows],
        )
        for label in labels
    ) / len(labels)
    return {
        "matches": count,
        "coverage": count / total_matches if total_matches else 1.0,
        "top1_result_accuracy": sum(bool(row["top1_result_correct"]) for row in rows) / count,
        "macro_f1": sum(f1_by_label.values()) / len(labels),
        "draw_recall": recall_by_label["和局"],
        "mean_log_loss": sum(float(row["log_loss"]) for row in rows) / count,
        "mean_brier_score": sum(float(row["brier_score"]) for row in rows) / count,
        "mean_ranked_probability_score": sum(float(row["ranked_probability_score"]) for row in rows) / count,
        "exact_score_top1_accuracy": sum(bool(row["exact_score_top1_hit"]) for row in rows) / count,
        "exact_score_top3_accuracy": sum(bool(row["exact_score_top3_hit"]) for row in rows) / count,
        "ece_top_label": binned_gap(top_confidences, top_correct),
        "ece_classwise": classwise_ece,
    }


def _paired_rows(
    champion: Iterable[dict[str, object]],
    challenger: Iterable[dict[str, object]],
) -> list[tuple[dict[str, object], dict[str, object]]]:
    def by_id(rows: Iterable[dict[str, object]], label: str) -> dict[str, dict[str, object]]:
        indexed: dict[str, dict[str, object]] = {}
        for row in rows:
            match_id = str(row.get("match_id", "")).strip()
            if not match_id:
                raise ValueError(f"{label} 評估缺少 match_id")
            if match_id in indexed:
                raise ValueError(f"{label} 評估有重複 match_id：{match_id}")
            indexed[match_id] = row
        return indexed

    champion_by_id = by_id(champion, "champion")
    challenger_by_id = by_id(challenger, "challenger")
    if set(champion_by_id) != set(challenger_by_id):
        raise ValueError("champion 與 challenger 必須使用完全相同的比賽集合")
    pairs = [(champion_by_id[key], challenger_by_id[key]) for key in sorted(champion_by_id)]
    for champion_row, challenger_row in pairs:
        for field in (
            "actual_result",
            "forecast_horizon",
            "dataset_role",
            "experiment_id",
            "data_snapshot_sha256",
            "football_feature_sha256",
            "qimen_feature_sha256",
            "git_commit",
            "calibration_status",
        ):
            champion_value = str(champion_row.get(field, "")).strip()
            challenger_value = str(challenger_row.get(field, "")).strip()
            if champion_value != challenger_value:
                raise ValueError(f"配對預測的 {field} 必須一致")
    return pairs


def _percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("無法對空樣本計算分位數")
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def compare_prediction_models(
    champion: Iterable[dict[str, object]],
    challenger: Iterable[dict[str, object]],
    *,
    metric: str = "log_loss",
    bootstrap_samples: int = 2000,
    seed: int = 20260815,
) -> dict[str, object]:
    """Paired competition/matchweek block bootstrap.

    The returned delta is challenger minus champion, so a negative value is an
    improvement for loss metrics. Missing block metadata falls back to one block
    per match and is explicitly reported.
    """

    if bootstrap_samples < 100:
        raise ValueError("bootstrap_samples 至少為 100")
    pairs = _paired_rows(champion, challenger)
    if not pairs:
        raise ValueError("至少需要一組配對評估")

    block_rows: dict[tuple[str, str], list[tuple[float, float]]] = {}
    fallback_matches = 0
    champion_values: list[float] = []
    challenger_values: list[float] = []
    for champion_row, challenger_row in pairs:
        try:
            champion_value = float(champion_row[metric])
            challenger_value = float(challenger_row[metric])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"評估缺少可用指標：{metric}") from exc
        champion_values.append(champion_value)
        challenger_values.append(challenger_value)
        competition = str(champion_row.get("competition", "")).strip()
        block = str(champion_row.get("evaluation_block", "")).strip()
        if (
            competition != str(challenger_row.get("competition", "")).strip()
            or block != str(challenger_row.get("evaluation_block", "")).strip()
        ):
            raise ValueError("配對預測的 competition／evaluation_block 必須一致")
        if not competition or not block:
            match_id = str(champion_row["match_id"])
            key = ("__MATCH_FALLBACK__", match_id)
            fallback_matches += 1
        else:
            key = (competition, block)
        block_rows.setdefault(key, []).append((champion_value, challenger_value))

    block_keys = sorted(block_rows)
    rng = random.Random(seed)
    bootstrap_deltas: list[float] = []
    for _ in range(bootstrap_samples):
        sampled_pairs: list[tuple[float, float]] = []
        for _ in block_keys:
            sampled_pairs.extend(block_rows[rng.choice(block_keys)])
        bootstrap_deltas.append(
            sum(challenger_value - champion_value for champion_value, challenger_value in sampled_pairs)
            / len(sampled_pairs)
        )

    champion_mean = sum(champion_values) / len(champion_values)
    challenger_mean = sum(challenger_values) / len(challenger_values)
    mean_delta = challenger_mean - champion_mean
    return {
        "metric": metric,
        "pairs": len(pairs),
        "blocks": len(block_keys),
        "fallback_match_blocks": fallback_matches,
        "champion_mean": champion_mean,
        "challenger_mean": challenger_mean,
        "mean_delta": mean_delta,
        "relative_improvement": (
            (champion_mean - challenger_mean) / champion_mean if champion_mean else 0.0
        ),
        "ci_level": 0.95,
        "ci_lower": _percentile(bootstrap_deltas, 0.025),
        "ci_upper": _percentile(bootstrap_deltas, 0.975),
        "seed": seed,
        "bootstrap_samples": bootstrap_samples,
        "interpretation": "delta < 0 代表 challenger 的 loss 較低。",
    }


def qimen_activation_gate(
    football_only: Iterable[dict[str, object]],
    football_plus_qimen: Iterable[dict[str, object]],
    *,
    bootstrap_samples: int = 2000,
    seed: int = 20260815,
) -> dict[str, object]:
    """Return eligibility for human review; this function never enables Qimen."""

    champion_rows = list(football_only)
    challenger_rows = list(football_plus_qimen)
    pairs = _paired_rows(champion_rows, challenger_rows)
    log_loss = compare_prediction_models(
        champion_rows,
        challenger_rows,
        metric="log_loss",
        bootstrap_samples=bootstrap_samples,
        seed=seed,
    )
    brier = compare_prediction_models(
        champion_rows,
        challenger_rows,
        metric="brier_score",
        bootstrap_samples=bootstrap_samples,
        seed=seed + 1,
    )
    champion_aggregate = aggregate_prediction_evaluations(champion_rows)
    challenger_aggregate = aggregate_prediction_evaluations(challenger_rows)

    blocks: dict[tuple[str, str], list[float]] = {}
    competitions: set[str] = set()
    experiment_ids: set[str] = set()
    all_untouched = True
    all_horizons_registered = True
    all_locks_valid = True
    all_provenance_valid = True
    all_git_commits_formal = True
    all_source_manifests_nonempty = True
    all_calibration_statuses_registered = True
    for champion_row, challenger_row in pairs:
        competition = str(champion_row.get("competition", "")).strip()
        block = str(champion_row.get("evaluation_block", "")).strip()
        if competition:
            competitions.add(competition)
        experiment_id = str(champion_row.get("experiment_id", "")).strip()
        if experiment_id:
            experiment_ids.add(experiment_id)
        if str(champion_row.get("dataset_role", "")).strip() != "TEST_UNTOUCHED":
            all_untouched = False
        if str(champion_row.get("forecast_horizon", "")).strip() not in {"EARLY", "LINEUP"}:
            all_horizons_registered = False
        for row in (champion_row, challenger_row):
            lock_hash = str(row.get("lock_fingerprint_sha256", "")).strip()
            if len(lock_hash) != 64 or any(character not in "0123456789abcdef" for character in lock_hash):
                all_locks_valid = False
            for field in (
                "data_snapshot_sha256",
                "football_feature_sha256",
                "qimen_feature_sha256",
                "model_spec_sha256",
            ):
                value = str(row.get(field, "")).strip()
                if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
                    all_provenance_valid = False
            if not is_formal_git_commit(str(row.get("git_commit", ""))):
                all_git_commits_formal = False
            try:
                source_manifest_entries = int(row.get("source_manifest_entries", 0))
            except (TypeError, ValueError):
                source_manifest_entries = 0
            if source_manifest_entries < 1:
                all_source_manifests_nonempty = False
            if str(row.get("calibration_status", "")).strip() not in {
                "UNCALIBRATED_V0",
                "CALIBRATED_TEMPERATURE_V1",
            }:
                all_calibration_statuses_registered = False
        if competition and block:
            blocks.setdefault((competition, block), []).append(
                float(challenger_row["log_loss"]) - float(champion_row["log_loss"])
            )
    improved_blocks = sum(sum(values) / len(values) < 0 for values in blocks.values())
    required_improved_blocks = ceil(0.8 * len(blocks)) if blocks else 0
    ece_degradation = (
        float(challenger_aggregate["ece_classwise"])
        - float(champion_aggregate["ece_classwise"])
    )
    checks = {
        "untouched_matches_at_least_5000": len(pairs) >= 5000 and all_untouched,
        "single_registered_experiment": len(experiment_ids) == 1,
        "registered_forecast_horizon": all_horizons_registered,
        "all_prediction_locks_valid": all_locks_valid,
        "all_provenance_hashes_valid": all_provenance_valid,
        "all_git_commits_formal": all_git_commits_formal,
        "all_source_manifests_nonempty": all_source_manifests_nonempty,
        "registered_calibration_status": all_calibration_statuses_registered,
        "at_least_5_rolling_blocks": len(blocks) >= 5,
        "at_least_2_competitions": len(competitions) >= 2,
        "log_loss_relative_improvement_at_least_0_5pct": float(log_loss["relative_improvement"]) >= 0.005,
        "log_loss_95pct_ci_below_zero": float(log_loss["ci_upper"]) < 0,
        "brier_same_direction": float(brier["mean_delta"]) < 0,
        "ece_degradation_at_most_0_005": ece_degradation <= 0.005,
        "at_least_80pct_blocks_improve": (
            bool(blocks) and improved_blocks >= required_improved_blocks
        ),
    }
    all_pass = all(checks.values())
    return {
        "status": "ELIGIBLE_FOR_REVIEW" if all_pass else "KEEP_SHADOW",
        "automatic_activation": False,
        "checks": checks,
        "matches": len(pairs),
        "competitions": len(competitions),
        "rolling_blocks": len(blocks),
        "improved_blocks": improved_blocks,
        "required_improved_blocks": required_improved_blocks,
        "log_loss_comparison": log_loss,
        "brier_comparison": brier,
        "ece_classwise_degradation": ece_degradation,
        "note": (
            "ELIGIBLE_FOR_REVIEW 只代表可進入人工、治理與重現性審查；"
            "程式不會自動把奇門權重從 SHADOW_ONLY 改為啟用。"
        ),
    }
