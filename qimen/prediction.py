from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from math import exp, isfinite
from typing import Any, Literal, TYPE_CHECKING

from .football import FootballReading
from .integrity import sha256_payload
from .models import QimenBoard
from .runtime import detect_git_commit
from .training import dixon_coles_tau, temperature_scale_probabilities

if TYPE_CHECKING:
    from .protocol import MatchInput


INDEPENDENT_POISSON_VERSION = "jarvis-independent-poisson-v0.3.0"
DIXON_COLES_VERSION = "jarvis-dixon-coles-challenger-v0.2.0"
QIMEN_FEATURE_VERSION = "jarvis-qimen-features-v0.2.0"
PROVENANCE_VERSION = "jarvis-provenance-v1.1.0"
CODE_VERSION = "7.2.0"

ScoreModel = Literal["INDEPENDENT_POISSON", "DIXON_COLES"]
ForecastHorizon = Literal["EARLY", "LINEUP"]
LineupStatus = Literal["UNAVAILABLE", "PARTIAL", "OFFICIAL_BOTH"]


def _is_artifact_reference(value: str, prefix: str) -> bool:
    reference = value.strip()
    if not reference.startswith(prefix):
        return False
    digest = reference.removeprefix(prefix)
    return len(digest) == 64 and all(character in "0123456789abcdef" for character in digest)


@dataclass(frozen=True)
class TeamForm:
    """A pre-match team snapshot using per-match rates known before kickoff."""

    matches: int
    goals_for_per_match: float
    goals_against_per_match: float
    xg_for_per_match: float | None = None
    xg_against_per_match: float | None = None
    effective_matches: float | None = None

    def validate(self, label: str) -> list[str]:
        errors: list[str] = []
        if isinstance(self.matches, bool) or not isinstance(self.matches, int):
            errors.append(f"{label}樣本場次必須為整數")
        elif self.matches < 0:
            errors.append(f"{label}樣本場次不可小於 0")
        for name, value in (
            ("場均進球", self.goals_for_per_match),
            ("場均失球", self.goals_against_per_match),
        ):
            if not isfinite(value) or value < 0:
                errors.append(f"{label}{name}必須為有限非負數")
        for name, value in (
            ("場均 xG", self.xg_for_per_match),
            ("場均 xGA", self.xg_against_per_match),
        ):
            if value is not None and (not isfinite(value) or value < 0):
                errors.append(f"{label}{name}必須為有限非負數")
        if self.effective_matches is not None:
            if not isfinite(self.effective_matches) or not 0 <= self.effective_matches <= self.matches:
                errors.append(f"{label}有效樣本權重必須介於 0 與實際樣本場次")
        return errors


