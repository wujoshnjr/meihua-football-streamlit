from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

import pytest

from qimen.engine import cast_qimen
from qimen.evaluation import lock_prediction
from qimen.football import interpret_football
from qimen.prediction import PrematchModelInput, TeamForm, build_prediction
from qimen.protocol import EvidenceItem, MatchInput


def _board_and_reading(calendar_context):
    board = cast_qimen(
        calendar_context.local_datetime,
        calendar_context.timezone_name,
        calendar=calendar_context,
    )
    return board, interpret_football(board)


def _input(calendar_context, *, home_for: float = 1.35) -> PrematchModelInput:
    return PrematchModelInput(
        home=TeamForm(10, home_for, 1.35),
        away=TeamForm(10, 1.35, 1.35),
        league_home_goals_per_match=1.50,
        league_away_goals_per_match=1.20,
        data_as_of=calendar_context.local_datetime - timedelta(days=1),
        data_source="test-fixture",
    )


def test_average_teams_reproduce_league_home_advantage(calendar_context):
    board, reading = _board_and_reading(calendar_context)
    result = build_prediction(_input(calendar_context), board, reading)

    assert result.expected_home_goals == pytest.approx(1.50)
    assert result.expected_away_goals == pytest.approx(1.20)
    assert (
        result.home_win_probability
        + result.draw_probability
        + result.away_win_probability
    ) == pytest.approx(1.0)
    assert sum(item.probability for item in result.top_scorelines) < 1.0
    assert result.score_grid_tail_mass < 1e-5


def test_stronger_home_attack_increases_home_win_probability(calendar_context):
    board, reading = _board_and_reading(calendar_context)
    baseline = build_prediction(_input(calendar_context), board, reading)
    stronger = build_prediction(
        _input(calendar_context, home_for=3.0),
        board,
        reading,
    )
    assert stronger.expected_home_goals > baseline.expected_home_goals
    assert stronger.home_win_probability > baseline.home_win_probability


def test_qimen_is_recorded_but_has_zero_model_weight(calendar_context):
    board, reading = _board_and_reading(calendar_context)
    result = build_prediction(_input(calendar_context), board, reading)
    assert result.qimen_mode == "SHADOW_ONLY"
    assert result.qimen_features["home_seasonal_state"] == reading.home.seasonal_state
    assert result.model_input["data_as_of"].endswith("+08:00")
    assert any("不影響 1X2" in warning for warning in result.data_warnings)


def test_invalid_model_input_is_rejected(calendar_context):
    board, reading = _board_and_reading(calendar_context)
    invalid = PrematchModelInput(
        home=TeamForm(-1, 1.0, 1.0),
        away=TeamForm(5, 1.0, 1.0),
    )
    with pytest.raises(ValueError, match="樣本場次"):
        build_prediction(invalid, board, reading)


def test_dixon_coles_changes_only_registered_low_score_structure(calendar_context):
    board, reading = _board_and_reading(calendar_context)
    independent = build_prediction(_input(calendar_context), board, reading)
    challenger_input = replace(
        _input(calendar_context),
        score_model="DIXON_COLES",
        dixon_coles_rho=-0.08,
        rho_source="dc-rho-fit:" + "a" * 64,
    )
    challenger = build_prediction(challenger_input, board, reading)
    independent_scores = {
        (item.home_goals, item.away_goals): item.probability
        for item in independent.top_scorelines
    }
    challenger_scores = {
        (item.home_goals, item.away_goals): item.probability
        for item in challenger.top_scorelines
    }
    assert challenger.score_model == "DIXON_COLES"
    assert challenger.model_status == "CHALLENGER_UNVALIDATED"
    assert challenger_scores[(1, 1)] > independent_scores[(1, 1)]
    assert challenger.home_win_probability + challenger.draw_probability + challenger.away_win_probability == pytest.approx(1)
    assert challenger.provenance["data_snapshot_sha256"] == independent.provenance["data_snapshot_sha256"]
    assert challenger.provenance["football_feature_sha256"] == independent.provenance["football_feature_sha256"]
    assert challenger.provenance["model_spec_sha256"] != independent.provenance["model_spec_sha256"]


def test_dixon_coles_rejects_unfitted_or_nonpositive_correction(calendar_context):
    board, reading = _board_and_reading(calendar_context)
    no_source = PrematchModelInput(
        home=TeamForm(10, 1.5, 1.2),
        away=TeamForm(10, 1.2, 1.5),
        score_model="DIXON_COLES",
        dixon_coles_rho=-0.08,
    )
    with pytest.raises(ValueError, match="TRAIN artifact"):
        build_prediction(no_source, board, reading)

    invalid_tau = PrematchModelInput(
        home=TeamForm(100, 8.0, 8.0),
        away=TeamForm(100, 8.0, 8.0),
        league_home_goals_per_match=4.0,
        league_away_goals_per_match=4.0,
        score_model="DIXON_COLES",
        dixon_coles_rho=0.25,
        rho_source="dc-rho-fit:" + "b" * 64,
    )
    with pytest.raises(ValueError, match="校正係數不為正"):
        build_prediction(invalid_tau, board, reading)


