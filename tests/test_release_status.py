from pathlib import Path

from jarvis.release import RELEASE_STATUS_SCHEMA_VERSION, runtime_release_status
from qimen.prediction import CODE_VERSION, INDEPENDENT_POISSON_VERSION
from version import __version__


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_release_status_binds_web_and_live_versions():
    release = runtime_release_status()

    assert release.schema_version == RELEASE_STATUS_SCHEMA_VERSION
    assert release.web_app_version == __version__
    assert release.research_generation == "JARVIS_V8"
    assert release.live_predictor_code_version == CODE_VERSION
    assert release.live_predictor_model_version == INDEPENDENT_POISSON_VERSION
    assert release.live_predictor_family == "FOOTBALL_BASELINE"
    assert release.promotion_policy == "FROZEN_CHRONOLOGICAL_ARTIFACT_REQUIRED"
    assert release.automatic_promotion is False


def test_readme_matches_runtime_release_status():
    release = runtime_release_status()
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert f"Web App v{release.web_app_version}" in readme
    assert f"Live Predictor v{release.live_predictor_code_version}" in readme
    assert "Production app 版本仍為 `7.2.0`" not in readme