@dataclass(frozen=True)
class PrematchModelInput:
    """Inputs for the first auditable JARVIS football baseline.

    League means encode the home advantage. Team rates are shrunk toward the
    league per-team mean so very small samples cannot dominate the forecast.
    """

    home: TeamForm
    away: TeamForm
    league_home_goals_per_match: float = 1.50
    league_away_goals_per_match: float = 1.20
    prior_match_equivalent: float = 5.0
    xg_weight: float = 0.65
    max_goals: int = 10
    data_as_of: datetime | None = None
    data_source: str = "manual_entry"
    score_model: ScoreModel = "INDEPENDENT_POISSON"
    dixon_coles_rho: float = 0.0
    rho_source: str = ""
    forecast_horizon: ForecastHorizon = "EARLY"
    lineup_status: LineupStatus = "UNAVAILABLE"
    calibration_temperature: float = 1.0
    calibration_source: str = ""

    def validate(self) -> list[str]:
        errors = [*self.home.validate("主隊"), *self.away.validate("客隊")]
        if (
            not isfinite(self.league_home_goals_per_match)
            or not isfinite(self.league_away_goals_per_match)
            or self.league_home_goals_per_match <= 0
            or self.league_away_goals_per_match <= 0
        ):
            errors.append("聯盟主客場均進球必須大於 0")
        if not isfinite(self.prior_match_equivalent) or self.prior_match_equivalent < 0:
            errors.append("先驗等效場次不可小於 0")
        if not isfinite(self.xg_weight) or not 0 <= self.xg_weight <= 1:
            errors.append("xG 權重必須介於 0 與 1")
        if (
            isinstance(self.max_goals, bool)
            or not isinstance(self.max_goals, int)
            or not 5 <= self.max_goals <= 15
        ):
            errors.append("比分矩陣上限必須介於 5 與 15")
        if self.data_as_of is not None and self.data_as_of.tzinfo is None:
            errors.append("統計資料截至時間必須含時區")
        if not self.data_source.strip():
            errors.append("統計資料來源不可空白")
        if self.score_model not in {"INDEPENDENT_POISSON", "DIXON_COLES"}:
            errors.append("比分模型必須為 INDEPENDENT_POISSON 或 DIXON_COLES")
        if not isfinite(self.dixon_coles_rho) or not -0.25 <= self.dixon_coles_rho <= 0.25:
            errors.append("Dixon–Coles rho 必須為 -0.25 至 0.25 的有限數")
        if self.score_model == "DIXON_COLES" and not _is_artifact_reference(
            self.rho_source, "dc-rho-fit:"
        ):
            errors.append("Dixon–Coles rho 必須引用 dc-rho-fit:<SHA-256> TRAIN artifact")
        if self.score_model == "INDEPENDENT_POISSON" and (
            abs(self.dixon_coles_rho) > 1e-15 or self.rho_source.strip()
        ):
            errors.append("獨立 Poisson 不可夾帶 Dixon–Coles rho 或 artifact")
        if self.forecast_horizon not in {"EARLY", "LINEUP"}:
            errors.append("預測時點必須為 EARLY 或 LINEUP")
        if self.lineup_status not in {"UNAVAILABLE", "PARTIAL", "OFFICIAL_BOTH"}:
            errors.append("先發狀態必須為 UNAVAILABLE、PARTIAL 或 OFFICIAL_BOTH")
        if self.forecast_horizon == "LINEUP" and self.lineup_status != "OFFICIAL_BOTH":
            errors.append("LINEUP 預測必須確認雙方官方先發")
        if not isfinite(self.calibration_temperature) or not 0.25 <= self.calibration_temperature <= 4.0:
            errors.append("calibration_temperature 必須為 0.25 至 4.0 的有限數")
        if not self.calibration_source.strip() and abs(self.calibration_temperature - 1.0) > 1e-15:
            errors.append("非 1.0 的 calibration_temperature 必須保存 CALIBRATION artifact 來源")
        if self.calibration_source.strip() and not _is_artifact_reference(
            self.calibration_source, "temperature-fit:"
        ):
            errors.append("calibration_source 必須引用 temperature-fit:<SHA-256> CALIBRATION artifact")
        return errors

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["data_as_of"] = self.data_as_of.isoformat() if self.data_as_of else None
        data["data_source"] = self.data_source.strip()
        data["rho_source"] = self.rho_source.strip()
        data["calibration_source"] = self.calibration_source.strip()
        return data


@dataclass(frozen=True)
class ScoreProbability:
    home_goals: int
    away_goals: int
    probability: float


@dataclass(frozen=True)
class PredictionResult:
    model_version: str
    score_model: str
    qimen_feature_version: str
    model_status: str
    calibration_status: str
    qimen_mode: str
    forecast_horizon: str
    lineup_status: str
    calibration_source: str
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
    score_grid_tail_mass: float
    model_input: dict[str, Any]
    qimen_features: dict[str, Any]
    provenance: dict[str, Any]
    data_warnings: tuple[str, ...]
    disclaimer: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _observed_rate(goals: float, xg: float | None, xg_weight: float) -> float:
    if xg is None:
        return goals
    return (1 - xg_weight) * goals + xg_weight * xg


def _shrunk_index(rate: float, matches: float, prior_rate: float, prior_matches: float) -> float:
    if matches == 0 and prior_matches == 0:
        return 1.0
    shrunk = (rate * matches + prior_rate * prior_matches) / (matches + prior_matches)
    return shrunk / prior_rate


def _poisson_probabilities(rate: float, max_goals: int) -> list[float]:
    probabilities = [exp(-rate)]
    for goals in range(1, max_goals + 1):
        probabilities.append(probabilities[-1] * rate / goals)
    return probabilities


def _source_manifest(match: MatchInput | None, model_input: PrematchModelInput) -> tuple[dict[str, Any], ...]:
    if match is None:
        return ()
    match_errors = match.validate()
    if match_errors:
        raise ValueError("；".join(match_errors))
    if model_input.data_as_of is None:
        raise ValueError("連結來源證據時必須保存統計資料截至時間")
    if model_input.data_as_of >= match.event_at:
        raise ValueError("統計資料截至時間必須早於開賽")

    rows: list[dict[str, Any]] = []
    for item in match.evidence:
        if item.retrieved_at > model_input.data_as_of:
            raise ValueError(f"來源「{item.title}」擷取時間晚於統計資料截至時間")
        rows.append({
            "title": item.title.strip(),
            "url": item.url.strip(),
            "published_at": item.published_at.isoformat(),
            "retrieved_at": item.retrieved_at.isoformat(),
            "category": item.category,
            "team": item.team,
            "material_update": item.material_update,
            "reliability": item.reliability,
        })

    if model_input.forecast_horizon == "LINEUP":
        lineup_rows = [item for item in match.evidence if item.category == "official_lineup"]
        covered_teams = {item.team for item in lineup_rows}
        if not lineup_rows or not ({"home", "away"}.issubset(covered_teams) or "neutral" in covered_teams):
            raise ValueError("LINEUP 預測必須連結可覆蓋雙方的官方先發來源")
    return tuple(sorted(rows, key=lambda row: (row["retrieved_at"], row["url"], row["title"])))


