from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from jarvis.provenance import sha256_payload
from meihua.engine import MeihuaSnapshot, build_meihua_snapshot
from meihua.outcome_features import (
    MEIHUA_OUTCOME_DESIGN_VERSION,
    meihua_outcome_numeric_features,
)
from qimen.engine import cast_qimen
from qimen.features import PrematchFeatureSnapshot
from qimen.football import interpret_football
from qimen.outcome_design import QIMEN_OUTCOME_DESIGN_VERSION, qimen_outcome_numeric_features
from qimen.outcome_features import QimenOutcomeFeatureSnapshot, build_qimen_outcome_feature_snapshot

from .experiment import PrematchExperimentRecord, SnapshotRef


MULTISIGNAL_DATASET_VERSION = "jarvis-multisignal-dataset-v0.1.0"
DatasetRole = Literal["TRAIN", "VALIDATION", "CALIBRATION", "TEST_UNTOUCHED"]
VenueMode = Literal["TRUE_HOME", "NEUTRAL"]


@dataclass(frozen=True)
class HistoricalFixture:
    match_id: str
    competition: str
    event_at: datetime
    timezone_name: str
    home_team_id: str
    away_team_id: str
    schedule_available_at: datetime
    venue_mode: VenueMode
    dataset_role: DatasetRole
    evaluation_block: str
    experiment_id: str
    actual_home_goals: int
    actual_away_goals: int

    def validate(self, *, cutoff: datetime) -> list[str]:
        errors: list[str] = []
        if not self.match_id.strip() or not self.competition.strip():
            errors.append("HistoricalFixture 必須有 match_id 與 competition")
        if not self.home_team_id.strip() or not self.away_team_id.strip():
            errors.append(f"{self.match_id} 的主客隊 ID 不可空白")
        if self.home_team_id == self.away_team_id:
            errors.append(f"{self.match_id} 的主客隊不可相同")
        if self.event_at.tzinfo is None or self.schedule_available_at.tzinfo is None or cutoff.tzinfo is None:
            errors.append(f"{self.match_id} 的 event/schedule/cutoff 時間必須含時區")
        else:
            if cutoff >= self.event_at:
                errors.append(f"{self.match_id} cutoff 必須早於 event_at")
            if self.schedule_available_at > cutoff:
                errors.append(f"{self.match_id} schedule 在 cutoff 後才可得")
        if not self.timezone_name.strip():
            errors.append(f"{self.match_id} timezone_name 不可空白")
        if self.venue_mode not in {"TRUE_HOME", "NEUTRAL"}:
            errors.append(f"{self.match_id} venue_mode 無效")
        if self.dataset_role not in {"TRAIN", "VALIDATION", "CALIBRATION", "TEST_UNTOUCHED"}:
            errors.append(f"{self.match_id} dataset_role 無效")
        if not self.evaluation_block.strip() or not self.experiment_id.strip():
            errors.append(f"{self.match_id} evaluation_block/experiment_id 不可空白")
        for label, value in (
            ("actual_home_goals", self.actual_home_goals),
            ("actual_away_goals", self.actual_away_goals),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                errors.append(f"{self.match_id} 的 {label} 必須為非負整數")
        return errors


@dataclass(frozen=True)
class MultiSignalDatasetRow:
    schema_version: str
    record: PrematchExperimentRecord
    football_snapshot_fingerprint: str
    football_model_input: dict[str, Any]
    qimen_snapshot: QimenOutcomeFeatureSnapshot
    qimen_numeric_features: dict[str, float]
    meihua_snapshot: MeihuaSnapshot
    meihua_numeric_features: dict[str, float]
    fingerprint_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "record": self.record.to_dict(),
            "record_fingerprint_sha256": self.record.fingerprint_sha256,
            "football_snapshot_fingerprint": self.football_snapshot_fingerprint,
            "football_model_input": self.football_model_input,
            "qimen_snapshot": self.qimen_snapshot.to_dict(),
            "qimen_numeric_features": dict(sorted(self.qimen_numeric_features.items())),
            "meihua_snapshot": self.meihua_snapshot.to_dict(),
            "meihua_numeric_features": dict(sorted(self.meihua_numeric_features.items())),
            "fingerprint_sha256": self.fingerprint_sha256,
        }