def test_provenance_is_deterministic_and_feature_sensitive(calendar_context):
    board, reading = _board_and_reading(calendar_context)
    first = build_prediction(_input(calendar_context), board, reading)
    second = build_prediction(_input(calendar_context), board, reading)
    changed = build_prediction(_input(calendar_context, home_for=2.1), board, reading)
    assert first.provenance == second.provenance
    assert first.provenance["data_snapshot_sha256"] != changed.provenance["data_snapshot_sha256"]
    assert first.provenance["football_feature_sha256"] != changed.provenance["football_feature_sha256"]
    assert first.provenance["qimen_feature_sha256"] == changed.provenance["qimen_feature_sha256"]


def test_evidence_retrieved_after_data_cutoff_is_rejected(calendar_context):
    board, reading = _board_and_reading(calendar_context)
    cutoff = calendar_context.local_datetime - timedelta(days=1)
    evidence = EvidenceItem(
        "team form", "https://example.test/form",
        cutoff - timedelta(hours=1), cutoff + timedelta(minutes=1), "team_form",
    )
    match = MatchInput(
        "SOURCE-CHAIN", "Home", "Away", "League",
        calendar_context.local_datetime, calendar_context.timezone_name,
        "Stadium", "Taipei", evidence=[evidence],
    )
    with pytest.raises(ValueError, match="擷取時間晚於統計資料截至時間"):
        build_prediction(_input(calendar_context), board, reading, match=match)


def test_lineup_horizon_requires_and_accepts_both_official_sources(calendar_context):
    board, reading = _board_and_reading(calendar_context)
    event = calendar_context.local_datetime
    evidence = [
        EvidenceItem(
            f"{team} official lineup", f"https://example.test/{team}",
            event - timedelta(minutes=70), event - timedelta(minutes=60),
            "official_lineup", team=team, material_update=True, reliability="高",
        )
        for team in ("home", "away")
    ]
    match = MatchInput(
        "LINEUP-LOCK", "Home", "Away", "League", event,
        calendar_context.timezone_name, "Stadium", "Taipei", evidence=evidence,
        both_teams_refreshed_after_material_update=True,
    )
    model_input = replace(
        _input(calendar_context),
        data_as_of=event - timedelta(minutes=45),
        forecast_horizon="LINEUP",
        lineup_status="OFFICIAL_BOTH",
    )
    prediction = build_prediction(model_input, board, reading, match=match)
    locked = lock_prediction(
        match.match_id, event, event - timedelta(minutes=40), prediction,
        competition=match.competition, evaluation_block="2026-W02",
    )
    assert locked.forecast_horizon == "LINEUP"
    assert len(prediction.provenance["source_manifest"]) == 2


def test_temperature_artifact_calibrates_1x2_but_not_score_grid(calendar_context):
    board, reading = _board_and_reading(calendar_context)
    raw = build_prediction(_input(calendar_context), board, reading)
    calibrated = build_prediction(
        replace(
            _input(calendar_context),
            calibration_temperature=1.8,
            calibration_source="temperature-fit:" + "c" * 64,
        ),
        board,
        reading,
    )
    assert calibrated.calibration_status == "CALIBRATED_TEMPERATURE_V1"
    assert calibrated.calibration_source.startswith("temperature-fit:")
    assert calibrated.home_win_probability + calibrated.draw_probability + calibrated.away_win_probability == pytest.approx(1)
    assert calibrated.raw_home_win_probability == pytest.approx(raw.home_win_probability)
    assert calibrated.top_scorelines == raw.top_scorelines
    assert calibrated.home_win_probability != pytest.approx(raw.home_win_probability)
    assert calibrated.provenance["data_snapshot_sha256"] == raw.provenance["data_snapshot_sha256"]
    assert calibrated.provenance["model_spec_sha256"] != raw.provenance["model_spec_sha256"]


def test_calibration_temperature_cannot_be_entered_without_artifact(calendar_context):
    board, reading = _board_and_reading(calendar_context)
    with pytest.raises(ValueError, match="CALIBRATION artifact"):
        build_prediction(
            replace(_input(calendar_context), calibration_temperature=1.2),
            board,
            reading,
        )


def test_time_decayed_effective_matches_control_shrinkage(calendar_context):
    board, reading = _board_and_reading(calendar_context)
    full_weight = build_prediction(
        replace(
            _input(calendar_context, home_for=3.0),
            home=TeamForm(20, 3.0, 1.35, effective_matches=20.0),
        ),
        board,
        reading,
    )
    low_effective_weight = build_prediction(
        replace(
            _input(calendar_context, home_for=3.0),
            home=TeamForm(20, 3.0, 1.35, effective_matches=2.0),
        ),
        board,
        reading,
    )
    assert low_effective_weight.expected_home_goals < full_weight.expected_home_goals
    assert low_effective_weight.model_status == "LIMITED_DATA"