def data_snapshot_payload(
    model_input: dict[str, Any],
    source_manifest: tuple[dict[str, Any], ...] | list[dict[str, Any]],
) -> dict[str, Any]:
    """Return only the observed data/context, excluding model-family choices."""

    keys = (
        "home",
        "away",
        "league_home_goals_per_match",
        "league_away_goals_per_match",
        "data_as_of",
        "data_source",
        "forecast_horizon",
        "lineup_status",
    )
    return {
        "model_data": {key: model_input[key] for key in keys},
        "source_manifest": source_manifest,
    }


def football_feature_payload(model_input: dict[str, Any]) -> dict[str, Any]:
    """Return the pre-model football feature vector used in paired ablations."""

    return {
        "home": model_input["home"],
        "away": model_input["away"],
        "league_home_goals_per_match": model_input["league_home_goals_per_match"],
        "league_away_goals_per_match": model_input["league_away_goals_per_match"],
    }


def model_spec_payload(model_input: dict[str, Any], model_version: str) -> dict[str, Any]:
    return {
        "model_version": model_version,
        "score_model": model_input["score_model"],
        "dixon_coles_rho": model_input["dixon_coles_rho"],
        "rho_source": str(model_input["rho_source"]).strip(),
        "prior_match_equivalent": model_input["prior_match_equivalent"],
        "xg_weight": model_input["xg_weight"],
        "max_goals": model_input["max_goals"],
        "calibration_temperature": model_input["calibration_temperature"],
        "calibration_source": str(model_input["calibration_source"]).strip(),
        "lambda_bounds": [0.15, 4.5],
        "qimen_weight": 0.0,
    }


def _build_provenance(
    model_input: PrematchModelInput,
    qimen_features: dict[str, Any],
    source_manifest: tuple[dict[str, Any], ...],
    *,
    model_version: str,
    board: QimenBoard,
) -> dict[str, Any]:
    model_snapshot = model_input.to_dict()
    data_snapshot = data_snapshot_payload(model_snapshot, source_manifest)
    football_features = football_feature_payload(model_snapshot)
    model_spec = model_spec_payload(model_snapshot, model_version)
    return {
        "schema_version": PROVENANCE_VERSION,
        "code_version": CODE_VERSION,
        "git_commit": detect_git_commit(),
        "tzdb_version": board.calendar.tzdb_version,
        "source_manifest": source_manifest,
        "source_manifest_sha256": sha256_payload(source_manifest),
        "data_snapshot_sha256": sha256_payload(data_snapshot),
        "football_feature_sha256": sha256_payload(football_features),
        "qimen_feature_sha256": sha256_payload(qimen_features),
        "model_spec_sha256": sha256_payload(model_spec),
    }


def extract_qimen_features(board: QimenBoard, reading: FootballReading) -> dict[str, Any]:
    """Return deterministic, model-ready facts without assigning outcome weights."""

    def profile(prefix: str, item) -> dict[str, Any]:
        palace = board.palaces[item.palace]
        return {
            f"{prefix}_stem": item.stem,
            f"{prefix}_palace": item.palace,
            f"{prefix}_palace_element": palace.element,
            f"{prefix}_door": item.door,
            f"{prefix}_stars": list(item.stars),
            f"{prefix}_deity": item.deity,
            f"{prefix}_seasonal_state": item.seasonal_state,
            f"{prefix}_is_void": palace.is_void,
            f"{prefix}_is_horse": palace.is_horse,
            f"{prefix}_semantic_index": item.signal_index,
        }

    return {
        "feature_version": QIMEN_FEATURE_VERSION,
        "method_version": board.method.version,
        "seasonal_rule_version": reading.seasonal_rule_version,
        "dun": board.dun,
        "yuan": board.yuan,
        "ju": board.ju,
        "solar_term": board.calendar.solar_term,
        "month_branch": board.calendar.month_ganzhi[1],
        "day_stem": board.calendar.day_ganzhi[0],
        "hour_stem": board.calendar.hour_ganzhi[0],
        "chief_star": board.chief_star,
        "chief_star_palace": board.chief_star_palace,
        "chief_door": board.chief_door,
        "chief_door_palace": board.chief_door_palace,
        "horse_palace": board.horse_palace,
        "pattern_names": sorted({item.name for item in board.patterns}),
        **profile("home", reading.home),
        **profile("away", reading.away),
    }