def build_multisignal_dataset_row(
    fixture: HistoricalFixture,
    football_snapshot: PrematchFeatureSnapshot,
) -> MultiSignalDatasetRow:
    """Build one deterministic Football/Qimen/Meihua historical research row."""

    cutoff = football_snapshot.cutoff_at
    errors = fixture.validate(cutoff=cutoff)
    if football_snapshot.competition != fixture.competition:
        errors.append(f"{fixture.match_id} football competition 與 fixture 不一致")
    if football_snapshot.home.team_id != fixture.home_team_id:
        errors.append(f"{fixture.match_id} football home_team_id 與 fixture 不一致")
    if football_snapshot.away.team_id != fixture.away_team_id:
        errors.append(f"{fixture.match_id} football away_team_id 與 fixture 不一致")
    if errors:
        raise ValueError("；".join(errors))

    board = cast_qimen(fixture.event_at, fixture.timezone_name)
    reading = interpret_football(board)
    qimen_snapshot = build_qimen_outcome_feature_snapshot(board, reading)
    qimen_features = qimen_outcome_numeric_features(qimen_snapshot)

    meihua_snapshot = build_meihua_snapshot(fixture.event_at, fixture.timezone_name)
    meihua_features = meihua_outcome_numeric_features(meihua_snapshot)

    football_payload = football_snapshot.to_dict()
    football_payload_hash = sha256_payload(football_payload)
    qimen_payload = qimen_snapshot.to_dict()
    meihua_payload = meihua_snapshot.to_dict()
    record = PrematchExperimentRecord(
        match_id=fixture.match_id,
        competition=fixture.competition,
        event_at=fixture.event_at,
        cutoff=cutoff,
        venue_mode=fixture.venue_mode,
        dataset_role=fixture.dataset_role,
        evaluation_block=fixture.evaluation_block,
        experiment_id=fixture.experiment_id,
        football_snapshot=SnapshotRef(
            source=football_snapshot.data_source,
            schema_version=football_snapshot.schema_version,
            available_at=cutoff,
            payload_sha256=football_payload_hash,
        ),
        qimen_snapshot=SnapshotRef(
            source=f"qimen:{QIMEN_OUTCOME_DESIGN_VERSION}",
            schema_version=QIMEN_OUTCOME_DESIGN_VERSION,
            available_at=fixture.schedule_available_at,
            payload_sha256=sha256_payload(qimen_payload),
        ),
        meihua_snapshot=SnapshotRef(
            source=f"meihua:{MEIHUA_OUTCOME_DESIGN_VERSION}",
            schema_version=MEIHUA_OUTCOME_DESIGN_VERSION,
            available_at=fixture.schedule_available_at,
            payload_sha256=sha256_payload(meihua_payload),
        ),
        actual_home_goals=fixture.actual_home_goals,
        actual_away_goals=fixture.actual_away_goals,
    )
    record_errors = record.validate()
    if record_errors:
        raise ValueError("；".join(record_errors))

    model_input = football_snapshot.to_model_input().to_dict()
    core = {
        "schema_version": MULTISIGNAL_DATASET_VERSION,
        "record_fingerprint_sha256": record.fingerprint_sha256,
        "football_snapshot_fingerprint": football_snapshot.fingerprint_sha256,
        "football_model_input": model_input,
        "qimen_snapshot": qimen_payload,
        "qimen_numeric_features": dict(sorted(qimen_features.items())),
        "meihua_snapshot": meihua_payload,
        "meihua_numeric_features": dict(sorted(meihua_features.items())),
    }
    return MultiSignalDatasetRow(
        schema_version=MULTISIGNAL_DATASET_VERSION,
        record=record,
        football_snapshot_fingerprint=football_snapshot.fingerprint_sha256,
        football_model_input=model_input,
        qimen_snapshot=qimen_snapshot,
        qimen_numeric_features=qimen_features,
        meihua_snapshot=meihua_snapshot,
        meihua_numeric_features=meihua_features,
        fingerprint_sha256=sha256_payload(core),
    )
