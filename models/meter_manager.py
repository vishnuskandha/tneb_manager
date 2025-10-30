from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional, Tuple
import os

from .meter_reading import MeterReading
from .tariff_calculator import TariffCalculator
try:
    from data.repository import DataRepository, create_repository
    from data.config import load_config, AppConfig
except Exception:
    # Allow operation without persistence for backward compatibility
    DataRepository = object  # type: ignore
    AppConfig = object  # type: ignore
    def create_repository(*args, **kwargs):  # type: ignore
        class _Dummy:
            pass
        return _Dummy()
    def load_config(*args, **kwargs):  # type: ignore
        return None


@dataclass
class MeterConfig:
    meter_id: str
    meter_name: str
    meter_type: str  # "3_phase" or "single_phase"


class MeterManager:
    """High-level orchestrator for multiple meters and billing operations.

    Persistence-aware via a pluggable repository. Maintains an in-memory
    `reading_history` list for backward compatibility and UI usage, and
    syncs with the configured repository when auto_save is enabled.
    """

    def __init__(self, *, repository: Optional[DataRepository] = None, auto_save: bool = True, backup_enabled: bool = True) -> None:
        self.meters: Dict[str, MeterConfig] = {
            "R": MeterConfig("R", "First Floor Main (3 Phase)", "3_phase"),
            "Y": MeterConfig("Y", "2nd Floor (3 Phase)", "3_phase"),
            "B": MeterConfig("B", "First Floor Side Portion (Single Phase)", "single_phase"),
        }
        self.tariff_calculator = TariffCalculator()
        self.reading_history: List[MeterReading] = []
        self.auto_save = bool(auto_save)
        self.backup_enabled = bool(backup_enabled)

        # Initialize repository with default config if not provided
        self.config: Optional[AppConfig] = None
        try:
            self.config = load_config()
        except Exception:
            self.config = None
        if repository is not None:
            self.repository = repository
        else:
            try:
                backend = None if self.config is None else self.config.data.get("storage", {}).get("backend", "sqlite")
                db_path = None if self.config is None else self.config.data["storage"].get("database_path")
                csv_path = None if self.config is None else self.config.data["storage"].get("csv_backup_path")
                self.repository = create_repository(backend or "sqlite", db_path=db_path, csv_path=csv_path)
            except Exception:
                self.repository = None  # type: ignore

        # Load any existing readings from storage to in-memory history
        self.load_readings_from_storage()

    def _get_last_reading_for_meter(self, meter_id: str) -> Optional[MeterReading]:
        # Prefer repository if available
        try:
            if getattr(self, "repository", None) and hasattr(self.repository, "get_latest_reading_by_meter"):
                latest = self.repository.get_latest_reading_by_meter(meter_id)  # type: ignore[attr-defined]
                if latest is not None:
                    return latest
        except Exception:
            pass
        for reading in reversed(self.reading_history):
            if reading.meter_id == meter_id:
                return reading
        return None

    def validate_reading(self, meter_id: str, new_reading: float) -> Tuple[bool, Optional[str]]:
        last = self._get_last_reading_for_meter(meter_id)
        if last is None:
            return True, None
        if new_reading < last.current_reading:
            return False, "New reading must be greater than or equal to previous reading"
        return True, None

    def add_reading(self, meter_id: str, reading_date: date, current_reading: float) -> MeterReading:
        if meter_id not in self.meters:
            raise KeyError(f"Unknown meter_id: {meter_id}")

        last = self._get_last_reading_for_meter(meter_id)
        if last is not None and reading_date < last.reading_date:
            raise ValueError(
                f"Reading date {reading_date} is earlier than last reading date {last.reading_date} for meter {meter_id}"
            )
        previous_value = last.current_reading if last else None

        ok, err = self.validate_reading(meter_id, float(current_reading))
        if not ok:
            raise ValueError(err)

        cfg = self.meters[meter_id]
        reading = MeterReading(
            meter_id=meter_id,
            meter_name=cfg.meter_name,
            reading_date=reading_date,
            current_reading=float(current_reading),
            previous_reading=previous_value,
            meter_type=cfg.meter_type,
        )
        self.reading_history.append(reading)
        # Persist if enabled
        if getattr(self, "repository", None) and self.auto_save:
            try:
                self.repository.save_reading(reading)  # type: ignore[attr-defined]
            except Exception:
                # Fail silently to not break UI/CLI; in-memory keeps working
                pass
        return reading

    def get_latest_readings(self) -> Dict[str, Optional[MeterReading]]:
        latest: Dict[str, Optional[MeterReading]] = {k: None for k in self.meters}
        for meter_id in self.meters:
            latest[meter_id] = self._get_last_reading_for_meter(meter_id)
        return latest

    def get_consumption_summary(self) -> Dict[str, Any]:
        latest = self.get_latest_readings()
        per_meter_units: Dict[str, float] = {
            m_id: (r.consumption if r is not None else 0.0) for m_id, r in latest.items()
        }
        total_units = sum(per_meter_units.values())
        per_meter_cost: Dict[str, float] = {
            m_id: self.tariff_calculator.calculate_bill(units) for m_id, units in per_meter_units.items()
        }
        total_cost = sum(per_meter_cost.values())
        return {
            "per_meter_units": per_meter_units,
            "total_units": total_units,
            "per_meter_cost": per_meter_cost,
            "total_cost": round(total_cost, 2),
        }

    def calculate_total_bill(self) -> float:
        summary = self.get_consumption_summary()
        return float(summary["total_cost"])

    def recommend_rotation(self, threshold: float = 350.0) -> Dict[str, Any]:
        latest = self.get_latest_readings()
        approaching = {
            m_id: r for m_id, r in latest.items() if r is not None and r.is_approaching_limit(threshold)
        }
        suggestions: List[str] = []
        if approaching:
            # Suggest shifting from highest consumption meters to lowest
            sorted_by_units = sorted(
                ((m_id, r.consumption) for m_id, r in latest.items() if r is not None),
                key=lambda x: x[1],
                reverse=True,
            )
            if len(sorted_by_units) >= 2:
                src, _ = sorted_by_units[0]
                dst, _ = sorted_by_units[-1]
                suggestions.append(f"Shift non-critical load from {src} to {dst} to stay under slabs")

        consumptions = {m_id: (r.consumption if r else 0.0) for m_id, r in latest.items()}
        savings = self.tariff_calculator.calculate_savings_from_rotation(consumptions)
        return {
            "approaching": list(approaching.keys()),
            "suggestions": suggestions,
            "economics": savings,
        }

    def get_meter_status(self, threshold: float = 350.0) -> List[Dict[str, Any]]:
        latest = self.get_latest_readings()
        rows: List[Dict[str, Any]] = []
        for m_id, cfg in self.meters.items():
            r = latest[m_id]
            rows.append(
                {
                    "meter_id": m_id,
                    "meter_name": cfg.meter_name,
                    "meter_type": cfg.meter_type,
                    "has_reading": r is not None,
                    "current": None if r is None else r.current_reading,
                    "previous": None if r is None else r.previous_reading,
                    "consumption": 0.0 if r is None else r.consumption,
                    "approaching_threshold": False if r is None else r.is_approaching_limit(threshold),
                }
            )
        return rows

    def export_readings_data(self) -> List[Dict[str, Any]]:
        # Flat records suitable for CSV/Excel
        try:
            if getattr(self, "repository", None) and hasattr(self.repository, "get_all_readings"):
                rows = self.repository.get_all_readings()  # type: ignore[attr-defined]
                return [r.to_dict() for r in rows]
        except Exception:
            pass
        return [r.to_dict() for r in self.reading_history]

    # Persistence helpers
    def load_readings_from_storage(self) -> None:
        try:
            if getattr(self, "repository", None) and hasattr(self.repository, "get_all_readings"):
                rows = self.repository.get_all_readings()  # type: ignore[attr-defined]
                self.reading_history = list(rows)
        except Exception:
            # Keep existing in-memory history
            pass

    def save_all_readings(self) -> None:
        try:
            if getattr(self, "repository", None) and hasattr(self.repository, "save_reading"):
                for r in self.reading_history:
                    self.repository.save_reading(r)  # type: ignore[attr-defined]
        except Exception:
            pass

    def create_backup(self, backup_path: Optional[str] = None) -> None:
        try:
            # Respect backup_enabled flag
            if not self.backup_enabled:
                return
            if getattr(self, "repository", None) and hasattr(self.repository, "backup_data"):
                path = backup_path
                if path is None and self.config is not None:
                    # default backup file
                    directory = self.config.get_backup_directory()
                    path = os.path.join(directory, "readings_backup.csv")  # type: ignore[name-defined]
                if path is None:
                    return
                self.repository.backup_data(path)  # type: ignore[attr-defined]
        except Exception:
            pass

    def restore_from_backup(self, backup_path: str) -> int:
        try:
            if getattr(self, "repository", None) and hasattr(self.repository, "restore_data"):
                count = self.repository.restore_data(backup_path)  # type: ignore[attr-defined]
                self.load_readings_from_storage()
                return int(count)
        except Exception:
            pass
        return 0

    def get_readings_history(self, meter_id: Optional[str] = None, limit: Optional[int] = None) -> List[MeterReading]:
        try:
            if getattr(self, "repository", None):
                if meter_id:
                    rows = self.repository.get_readings_by_meter(meter_id, limit=limit)  # type: ignore[attr-defined]
                    return rows
                rows = self.repository.get_all_readings()  # type: ignore[attr-defined]
                if limit is not None:
                    return rows[: int(limit)]
                return rows
        except Exception:
            pass
        rows = [r for r in self.reading_history if (meter_id is None or r.meter_id == meter_id)]
        return rows if limit is None else rows[: int(limit)]

    def get_readings_by_date_range(self, start_date: str, end_date: str) -> List[MeterReading]:
        try:
            if getattr(self, "repository", None) and hasattr(self.repository, "get_readings_by_date_range"):
                return self.repository.get_readings_by_date_range(start_date, end_date)  # type: ignore[attr-defined]
        except Exception:
            pass
        return [r for r in self.reading_history if start_date <= r.reading_date.isoformat() <= end_date]

    def switch_storage_backend(self, new_repository: DataRepository) -> None:
        # Migrate current in-memory to new repo, then switch
        try:
            self.repository = new_repository  # type: ignore[assignment]
            if self.auto_save:
                self.save_all_readings()
        finally:
            self.load_readings_from_storage()

    # Migration helpers
    def migrate_from_memory(self) -> None:
        if getattr(self, "repository", None):
            for r in self.reading_history:
                try:
                    self.repository.save_reading(r)  # type: ignore[attr-defined]
                except Exception:
                    pass
            self.load_readings_from_storage()

    def migrate_between_repositories(self, source_repo: DataRepository, target_repo: DataRepository) -> int:
        try:
            rows = source_repo.get_all_readings()
            count = 0
            for r in rows:
                target_repo.save_reading(r)
                count += 1
            return count
        except Exception:
            return 0


