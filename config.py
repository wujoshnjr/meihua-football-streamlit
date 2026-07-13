from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from version import APP_TITLE


@dataclass(frozen=True, slots=True)
class AppConfig:
    app_title: str = APP_TITLE
    data_dir: Path = Path("data")
    reports_dir: Path = Path("casting_reports")
    knowledge_dir: Path = Path("knowledge")
    github_token: str = ""
    github_repo: str = ""
    github_branch: str = "main"
    github_castings_path: str = "data/meihua_castings.csv"
    github_reports_dir: str = "casting_reports"
    request_timeout_seconds: int = 45

    @property
    def use_github_backend(self) -> bool:
        return bool(self.github_token and self.github_repo)

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)


def _string(source: Mapping[str, Any], name: str, default: str = "") -> str:
    value = source.get(name, default)
    return str(value).strip() if value is not None else default


def _integer(source: Mapping[str, Any], name: str, default: int) -> int:
    try:
        return int(source.get(name, default))
    except (TypeError, ValueError):
        return default


def load_config(secrets: Mapping[str, Any]) -> AppConfig:
    config = AppConfig(
        github_token=_string(secrets, "GITHUB_TOKEN"),
        github_repo=_string(secrets, "GITHUB_REPO"),
        github_branch=_string(secrets, "GITHUB_BRANCH", "main"),
        github_castings_path=_string(secrets, "GITHUB_CASTINGS_PATH", "data/meihua_castings.csv"),
        github_reports_dir=_string(secrets, "GITHUB_REPORTS_DIR", "casting_reports"),
        request_timeout_seconds=max(10, min(120, _integer(secrets, "REQUEST_TIMEOUT_SECONDS", 45))),
    )
    config.ensure_dirs()
    return config
