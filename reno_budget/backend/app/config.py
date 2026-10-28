"""Runtime configuration: data paths, dev mode and the app options set in Home Assistant."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

INGRESS_IP = "172.30.32.2"

_LOG_LEVELS = {
    "trace": logging.DEBUG,
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "notice": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "fatal": logging.CRITICAL,
}


@dataclass(frozen=True)
class Options:
    log_level: str = "info"
    auto_backup: bool = True
    backup_keep: int = 14

    @property
    def python_log_level(self) -> int:
        return _LOG_LEVELS.get(self.log_level, logging.INFO)


@dataclass(frozen=True)
class AppConfig:
    data_dir: Path
    static_dir: Path
    dev_mode: bool

    @classmethod
    def from_env(cls) -> AppConfig:
        default_static = Path(__file__).resolve().parent.parent / "static"
        return cls(
            data_dir=Path(os.environ.get("RENO_DATA_DIR", "/data")),
            static_dir=Path(os.environ.get("RENO_STATIC_DIR", default_static)),
            dev_mode=os.environ.get("RENO_DEV") == "1",
        )

    @property
    def db_path(self) -> Path:
        return self.data_dir / "reno.db"

    @property
    def db_url(self) -> str:
        return f"sqlite:///{self.db_path}"

    @property
    def attachments_dir(self) -> Path:
        return self.data_dir / "attachments"

    @property
    def backups_dir(self) -> Path:
        return self.data_dir / "backups"

    def ensure_dirs(self) -> None:
        for path in (self.data_dir, self.attachments_dir, self.backups_dir):
            path.mkdir(parents=True, exist_ok=True)

    def load_options(self) -> Options:
        options_file = self.data_dir / "options.json"
        if not options_file.exists():
            return Options()
        raw = json.loads(options_file.read_text())
        defaults = Options()
        return Options(
            log_level=str(raw.get("log_level", defaults.log_level)),
            auto_backup=bool(raw.get("auto_backup", defaults.auto_backup)),
            backup_keep=int(raw.get("backup_keep", defaults.backup_keep)),
        )


_config = AppConfig.from_env()


def get_config() -> AppConfig:
    return _config


def set_config(new: AppConfig) -> None:
    """Swap the global config (used by tests and dev tooling)."""
    global _config
    _config = new
