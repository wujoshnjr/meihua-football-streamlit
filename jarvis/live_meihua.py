from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
from math import exp, isfinite
from pathlib import Path
from typing import Any

from jarvis.provenance import sha256_payload
from jarvis.research.residual import (
    GENERIC_RESIDUAL_FIT_VERSION,
    ResidualLambdaFit,
    apply_residual_lambda_adjustment,
)
from meihua import (
    MEIHUA_OUTCOME_DESIGN_VERSION,
    MeihuaSnapshot,
    build_meihua_snapshot,
    meihua_outcome_numeric_features,
)
from qimen.prediction import PredictionResult, ScoreProbability
from qimen.runtime import is_formal_git_commit
from qimen.training import dixon_coles_tau, temperature_scale_probabilities


LIVE_MEIHUA_VERSION = "jarvis-live-meihua-v0.1.0"
LIVE_MEIHUA_ARTIFACT_VERSION = "jarvis-live-meihua-artifact-v1.0.0"
DEPLOYED_MEIHUA_ARTIFACT_PATH = Path("artifacts/live_meihua.json")


def _valid_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _residual_fit_core(fit: ResidualLambdaFit) -> dict[str, Any]:
    return {
        "schema_version": fit.schema_version,
        "feature_family": fit.feature_family,
        "feature_schema_version": fit.feature_schema_version,
        "feature_names": fit.feature_names,
        "home_coefficients": fit.home_coefficients,
        "away_coefficients": fit.away_coefficients,
        "l2_penalty": fit.l2_penalty,
        "matches": fit.matches,
        "converged_home": fit.converged_home,
        "converged_away": fit.converged_away,
        "iterations_home": fit.iterations_home,
        "iterations_away": fit.iterations_away,
        "training_started_at": fit.training_started_at.isoformat(),
        "training_ended_at": fit.training_ended_at.isoformat(),
        "git_commit": fit.git_commit,
        "training_data_sha256": fit.training_data_sha256,
    }


