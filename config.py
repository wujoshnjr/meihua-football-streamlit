from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from version import APP_TITLE


@dataclass(frozen=True, slots=True)
class AppConfig:
    app_title: str = APP_TITLE
    data_dir: Path = Path("data")
    reports_dir: Path = Path("reports")
    knowledge_dir: Path = Path("knowledge")

    github_token: str = ""
    github_repo: str = ""
    github_branch: str = "main"
    github_cases_path: str = "data/meihua_cases.csv"
    github_reports_dir: str = "reports"

    github_models_token: str = ""
    ai_enabled: bool = False
    ai_provider: str = "github_models"
    ai_model: str = "openai/gpt-4.1-mini"
    ai_top_k_cases: int = 5
    ai_max_output_tokens: int = 1600
    ai_temperature: float = 0.2
    ai_require_confirmation: bool = True

    max_casebook_rows_for_ai: int = 500
    request_timeout_seconds: int = 45

    @property
    def use_github_backend(self) -> bool:
        return bool(self.github_token and self.github_repo)

    @property
    def use_ai(self) -> bool:
        return bool(self.ai_enabled and self.github_models_token)

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)


def _string(source: Mapping[str, Any], name: str, default: str = "") -> str:
    value = source.get(name, default)
    return str(value).strip() if value is not None else default


def _boolean(source: Mapping[str, Any], name: str, default: bool = False) -> bool:
    value = source.get(name, default)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on", "是", "啟用"}


def _integer(source: Mapping[str, Any], name: str, default: int) -> int:
    try:
        return int(source.get(name, default))
    except (TypeError, ValueError):
        return default


def _float(source: Mapping[str, Any], name: str, default: float) -> float:
    try:
        return float(source.get(name, default))
    except (TypeError, ValueError):
        return default


def load_config(secrets: Mapping[str, Any]) -> AppConfig:
    config = AppConfig(
        github_token=_string(secrets, "GITHUB_TOKEN"),
        github_repo=_string(secrets, "GITHUB_REPO"),
        github_branch=_string(secrets, "GITHUB_BRANCH", "main"),
        github_cases_path=_string(secrets, "GITHUB_CASES_PATH", "data/meihua_cases.csv"),
        github_reports_dir=_string(secrets, "GITHUB_REPORTS_DIR", "reports"),
        github_models_token=_string(secrets, "GITHUB_MODELS_TOKEN"),
        ai_enabled=_boolean(secrets, "AI_ENABLED", False),
        ai_provider=_string(secrets, "AI_PROVIDER", "github_models"),
        ai_model=_string(secrets, "AI_MODEL", "openai/gpt-4.1-mini"),
        ai_top_k_cases=max(1, min(10, _integer(secrets, "AI_TOP_K_CASES", 5))),
        ai_max_output_tokens=max(400, min(4000, _integer(secrets, "AI_MAX_OUTPUT_TOKENS", 1600))),
        ai_temperature=max(0.0, min(1.0, _float(secrets, "AI_TEMPERATURE", 0.2))),
        ai_require_confirmation=_boolean(secrets, "AI_REQUIRE_CONFIRMATION", True),
        max_casebook_rows_for_ai=max(50, min(5000, _integer(secrets, "MAX_CASEBOOK_ROWS_FOR_AI", 500))),
        request_timeout_seconds=max(10, min(120, _integer(secrets, "REQUEST_TIMEOUT_SECONDS", 45))),
    )
    config.ensure_dirs()
    return config
