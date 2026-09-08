from __future__ import annotations

import sys
from unittest.mock import patch

import main


def _run_main(argv: list[str]) -> None:
    with patch.object(sys, "argv", ["main.py", *argv]), patch.object(main, "_configure_unicode_stdio"):
        main.main()


def test_cli_demo_defaults_to_memory_storage() -> None:
    with patch.object(main, "load_config") as load_config, patch.object(main, "create_repository"), patch.object(
        main, "MeterManager"
    ), patch.object(main, "run_cli_demo") as run_cli_demo:
        load_config.return_value.data = {
            "storage": {
                "backend": "sqlite",
                "database_path": "configured.db",
                "csv_backup_path": "backups",
            }
        }

        _run_main(["--cli"])

        run_cli_demo.assert_called_once_with(storage="memory", db_path=None, csv_path=None)


def test_cli_demo_uses_explicit_storage_selection() -> None:
    with patch.object(main, "load_config") as load_config, patch.object(main, "create_repository"), patch.object(
        main, "MeterManager"
    ), patch.object(main, "run_cli_demo") as run_cli_demo:
        load_config.return_value.data = {
            "storage": {
                "backend": "sqlite",
                "database_path": "configured.db",
                "csv_backup_path": "backups",
            }
        }

        _run_main(["--cli", "--storage", "sqlite", "--db-path", "demo.db"])

        run_cli_demo.assert_called_once_with(storage="sqlite", db_path="demo.db", csv_path=None)
