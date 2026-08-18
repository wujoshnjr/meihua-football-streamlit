from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from qimen.prediction import CODE_VERSION as LIVE_PREDICTOR_CODE_VERSION
from qimen.prediction import INDEPENDENT_POISSON_VERSION
from version import __version__


RELEASE_STATUS_SCHEMA_VERSION = "jarvis-runtime-release-status-v1.0.0"


@dataclass(frozen=True)
class RuntimeReleaseStatus:
    """Single source of truth for deployed UI vs live predictor vs research stack.

    The Streamlit application can move to a new web release without implying that
    an unvalidated research challenger has replaced the frozen live predictor.
    """

    schema_version: str
    web_app_version: str
    research_generation: str
    live_predictor_code_version: str
    live_predictor_model_version: str
    live_predictor_family: str
    live_predictor_mode: str
    promotion_policy: str
    automatic_promotion: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


RUNTIME_RELEASE_STATUS = RuntimeReleaseStatus(
    schema_version=RELEASE_STATUS_SCHEMA_VERSION,
    web_app_version=__version__,
    research_generation="JARVIS_V8",
    live_predictor_code_version=LIVE_PREDICTOR_CODE_VERSION,
    live_predictor_model_version=INDEPENDENT_POISSON_VERSION,
    live_predictor_family="FOOTBALL_BASELINE",
    live_predictor_mode="FROZEN_CHAMPION_COMPATIBILITY_PATH",
    promotion_policy="FROZEN_CHRONOLOGICAL_ARTIFACT_REQUIRED",
    automatic_promotion=False,
)


def runtime_release_status() -> RuntimeReleaseStatus:
    return RUNTIME_RELEASE_STATUS
