from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional


DEFAULT_CONFIG: Dict[str, Any] = {
    "storage": {
        "backend": "sqlite",
        "database_path": "data/tneb_readings.db",
        "csv_backup_path": "data/backups/",
        "auto_save": True,
        "backup_enabled": True,
        "backup_frequency": "daily",
    },
    "application": {
        "rotation_threshold": 350.0,
        "date_format": "%d/%m/%Y",
    },
}


@dataclass
class AppConfig:
    data: Dict[str, Any]

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    # Storage helpers
    def get_database_path(self) -> str:
        path = self.data["storage"]["database_path"]
        return os.path.normpath(path)

    def get_backup_directory(self) -> str:
        path = self.data["storage"]["csv_backup_path"]
        return os.path.normpath(path)

    def create_directories(self) -> None:
        os.makedirs(os.path.dirname(self.get_database_path()) or ".", exist_ok=True)
        os.makedirs(self.get_backup_directory(), exist_ok=True)

    # Flags
    @property
    def auto_save(self) -> bool:
        return bool(self.data["storage"].get("auto_save", True))

    @property
    def backup_enabled(self) -> bool:
        return bool(self.data["storage"].get("backup_enabled", True))


def _merge_env(config: Dict[str, Any]) -> Dict[str, Any]:
    # Allow environment overrides
    backend = os.getenv("TNEB_STORAGE_BACKEND")
    if backend:
        config["storage"]["backend"] = backend
    db_path = os.getenv("TNEB_DB_PATH")
    if db_path:
        config["storage"]["database_path"] = db_path
    backup_path = os.getenv("TNEB_CSV_BACKUP_PATH")
    if backup_path:
        config["storage"]["csv_backup_path"] = backup_path
    return config


def load_config(config_file: Optional[str] = None) -> AppConfig:
    cfg = dict(DEFAULT_CONFIG)
    if config_file and os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                file_cfg = json.load(f)
                # shallow merge
                for k, v in file_cfg.items():
                    if isinstance(v, dict) and k in cfg:
                        cfg[k].update(v)
                    else:
                        cfg[k] = v
        except Exception:
            pass
    cfg = _merge_env(cfg)
    app_cfg = AppConfig(cfg)
    app_cfg.create_directories()
    return app_cfg


def save_config(config: AppConfig, config_file: Optional[str] = None) -> None:
    target = config_file or "data/config.json"
    os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(config.data, f, indent=2)


