from __future__ import annotations

from abc import ABC, abstractmethod
import os
from typing import Any, Dict, List, Optional, Tuple

from models.meter_reading import MeterReading
from .database_manager import DatabaseManager, DatabaseError
from .csv_manager import CSVManager, CSVError


class DataRepository(ABC):
    @abstractmethod
    def save_reading(self, meter_reading: MeterReading) -> int:  # returns id
        raise NotImplementedError

    @abstractmethod
    def get_reading_by_id(self, reading_id: int) -> Optional[MeterReading]:
        raise NotImplementedError

    @abstractmethod
    def get_readings_by_meter(self, meter_id: str, limit: Optional[int] = None) -> List[MeterReading]:
        raise NotImplementedError

    @abstractmethod
    def get_latest_reading_by_meter(self, meter_id: str) -> Optional[MeterReading]:
        raise NotImplementedError

    @abstractmethod
    def get_all_readings(self) -> List[MeterReading]:
        raise NotImplementedError

    @abstractmethod
    def get_readings_by_date_range(self, start_date: str, end_date: str) -> List[MeterReading]:
        raise NotImplementedError

    @abstractmethod
    def delete_reading(self, reading_id: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def backup_data(self, backup_path: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def restore_data(self, backup_path: str) -> int:
        raise NotImplementedError


class SQLiteRepository(DataRepository):
    def __init__(self, db_path: str) -> None:
        self.db = DatabaseManager(db_path)

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> "SQLiteRepository":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def save_reading(self, meter_reading: MeterReading) -> int:
        return self.db.insert_reading(meter_reading)

    def get_reading_by_id(self, reading_id: int) -> Optional[MeterReading]:
        rows = self.db.conn.execute("SELECT * FROM meter_readings WHERE id=?", (reading_id,)).fetchall()
        if not rows:
            return None
        return self.db._row_to_reading(rows[0])

    def get_readings_by_meter(self, meter_id: str, limit: Optional[int] = None) -> List[MeterReading]:
        return [r for _id, r in self.db.get_readings_by_meter(meter_id, limit=limit)]

    def get_latest_reading_by_meter(self, meter_id: str) -> Optional[MeterReading]:
        row = self.db.get_latest_reading_by_meter(meter_id)
        return None if row is None else row[1]

    def get_all_readings(self) -> List[MeterReading]:
        return [r for _id, r in self.db.get_all_readings()]

    def get_readings_by_date_range(self, start_date: str, end_date: str) -> List[MeterReading]:
        return [r for _id, r in self.db.get_readings_by_date_range(start_date, end_date)]

    def delete_reading(self, reading_id: int) -> None:
        self.db.delete_reading(reading_id)

    def backup_data(self, backup_path: str) -> None:
        self.db.backup_to_csv(backup_path)

    def restore_data(self, backup_path: str) -> int:
        return self.db.restore_from_csv(backup_path)


class CSVRepository(DataRepository):
    def __init__(self, csv_path: str) -> None:
        self.csv = CSVManager(csv_path)

    def save_reading(self, meter_reading: MeterReading) -> int:
        # CSV rows don't have stable IDs; return -1 as placeholder
        self.csv.append_reading(meter_reading)
        return -1

    def get_reading_by_id(self, reading_id: int) -> Optional[MeterReading]:  # Not applicable for CSV
        return None

    def get_readings_by_meter(self, meter_id: str, limit: Optional[int] = None) -> List[MeterReading]:
        rows = self.csv.get_readings_by_meter(meter_id)
        # Ensure results are sorted by reading_date ascending for consistent semantics
        rows.sort(key=lambda r: r.reading_date)
        return rows if limit is None else rows[: int(limit)]

    def get_latest_reading_by_meter(self, meter_id: str) -> Optional[MeterReading]:
        rows = self.csv.get_readings_by_meter(meter_id)
        if not rows:
            return None
        # Select latest by reading_date
        return max(rows, key=lambda r: r.reading_date)

    def get_all_readings(self) -> List[MeterReading]:
        return self.csv.load_readings()

    def get_readings_by_date_range(self, start_date: str, end_date: str) -> List[MeterReading]:
        # Normalize to ISO strings if dates provided as date/datetime
        try:
            start_iso = getattr(start_date, "isoformat", lambda: str(start_date))()
        except Exception:
            start_iso = str(start_date)
        try:
            end_iso = getattr(end_date, "isoformat", lambda: str(end_date))()
        except Exception:
            end_iso = str(end_date)
        all_rows = self.csv.load_readings()
        return [r for r in all_rows if start_iso <= r.reading_date.isoformat() <= end_iso]

    def delete_reading(self, reading_id: int) -> None:  # Not supported for CSV
        raise CSVError("Delete by ID is not supported for CSV repository")

    def backup_data(self, backup_path: str) -> None:
        # Copy current CSV to backup_path
        readings = self.csv.load_readings()
        CSVManager(backup_path).save_readings(readings)

    def restore_data(self, backup_path: str) -> int:
        readings = CSVManager(backup_path).load_readings()
        self.csv.save_readings(readings)
        return len(readings)


class MemoryRepository(DataRepository):
    def __init__(self) -> None:
        self._rows: List[MeterReading] = []

    def save_reading(self, meter_reading: MeterReading) -> int:
        self._rows.append(meter_reading)
        return len(self._rows)

    def get_reading_by_id(self, reading_id: int) -> Optional[MeterReading]:
        idx = reading_id - 1
        if 0 <= idx < len(self._rows):
            return self._rows[idx]
        return None

    def get_readings_by_meter(self, meter_id: str, limit: Optional[int] = None) -> List[MeterReading]:
        rows = [r for r in self._rows if r.meter_id == meter_id]
        return rows if limit is None else rows[: int(limit)]

    def get_latest_reading_by_meter(self, meter_id: str) -> Optional[MeterReading]:
        rows = [r for r in self._rows if r.meter_id == meter_id]
        return rows[-1] if rows else None

    def get_all_readings(self) -> List[MeterReading]:
        return list(self._rows)

    def get_readings_by_date_range(self, start_date: str, end_date: str) -> List[MeterReading]:
        try:
            start_iso = getattr(start_date, "isoformat", lambda: str(start_date))()
        except Exception:
            start_iso = str(start_date)
        try:
            end_iso = getattr(end_date, "isoformat", lambda: str(end_date))()
        except Exception:
            end_iso = str(end_date)
        return [r for r in self._rows if start_iso <= r.reading_date.isoformat() <= end_iso]

    def delete_reading(self, reading_id: int) -> None:
        idx = reading_id - 1
        if 0 <= idx < len(self._rows):
            del self._rows[idx]

    def backup_data(self, backup_path: str) -> None:
        CSVManager(backup_path).save_readings(self._rows)

    def restore_data(self, backup_path: str) -> int:
        rows = CSVManager(backup_path).load_readings()
        self._rows = rows
        return len(rows)


def create_repository(storage_type: str, **kwargs: Any) -> DataRepository:
    def _normalize_csv_path(path: str) -> str:
        normalized = os.path.normpath(path)
        # Accept directory-style inputs (existing directory or trailing separator) and map to default filename.
        if os.path.isdir(normalized) or path.endswith(("/", "\\")):
            return os.path.join(normalized, "readings.csv")
        return normalized

    st = (storage_type or "sqlite").lower()
    if st == "sqlite":
        path = kwargs.get("db_path") or kwargs.get("database_path") or "data/tneb_readings.db"
        return SQLiteRepository(path)
    if st == "csv":
        path = kwargs.get("csv_path") or kwargs.get("backup_path") or "data/backups/readings.csv"
        return CSVRepository(_normalize_csv_path(path))
    if st == "memory":
        return MemoryRepository()
    # default fallback
    return MemoryRepository()

