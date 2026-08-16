from __future__ import annotations

import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qimen.training import (  # noqa: E402
    CalibrationObservation,
    ChronologicalSample,
    DixonColesObservation,
    build_chronological_split_manifest,
    fit_dixon_coles_rho,
    fit_temperature_scaler,
)
from qimen.features import HistoricalMatch, build_prematch_feature_snapshot  # noqa: E402


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _aware_datetime(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} 必須為 ISO 8601") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label} 必須含時區")
    return parsed


def _write_artifact(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _split(args: argparse.Namespace) -> dict[str, object]:
    samples = [
        ChronologicalSample(
            row["match_id"],
            _aware_datetime(row["event_at"], f"{row['match_id']} event_at"),
            row["competition"],
            row["evaluation_block"],
            row["payload_sha256"],
        )
        for row in _read_rows(args.input)
    ]
    return build_chronological_split_manifest(
        samples,
        experiment_id=args.experiment_id,
        train_end=_aware_datetime(args.train_end, "train_end"),
        validation_end=_aware_datetime(args.validation_end, "validation_end"),
        calibration_end=_aware_datetime(args.calibration_end, "calibration_end"),
    ).to_dict()


def _rho(args: argparse.Namespace) -> dict[str, object]:
    observations = [
        DixonColesObservation(
            row["match_id"],
            _aware_datetime(row["event_at"], f"{row['match_id']} event_at"),
            float(row["expected_home_goals"]),
            float(row["expected_away_goals"]),
            int(row["actual_home_goals"]),
            int(row["actual_away_goals"]),
            row["payload_sha256"],
            row["dataset_role"],
        )
        for row in _read_rows(args.input)
    ]
    return fit_dixon_coles_rho(
        observations,
        half_life_days=args.half_life_days,
    ).to_dict()


def _temperature(args: argparse.Namespace) -> dict[str, object]:
    observations = [
        CalibrationObservation(
            row["match_id"],
            _aware_datetime(row["event_at"], f"{row['match_id']} event_at"),
            (float(row["p_home"]), float(row["p_draw"]), float(row["p_away"])),
            row["actual_result"],
            row["model_spec_sha256"],
            row["payload_sha256"],
            row["dataset_role"],
        )
        for row in _read_rows(args.input)
    ]
    return fit_temperature_scaler(observations).to_dict()


def _optional_float(value: str) -> float | None:
    return float(value) if value.strip() else None


def _features(args: argparse.Namespace) -> dict[str, object]:
    matches = [
        HistoricalMatch(
            row["match_id"],
            row["competition"],
            _aware_datetime(row["event_at"], f"{row['match_id']} event_at"),
            row["home_team_id"],
            row["away_team_id"],
            int(row["home_goals"]),
            int(row["away_goals"]),
            row["source_payload_sha256"],
            _optional_float(row.get("home_xg", "")),
            _optional_float(row.get("away_xg", "")),
            _aware_datetime(row["available_at"], f"{row['match_id']} available_at"),
        )
        for row in _read_rows(args.input)
    ]
    return build_prematch_feature_snapshot(
        matches,
        competition=args.competition,
        home_team_id=args.home_team_id,
        away_team_id=args.away_team_id,
        cutoff_at=_aware_datetime(args.cutoff, "cutoff"),
        half_life_days=args.half_life_days,
        maximum_team_matches=args.maximum_team_matches,
        minimum_league_matches=args.minimum_league_matches,
    ).to_dict()


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Fit immutable JARVIS training artifacts")
    subcommands = root.add_subparsers(dest="command", required=True)

    split = subcommands.add_parser("split", help="build four-layer chronological manifest")
    split.add_argument("--input", type=Path, required=True)
    split.add_argument("--output", type=Path, required=True)
    split.add_argument("--experiment-id", required=True)
    split.add_argument("--train-end", required=True)
    split.add_argument("--validation-end", required=True)
    split.add_argument("--calibration-end", required=True)
    split.set_defaults(handler=_split)

    rho = subcommands.add_parser("fit-rho", help="fit Dixon-Coles rho on TRAIN only")
    rho.add_argument("--input", type=Path, required=True)
    rho.add_argument("--output", type=Path, required=True)
    rho.add_argument("--half-life-days", type=float, default=365.0)
    rho.set_defaults(handler=_rho)

    temperature = subcommands.add_parser(
        "fit-temperature",
        help="fit temperature scaling on CALIBRATION only",
    )
    temperature.add_argument("--input", type=Path, required=True)
    temperature.add_argument("--output", type=Path, required=True)
    temperature.set_defaults(handler=_temperature)

    features = subcommands.add_parser(
        "build-features",
        help="build one cutoff-only time-decayed TeamForm snapshot",
    )
    features.add_argument("--input", type=Path, required=True)
    features.add_argument("--output", type=Path, required=True)
    features.add_argument("--competition", required=True)
    features.add_argument("--home-team-id", required=True)
    features.add_argument("--away-team-id", required=True)
    features.add_argument("--cutoff", required=True)
    features.add_argument("--half-life-days", type=float, default=180.0)
    features.add_argument("--maximum-team-matches", type=int, default=20)
    features.add_argument("--minimum-league-matches", type=int, default=50)
    features.set_defaults(handler=_features)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        payload = args.handler(args)
        _write_artifact(args.output, payload)
    except (KeyError, TypeError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"OK: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