def build_prediction(
    model_input: PrematchModelInput,
    board: QimenBoard,
    reading: FootballReading,
    *,
    match: MatchInput | None = None,
) -> PredictionResult:
    """Build an auditable score model and record Qimen features in shadow mode.

    Qimen features deliberately have zero influence in this version. They can only be
    promoted into the outcome model after chronological out-of-sample testing.
    """

    errors = model_input.validate()
    if errors:
        raise ValueError("；".join(errors))

    source_manifest = _source_manifest(match, model_input)

    home = model_input.home
    away = model_input.away
    home_sample_weight = home.effective_matches if home.effective_matches is not None else float(home.matches)
    away_sample_weight = away.effective_matches if away.effective_matches is not None else float(away.matches)
    league_team_mean = (
        model_input.league_home_goals_per_match
        + model_input.league_away_goals_per_match
    ) / 2
    home_attack_rate = _observed_rate(
        home.goals_for_per_match, home.xg_for_per_match, model_input.xg_weight
    )
    home_defence_rate = _observed_rate(
        home.goals_against_per_match, home.xg_against_per_match, model_input.xg_weight
    )
    away_attack_rate = _observed_rate(
        away.goals_for_per_match, away.xg_for_per_match, model_input.xg_weight
    )
    away_defence_rate = _observed_rate(
        away.goals_against_per_match, away.xg_against_per_match, model_input.xg_weight
    )

    home_attack = _shrunk_index(
        home_attack_rate, home_sample_weight, league_team_mean, model_input.prior_match_equivalent
    )
    home_defence_weakness = _shrunk_index(
        home_defence_rate, home_sample_weight, league_team_mean, model_input.prior_match_equivalent
    )
    away_attack = _shrunk_index(
        away_attack_rate, away_sample_weight, league_team_mean, model_input.prior_match_equivalent
    )
    away_defence_weakness = _shrunk_index(
        away_defence_rate, away_sample_weight, league_team_mean, model_input.prior_match_equivalent
    )

    raw_home_lambda = model_input.league_home_goals_per_match * home_attack * away_defence_weakness
    raw_away_lambda = model_input.league_away_goals_per_match * away_attack * home_defence_weakness
    home_lambda = min(4.5, max(0.15, raw_home_lambda))
    away_lambda = min(4.5, max(0.15, raw_away_lambda))

    home_goal_probs = _poisson_probabilities(home_lambda, model_input.max_goals)
    away_goal_probs = _poisson_probabilities(away_lambda, model_input.max_goals)
    raw_grid: list[tuple[int, int, float]] = []
    for home_goals, home_probability in enumerate(home_goal_probs):
        for away_goals, away_probability in enumerate(away_goal_probs):
            tau = 1.0
            if model_input.score_model == "DIXON_COLES":
                tau = dixon_coles_tau(
                    home_goals,
                    away_goals,
                    home_lambda,
                    away_lambda,
                    model_input.dixon_coles_rho,
                )
                if tau <= 0:
                    raise ValueError(
                        "Dixon–Coles rho 使低比分校正係數不為正；"
                        "請重新以盤前歷史訓練窗估計 rho"
                    )
            raw_grid.append((home_goals, away_goals, home_probability * away_probability * tau))

    grid_mass = sum(probability for _, _, probability in raw_grid)
    if not isfinite(grid_mass) or grid_mass <= 0:
        raise ValueError("比分矩陣總質量無效")
    grid = [
        ScoreProbability(home_goals, away_goals, probability / grid_mass)
        for home_goals, away_goals, probability in raw_grid
    ]

    raw_home_win = sum(item.probability for item in grid if item.home_goals > item.away_goals)
    raw_draw = sum(item.probability for item in grid if item.home_goals == item.away_goals)
    raw_away_win = sum(item.probability for item in grid if item.home_goals < item.away_goals)
    home_win, draw, away_win = (
        temperature_scale_probabilities(
            (raw_home_win, raw_draw, raw_away_win),
            model_input.calibration_temperature,
        )
        if model_input.calibration_source.strip()
        else (raw_home_win, raw_draw, raw_away_win)
    )
    outcomes = {"主勝": home_win, "和局": draw, "客勝": away_win}
    ordered_outcomes = sorted(outcomes.items(), key=lambda item: item[1], reverse=True)
    predicted_result = ordered_outcomes[0][0]
    decision_margin = ordered_outcomes[0][1] - ordered_outcomes[1][1]
    top_scorelines = tuple(sorted(grid, key=lambda item: item.probability, reverse=True)[:5])

    warnings: list[str] = []
    if home.matches < 5:
        warnings.append("主隊樣本少於 5 場，預測較依賴聯盟先驗。")
    if away.matches < 5:
        warnings.append("客隊樣本少於 5 場，預測較依賴聯盟先驗。")
    if home.effective_matches is not None and home.effective_matches < 5:
        warnings.append("主隊時間衰減後有效樣本權重少於 5 場，預測較依賴聯盟先驗。")
    if away.effective_matches is not None and away.effective_matches < 5:
        warnings.append("客隊時間衰減後有效樣本權重少於 5 場，預測較依賴聯盟先驗。")
    if home.xg_for_per_match is None or home.xg_against_per_match is None:
        warnings.append("主隊未提供完整 xG/xGA，僅以進失球估計部分攻防能力。")
    if away.xg_for_per_match is None or away.xg_against_per_match is None:
        warnings.append("客隊未提供完整 xG/xGA，僅以進失球估計部分攻防能力。")
    if raw_home_lambda != home_lambda or raw_away_lambda != away_lambda:
        warnings.append("至少一隊期望進球超出安全範圍，已截斷至 0.15–4.50。")
    if not source_manifest:
        warnings.append("未連結結構化來源清單；輸出可探索，但資料來源鏈仍不完整。")
    if model_input.score_model == "DIXON_COLES":
        warnings.append(
            "Dixon–Coles 是未通過盲測的 challenger；rho 只能由歷史訓練窗估計，"
            "不得依本場已知賽果調整。"
        )
    if model_input.calibration_source.strip():
        warnings.append(
            "1X2 已套用 calibration-only temperature artifact；比分候選仍是未校準的比分矩陣，"
            "兩者用途不可混為一談。"
        )
    warnings.append("奇門特徵目前只進入 shadow mode，不影響 1X2；須經盲測證明增量後才可啟用。")

    model_version = (
        DIXON_COLES_VERSION
        if model_input.score_model == "DIXON_COLES"
        else INDEPENDENT_POISSON_VERSION
    )
    sufficient_data = (
        home.matches >= 5
        and away.matches >= 5
        and home_sample_weight >= 5
        and away_sample_weight >= 5
    )
    if model_input.score_model == "DIXON_COLES":
        model_status = "CHALLENGER_UNVALIDATED" if sufficient_data else "CHALLENGER_LIMITED_DATA"
    else:
        model_status = "BASELINE_READY" if sufficient_data else "LIMITED_DATA"
    qimen_features = extract_qimen_features(board, reading)
    provenance = _build_provenance(
        model_input,
        qimen_features,
        source_manifest,
        model_version=model_version,
        board=board,
    )
    return PredictionResult(
        model_version=model_version,
        score_model=model_input.score_model,
        qimen_feature_version=QIMEN_FEATURE_VERSION,
        model_status=model_status,
        calibration_status=(
            "CALIBRATED_TEMPERATURE_V1"
            if model_input.calibration_source.strip()
            else "UNCALIBRATED_V0"
        ),
        qimen_mode="SHADOW_ONLY",
        forecast_horizon=model_input.forecast_horizon,
        lineup_status=model_input.lineup_status,
        calibration_source=model_input.calibration_source.strip(),
        expected_home_goals=home_lambda,
        expected_away_goals=away_lambda,
        raw_home_win_probability=raw_home_win,
        raw_draw_probability=raw_draw,
        raw_away_win_probability=raw_away_win,
        home_win_probability=home_win,
        draw_probability=draw,
        away_win_probability=away_win,
        predicted_result=predicted_result,
        decision_margin=decision_margin,
        top_scorelines=top_scorelines,
        score_grid_tail_mass=max(0.0, 1 - grid_mass),
        model_input=model_input.to_dict(),
        qimen_features=qimen_features,
        provenance=provenance,
        data_warnings=tuple(warnings),
        disclaimer=(
            "JARVIS 是尚待 untouched blind test 驗證的研究模型，不是投注建議。"
            "奇門特徵目前不改動機率；任何增量權重都必須由盤前鎖定資料與時間序列盲測取得。"
        ),
    )
