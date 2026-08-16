from __future__ import annotations

import json
from pathlib import Path


def test_prediction_lock_schema_is_draft_2020_12_and_requires_audit_fields():
    path = Path(__file__).resolve().parents[1] / "schemas" / "prediction-lock.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    assert schema["$schema"].endswith("draft/2020-12/schema")
    required = set(schema["required"])
    assert {
        "match_id", "event_at", "locked_at", "data_as_of", "forecast_horizon",
        "dataset_role", "experiment_id", "model_version", "score_model",
        "prediction_payload", "fingerprint_sha256",
    }.issubset(required)
    assert required == set(schema["properties"])


def test_experiment_manifest_schema_requires_all_four_split_roles():
    path = Path(__file__).resolve().parents[1] / "schemas" / "experiment-manifest.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    roles = set(schema["properties"]["assignments"]["items"]["properties"]["dataset_role"]["enum"])
    assert roles == {"TRAIN", "VALIDATION", "CALIBRATION", "TEST_UNTOUCHED"}
    assert set(schema["properties"]["counts"]["required"]) == roles