@dataclass(frozen=True)
class LiveMeihuaArtifact:
    """One fully frozen, human-approved M2 deployment artifact.

    The live layer deliberately refuses raw coefficients or an isolated residual
    fit. A deployable artifact must also bind the validation-selected shrinkage,
    score model, M2-specific calibration, promotion review, approval metadata,
    and source commit. This keeps TEST_UNTOUCHED results from becoming an
    informal tuning surface at deployment time.
    """

    schema_version: str
    model_family: str
    feature_family: str
    feature_schema_version: str
    baseline_model_version: str
    score_model: str
    dixon_coles_rho: float
    max_goals: int
    residual_fit: ResidualLambdaFit
    shrinkage_alpha: float
    tuning_artifact_sha256: str
    calibration_temperature: float
    calibration_artifact_sha256: str
    promotion_report_sha256: str
    promotion_status: str
    approved_for_live: bool
    approved_at: datetime
    approved_by: str
    source_commit: str
    artifact_sha256: str

    @property
    def artifact_source(self) -> str:
        return f"live-meihua-artifact:{self.artifact_sha256}"

    def _core(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "model_family": self.model_family,
            "feature_family": self.feature_family,
            "feature_schema_version": self.feature_schema_version,
            "baseline_model_version": self.baseline_model_version,
            "score_model": self.score_model,
            "dixon_coles_rho": self.dixon_coles_rho,
            "max_goals": self.max_goals,
            "residual_artifact_sha256": self.residual_fit.artifact_sha256,
            "shrinkage_alpha": self.shrinkage_alpha,
            "tuning_artifact_sha256": self.tuning_artifact_sha256,
            "calibration_temperature": self.calibration_temperature,
            "calibration_artifact_sha256": self.calibration_artifact_sha256,
            "promotion_report_sha256": self.promotion_report_sha256,
            "promotion_status": self.promotion_status,
            "approved_for_live": self.approved_for_live,
            "approved_at": self.approved_at.isoformat(),
            "approved_by": self.approved_by.strip(),
            "source_commit": self.source_commit.strip().lower(),
        }

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.schema_version != LIVE_MEIHUA_ARTIFACT_VERSION:
            errors.append("live Meihua artifact schema_version 不相容")
        if self.model_family != "M2_MEIHUA":
            errors.append("live Meihua artifact 必須綁定 M2_MEIHUA")
        if self.feature_family != "MEIHUA":
            errors.append("live Meihua artifact feature_family 必須為 MEIHUA")
        if self.feature_schema_version != MEIHUA_OUTCOME_DESIGN_VERSION:
            errors.append("live Meihua artifact feature schema 與目前程式不一致")
        if not self.baseline_model_version.strip():
            errors.append("live Meihua artifact 缺少 baseline_model_version")
        if self.score_model not in {"INDEPENDENT_POISSON", "DIXON_COLES"}:
            errors.append("live Meihua artifact score_model 無效")
        if not isfinite(self.dixon_coles_rho) or not -0.25 <= self.dixon_coles_rho <= 0.25:
            errors.append("live Meihua artifact Dixon-Coles rho 無效")
        if self.score_model == "INDEPENDENT_POISSON" and abs(self.dixon_coles_rho) > 1e-15:
            errors.append("Independent Poisson live Meihua artifact 不可夾帶 rho")
        if isinstance(self.max_goals, bool) or not isinstance(self.max_goals, int) or not 5 <= self.max_goals <= 15:
            errors.append("live Meihua artifact max_goals 必須介於 5 與 15")
        if not isfinite(self.shrinkage_alpha) or not 0 <= self.shrinkage_alpha <= 1:
            errors.append("live Meihua artifact shrinkage_alpha 必須介於 0 與 1")
        if not isfinite(self.calibration_temperature) or not 0.25 <= self.calibration_temperature <= 4.0:
            errors.append("live Meihua calibration temperature 無效")
        for label, value in (
            ("tuning_artifact_sha256", self.tuning_artifact_sha256),
            ("calibration_artifact_sha256", self.calibration_artifact_sha256),
            ("promotion_report_sha256", self.promotion_report_sha256),
            ("artifact_sha256", self.artifact_sha256),
        ):
            if not _valid_sha256(value):
                errors.append(f"live Meihua {label} 無效")
        if self.promotion_status != "ELIGIBLE_FOR_HUMAN_REVIEW":
            errors.append("live Meihua artifact 尚未通過 promotion review")
        if self.approved_for_live is not True:
            errors.append("live Meihua artifact 尚未人工批准正式部署")
        if self.approved_at.tzinfo is None:
            errors.append("live Meihua approved_at 必須含時區")
        if not self.approved_by.strip():
            errors.append("live Meihua approved_by 不可空白")
        if not is_formal_git_commit(self.source_commit):
            errors.append("live Meihua source_commit 必須為正式 40–64 位 commit")

        fit = self.residual_fit
        if fit.schema_version != GENERIC_RESIDUAL_FIT_VERSION:
            errors.append("live Meihua residual schema_version 不相容")
        if fit.feature_family != self.feature_family or fit.feature_schema_version != self.feature_schema_version:
            errors.append("live Meihua residual feature family/schema 與 deployment artifact 不一致")
        if not fit.converged_home or not fit.converged_away:
            errors.append("live Meihua residual 尚未雙側收斂")
        if fit.matches < 200:
            errors.append("live Meihua residual 至少需要 200 場 TRAIN")
        if not is_formal_git_commit(fit.git_commit):
            errors.append("live Meihua residual 缺少正式 training commit")
        if not _valid_sha256(fit.training_data_sha256):
            errors.append("live Meihua residual training_data_sha256 無效")
        if sha256_payload(_residual_fit_core(fit)) != fit.artifact_sha256:
            errors.append("live Meihua residual artifact SHA-256 驗證失敗")
        if sha256_payload(self._core()) != self.artifact_sha256:
            errors.append("live Meihua deployment artifact SHA-256 驗證失敗")
        return errors

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["approved_at"] = self.approved_at.isoformat()
        payload["residual_fit"]["training_started_at"] = self.residual_fit.training_started_at.isoformat()
        payload["residual_fit"]["training_ended_at"] = self.residual_fit.training_ended_at.isoformat()
        payload["artifact_source"] = self.artifact_source
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LiveMeihuaArtifact":
        try:
            residual_payload = dict(payload["residual_fit"])
            residual = ResidualLambdaFit(
                schema_version=str(residual_payload["schema_version"]),
                feature_family=str(residual_payload["feature_family"]),
                feature_schema_version=str(residual_payload["feature_schema_version"]),
                feature_names=tuple(str(value) for value in residual_payload["feature_names"]),
                home_coefficients=tuple(float(value) for value in residual_payload["home_coefficients"]),
                away_coefficients=tuple(float(value) for value in residual_payload["away_coefficients"]),
                l2_penalty=float(residual_payload["l2_penalty"]),
                matches=int(residual_payload["matches"]),
                converged_home=bool(residual_payload["converged_home"]),
                converged_away=bool(residual_payload["converged_away"]),
                iterations_home=int(residual_payload["iterations_home"]),
                iterations_away=int(residual_payload["iterations_away"]),
                training_started_at=datetime.fromisoformat(str(residual_payload["training_started_at"])),
                training_ended_at=datetime.fromisoformat(str(residual_payload["training_ended_at"])),
                git_commit=str(residual_payload["git_commit"]),
                training_data_sha256=str(residual_payload["training_data_sha256"]),
                artifact_sha256=str(residual_payload["artifact_sha256"]),
            )
            artifact = cls(
                schema_version=str(payload["schema_version"]),
                model_family=str(payload["model_family"]),
                feature_family=str(payload["feature_family"]),
                feature_schema_version=str(payload["feature_schema_version"]),
                baseline_model_version=str(payload["baseline_model_version"]),
                score_model=str(payload["score_model"]),
                dixon_coles_rho=float(payload["dixon_coles_rho"]),
                max_goals=int(payload["max_goals"]),
                residual_fit=residual,
                shrinkage_alpha=float(payload["shrinkage_alpha"]),
                tuning_artifact_sha256=str(payload["tuning_artifact_sha256"]),
                calibration_temperature=float(payload["calibration_temperature"]),
                calibration_artifact_sha256=str(payload["calibration_artifact_sha256"]),
                promotion_report_sha256=str(payload["promotion_report_sha256"]),
                promotion_status=str(payload["promotion_status"]),
                approved_for_live=bool(payload["approved_for_live"]),
                approved_at=datetime.fromisoformat(str(payload["approved_at"])),
                approved_by=str(payload["approved_by"]),
                source_commit=str(payload["source_commit"]),
                artifact_sha256=str(payload["artifact_sha256"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("live Meihua artifact JSON 欄位不完整或型別無效") from exc
        errors = artifact.validate()
        if errors:
            raise ValueError("；".join(errors))
        return artifact


@dataclass(frozen=True)
class LiveMeihuaForecast:
    integration_version: str
    mode: str
    active_probability_adjustment: bool
    model_family: str
    model_version: str
    meihua_snapshot: MeihuaSnapshot
    meihua_numeric_features: dict[str, float]
    meihua_feature_sha256: str
    artifact_source: str
    baseline_expected_home_goals: float
    baseline_expected_away_goals: float
    expected_home_goals: float
    expected_away_goals: float
    raw_home_win_probability: float
    raw_draw_probability: float
    raw_away_win_probability: float
    home_win_probability: float
    draw_probability: float
    away_win_probability: float
    predicted_result: str
    decision_margin: float
    top_scorelines: tuple[ScoreProbability, ...]
    forecast_sha256: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["meihua_snapshot"] = self.meihua_snapshot.to_dict()
        return payload


def load_deployed_live_meihua_artifact(
    path: str | Path = DEPLOYED_MEIHUA_ARTIFACT_PATH,
) -> LiveMeihuaArtifact | None:
    artifact_path = Path(path)
    if not artifact_path.exists():
        return None
    try:
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("無法讀取 deployed live Meihua artifact") from exc
    if not isinstance(payload, dict):
        raise ValueError("deployed live Meihua artifact 必須是 JSON object")
    return LiveMeihuaArtifact.from_dict(payload)


def _poisson_probabilities(rate: float, max_goals: int) -> list[float]:
    probabilities = [exp(-rate)]
    for goals in range(1, max_goals + 1):
        probabilities.append(probabilities[-1] * rate / goals)
    return probabilities


def _score_adjusted_lambdas(
    home_lambda: float,
    away_lambda: float,
    artifact: LiveMeihuaArtifact,
) -> tuple[
    float,
    float,
    float,
    float,
    float,
    float,
    tuple[ScoreProbability, ...],
]:
    home_goal_probs = _poisson_probabilities(home_lambda, artifact.max_goals)
    away_goal_probs = _poisson_probabilities(away_lambda, artifact.max_goals)
    raw_grid: list[tuple[int, int, float]] = []
    for home_goals, home_probability in enumerate(home_goal_probs):
        for away_goals, away_probability in enumerate(away_goal_probs):
            tau = 1.0
            if artifact.score_model == "DIXON_COLES":
                tau = dixon_coles_tau(
                    home_goals,
                    away_goals,
                    home_lambda,
                    away_lambda,
                    artifact.dixon_coles_rho,
                )
                if tau <= 0:
                    raise ValueError("deployed Meihua artifact 的 Dixon-Coles rho 使比分校正係數不為正")
            raw_grid.append((home_goals, away_goals, home_probability * away_probability * tau))
    grid_mass = sum(probability for _, _, probability in raw_grid)
    if not isfinite(grid_mass) or grid_mass <= 0:
        raise ValueError("Meihua 調整後比分矩陣總質量無效")
    grid = tuple(
        ScoreProbability(home, away, probability / grid_mass)
        for home, away, probability in raw_grid
    )
    raw_home = sum(item.probability for item in grid if item.home_goals > item.away_goals)
    raw_draw = sum(item.probability for item in grid if item.home_goals == item.away_goals)
    raw_away = sum(item.probability for item in grid if item.home_goals < item.away_goals)
    home, draw, away = temperature_scale_probabilities(
        (raw_home, raw_draw, raw_away),
        artifact.calibration_temperature,
    )
    return raw_home, raw_draw, raw_away, home, draw, away, grid


def build_live_meihua_forecast(
    base_prediction: PredictionResult,
    *,
    event_at: datetime,
    timezone_name: str,
    artifact: LiveMeihuaArtifact | None = None,
) -> LiveMeihuaForecast:
    """Build the production Meihua layer on top of one frozen Football forecast.

    Meihua is always computed and fingerprinted. Without a fully approved M2
    deployment artifact the returned probabilities are *exactly* the frozen
    Football probabilities. This makes live integration observable without
    inventing coefficients. With a valid artifact, M2 adjusts the Football
    lambdas and is rescored under the artifact-bound score/calibration model.
    """

    snapshot = build_meihua_snapshot(event_at, timezone_name)
    features = meihua_outcome_numeric_features(snapshot)
    feature_sha = sha256_payload(features)

    if artifact is None:
        core = {
            "integration_version": LIVE_MEIHUA_VERSION,
            "mode": "ADVISORY_ONLY_NO_PROMOTED_ARTIFACT",
            "base_model_version": base_prediction.model_version,
            "meihua_feature_sha256": feature_sha,
            "artifact_source": "",
            "expected_home_goals": base_prediction.expected_home_goals,
            "expected_away_goals": base_prediction.expected_away_goals,
            "probabilities": (
                base_prediction.home_win_probability,
                base_prediction.draw_probability,
                base_prediction.away_win_probability,
            ),
        }
        return LiveMeihuaForecast(
            integration_version=LIVE_MEIHUA_VERSION,
            mode="ADVISORY_ONLY_NO_PROMOTED_ARTIFACT",
            active_probability_adjustment=False,
            model_family="M0_FOOTBALL",
            model_version=base_prediction.model_version,
            meihua_snapshot=snapshot,
            meihua_numeric_features=features,
            meihua_feature_sha256=feature_sha,
            artifact_source="",
            baseline_expected_home_goals=base_prediction.expected_home_goals,
            baseline_expected_away_goals=base_prediction.expected_away_goals,
            expected_home_goals=base_prediction.expected_home_goals,
            expected_away_goals=base_prediction.expected_away_goals,
            raw_home_win_probability=base_prediction.raw_home_win_probability,
            raw_draw_probability=base_prediction.raw_draw_probability,
            raw_away_win_probability=base_prediction.raw_away_win_probability,
            home_win_probability=base_prediction.home_win_probability,
            draw_probability=base_prediction.draw_probability,
            away_win_probability=base_prediction.away_win_probability,
            predicted_result=base_prediction.predicted_result,
            decision_margin=base_prediction.decision_margin,
            top_scorelines=base_prediction.top_scorelines,
            forecast_sha256=sha256_payload(core),
        )

    errors = artifact.validate()
    if errors:
        raise ValueError("；".join(errors))
    if base_prediction.model_version != artifact.baseline_model_version:
        raise ValueError("live Meihua artifact 綁定的 Football baseline 與目前預測不一致")
    if base_prediction.score_model != artifact.score_model:
        raise ValueError("live Meihua artifact score_model 與目前 Football baseline 不一致")
    try:
        base_max_goals = int(base_prediction.model_input["max_goals"])
        base_rho = float(base_prediction.model_input["dixon_coles_rho"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Football baseline 缺少 Meihua deployment 所需 score-model provenance") from exc
    if base_max_goals != artifact.max_goals or abs(base_rho - artifact.dixon_coles_rho) > 1e-15:
        raise ValueError("live Meihua artifact 的 score grid/rho 與目前 Football baseline 不一致")

    if artifact.shrinkage_alpha <= 1e-15:
        mode = "PROMOTED_M2_BASELINE_FALLBACK"
        active = False
        adjusted_home = base_prediction.expected_home_goals
        adjusted_away = base_prediction.expected_away_goals
        raw_home = base_prediction.raw_home_win_probability
        raw_draw = base_prediction.raw_draw_probability
        raw_away = base_prediction.raw_away_win_probability
        home = base_prediction.home_win_probability
        draw = base_prediction.draw_probability
        away = base_prediction.away_win_probability
        grid = base_prediction.top_scorelines
    else:
        mode = "ACTIVE_PROMOTED_M2_MEIHUA"
        active = True
        adjusted_home, adjusted_away = apply_residual_lambda_adjustment(
            base_prediction.expected_home_goals,
            base_prediction.expected_away_goals,
            features,
            artifact.residual_fit,
            feature_family="MEIHUA",
            feature_schema_version=MEIHUA_OUTCOME_DESIGN_VERSION,
            shrinkage_alpha=artifact.shrinkage_alpha,
        )
        raw_home, raw_draw, raw_away, home, draw, away, full_grid = _score_adjusted_lambdas(
            adjusted_home,
            adjusted_away,
            artifact,
        )
        grid = tuple(sorted(full_grid, key=lambda item: item.probability, reverse=True)[:5])

    outcomes = {"主勝": home, "和局": draw, "客勝": away}
    ordered = sorted(outcomes.items(), key=lambda item: item[1], reverse=True)
    predicted_result = ordered[0][0]
    decision_margin = ordered[0][1] - ordered[1][1]
    model_version = (
        f"{LIVE_MEIHUA_VERSION}:M2:{artifact.artifact_sha256[:12]}"
        if active
        else base_prediction.model_version
    )
    core = {
        "integration_version": LIVE_MEIHUA_VERSION,
        "mode": mode,
        "base_model_version": base_prediction.model_version,
        "meihua_feature_sha256": feature_sha,
        "artifact_source": artifact.artifact_source,
        "expected_home_goals": adjusted_home,
        "expected_away_goals": adjusted_away,
        "probabilities": (home, draw, away),
    }
    return LiveMeihuaForecast(
        integration_version=LIVE_MEIHUA_VERSION,
        mode=mode,
        active_probability_adjustment=active,
        model_family="M2_MEIHUA" if active else "M0_FOOTBALL",
        model_version=model_version,
        meihua_snapshot=snapshot,
        meihua_numeric_features=features,
        meihua_feature_sha256=feature_sha,
        artifact_source=artifact.artifact_source,
        baseline_expected_home_goals=base_prediction.expected_home_goals,
        baseline_expected_away_goals=base_prediction.expected_away_goals,
        expected_home_goals=adjusted_home,
        expected_away_goals=adjusted_away,
        raw_home_win_probability=raw_home,
        raw_draw_probability=raw_draw,
        raw_away_win_probability=raw_away,
        home_win_probability=home,
        draw_probability=draw,
        away_win_probability=away,
        predicted_result=predicted_result,
        decision_margin=decision_margin,
        top_scorelines=grid,
        forecast_sha256=sha256_payload(core),
    )
