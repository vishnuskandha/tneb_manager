from __future__ import annotations

import os
import tempfile
from datetime import date

from models import MeterManager
from data.repository import create_repository


def _sample_seed(manager: MeterManager) -> None:
    today = date.today()
    prior = date(today.year, today.month, max(1, today.day - 10))
    manager.add_reading("R", prior, 0)
    manager.add_reading("Y", prior, 0)
    manager.add_reading("B", prior, 0)
    manager.add_reading("R", today, 100)
    manager.add_reading("Y", today, 150)
    manager.add_reading("B", today, 200)


def test_sqlite_crud_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "tneb.db")
        with create_repository("sqlite", db_path=db_path) as repo:
            manager = MeterManager(repository=repo)
            _sample_seed(manager)

            latest = manager.get_latest_readings()
            assert latest["R"] is not None and latest["R"].current_reading == 100
            assert latest["Y"] is not None and latest["Y"].current_reading == 150
            assert latest["B"] is not None and latest["B"].current_reading == 200

            history = manager.get_readings_history()
            assert len(history) == 6


def test_csv_repository_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        csv_path = os.path.join(tmp, "readings.csv")
        repo = create_repository("csv", csv_path=csv_path)
        manager = MeterManager(repository=repo)
        _sample_seed(manager)

        assert os.path.exists(csv_path)
        history = manager.get_readings_history()
        assert len(history) == 6


def test_backup_and_restore_between_backends():
    with tempfile.TemporaryDirectory() as tmp:
        # Seed SQLite
        db_path = os.path.join(tmp, "tneb.db")
        with create_repository("sqlite", db_path=db_path) as sqlite_repo:
            manager = MeterManager(repository=sqlite_repo)
            _sample_seed(manager)

            # Backup
            backup_path = os.path.join(tmp, "backup.csv")
            manager.create_backup(backup_path)
            assert os.path.exists(backup_path)

            # Restore into CSV repository
            csv_path = os.path.join(tmp, "restored.csv")
            csv_repo = create_repository("csv", csv_path=csv_path)
            manager.switch_storage_backend(csv_repo)
            restored = manager.restore_from_backup(backup_path)
            assert restored == 6
            history = manager.get_readings_history()
            assert len(history) == 6


