from __future__ import annotations

import csv
import os
from typing import Iterable, List, Optional

from models.meter_reading import MeterReading


CSV_HEADERS = [
    "meter_id",
    "meter_name",
    "reading_date",
    "current_reading",
    "previous_reading",
    "meter_type",
    "consumption",
]


class CSVError(Exception):
    pass


class CSVManager:
    def __init__(self, csv_path: str) -> None:
        self.csv_path = csv_path

    def validate_csv_format(self, csv_path: Optional[str] = None) -> bool:
        path = csv_path or self.csv_path
        try:
            with open(path, "r", newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                headers = next(reader)
                return headers == CSV_HEADERS
        except FileNotFoundError:
            return False
        except Exception as exc:
            raise CSVError(f"Failed to validate CSV: {exc}") from exc

    def save_readings(self, readings_list: Iterable[MeterReading]) -> None:
        try:
            os.makedirs(os.path.dirname(self.csv_path) or ".", exist_ok=True)
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
                writer.writeheader()
                for reading in readings_list:
                    writer.writerow(reading.to_dict())
        except Exception as exc:
            raise CSVError(f"Failed to save readings: {exc}") from exc

    def append_reading(self, meter_reading: MeterReading) -> None:
        try:
            file_exists = os.path.exists(self.csv_path)
            os.makedirs(os.path.dirname(self.csv_path) or ".", exist_ok=True)
            with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(meter_reading.to_dict())
        except Exception as exc:
            raise CSVError(f"Failed to append reading: {exc}") from exc

    def load_readings(self) -> List[MeterReading]:
        try:
            with open(self.csv_path, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                return [MeterReading.from_dict(row) for row in reader]
        except FileNotFoundError:
            return []
        except Exception as exc:
            raise CSVError(f"Failed to load readings: {exc}") from exc

    def get_readings_by_meter(self, meter_id: str) -> List[MeterReading]:
        rows = [r for r in self.load_readings() if r.meter_id == meter_id]
        rows.sort(key=lambda r: r.reading_date)
        return rows

    def backup_database_to_csv(self, database_manager, csv_path: str) -> None:
        database_manager.backup_to_csv(csv_path)

    @staticmethod
    def merge_csv_files(csv_files: List[str], output_path: str) -> int:
        try:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            written = 0
            with open(output_path, "w", newline="", encoding="utf-8") as out:
                writer = csv.DictWriter(out, fieldnames=CSV_HEADERS)
                writer.writeheader()
                for path in csv_files:
                    if not os.path.exists(path):
                        continue
                    with open(path, "r", newline="", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            writer.writerow(row)
                            written += 1
            return written
        except Exception as exc:
            raise CSVError(f"Failed to merge CSV files: {exc}") from exc


