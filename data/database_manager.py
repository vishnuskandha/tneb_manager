from __future__ import annotations

import csv
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from models.meter_reading import MeterReading


class DatabaseError(Exception):
    pass


class DatabaseManager:
    """SQLite database manager for meter readings.

    Responsibilities:
    - Manage connection lifecycle
    - Initialize schema
    - Provide CRUD and query utilities
    - CSV backup/restore helpers
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception as exc:  # pragma: no cover - best-effort
            raise DatabaseError(f"Failed to close database: {exc}") from exc

    @contextmanager
    def _tx(self):
        try:
            yield
            self.conn.commit()
        except Exception as exc:
            self.conn.rollback()
            raise DatabaseError(str(exc)) from exc

    def create_tables(self) -> None:
        try:
            with self._tx():
                self.conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS meter_readings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        meter_id TEXT NOT NULL,
                        meter_name TEXT NOT NULL,
                        reading_date TEXT NOT NULL,
                        current_reading REAL NOT NULL,
                        previous_reading REAL,
                        meter_type TEXT NOT NULL,
                        consumption REAL NOT NULL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                self.conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_meter_date ON meter_readings(meter_id, reading_date)"
                )
        except Exception as exc:
            raise DatabaseError(f"Failed to create tables: {exc}") from exc

    # CRUD operations
    def insert_reading(self, meter_reading: MeterReading) -> int:
        data = meter_reading.to_dict()
        try:
            with self._tx():
                cur = self.conn.execute(
                    """
                    INSERT INTO meter_readings (
                        meter_id, meter_name, reading_date, current_reading,
                        previous_reading, meter_type, consumption
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        data["meter_id"],
                        data["meter_name"],
                        data["reading_date"],
                        data["current_reading"],
                        data.get("previous_reading"),
                        data["meter_type"],
                        data["consumption"],
                    ),
                )
                return int(cur.lastrowid)
        except Exception as exc:
            raise DatabaseError(f"Failed to insert reading: {exc}") from exc

    def update_reading(self, reading_id: int, meter_reading: MeterReading) -> None:
        data = meter_reading.to_dict()
        try:
            with self._tx():
                self.conn.execute(
                    """
                    UPDATE meter_readings
                    SET meter_id=?, meter_name=?, reading_date=?, current_reading=?,
                        previous_reading=?, meter_type=?, consumption=?
                    WHERE id=?
                    """,
                    (
                        data["meter_id"],
                        data["meter_name"],
                        data["reading_date"],
                        data["current_reading"],
                        data.get("previous_reading"),
                        data["meter_type"],
                        data["consumption"],
                        reading_id,
                    ),
                )
        except Exception as exc:
            raise DatabaseError(f"Failed to update reading {reading_id}: {exc}") from exc

    def delete_reading(self, reading_id: int) -> None:
        try:
            with self._tx():
                self.conn.execute("DELETE FROM meter_readings WHERE id=?", (reading_id,))
        except Exception as exc:
            raise DatabaseError(f"Failed to delete reading {reading_id}: {exc}") from exc

    # Queries
    def _row_to_reading(self, row: sqlite3.Row) -> MeterReading:
        return MeterReading.from_dict(
            {
                "meter_id": row["meter_id"],
                "meter_name": row["meter_name"],
                "reading_date": row["reading_date"],
                "current_reading": row["current_reading"],
                "previous_reading": row["previous_reading"],
                "meter_type": row["meter_type"],
            }
        )

    def get_readings_by_meter(self, meter_id: str, limit: Optional[int] = None) -> List[Tuple[int, MeterReading]]:
        try:
            sql = "SELECT * FROM meter_readings WHERE meter_id=? ORDER BY reading_date ASC, id ASC"
            params: Tuple[Any, ...] = (meter_id,)
            if limit is not None:
                sql += " LIMIT ?"
                params = (meter_id, int(limit))
            cur = self.conn.execute(sql, params)
            rows = cur.fetchall()
            return [(int(r["id"]), self._row_to_reading(r)) for r in rows]
        except Exception as exc:
            raise DatabaseError(f"Failed to fetch readings for {meter_id}: {exc}") from exc

    def get_latest_reading_by_meter(self, meter_id: str) -> Optional[Tuple[int, MeterReading]]:
        try:
            cur = self.conn.execute(
                """
                SELECT * FROM meter_readings
                WHERE meter_id=?
                ORDER BY reading_date DESC, id DESC
                LIMIT 1
                """,
                (meter_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return int(row["id"]), self._row_to_reading(row)
        except Exception as exc:
            raise DatabaseError(f"Failed to fetch latest reading for {meter_id}: {exc}") from exc

    def get_all_readings(self, order_by: str = "reading_date") -> List[Tuple[int, MeterReading]]:
        order_sql = "reading_date"
        if order_by in {"reading_date", "created_at", "meter_id", "id"}:
            order_sql = order_by
        try:
            cur = self.conn.execute(f"SELECT * FROM meter_readings ORDER BY {order_sql} ASC, id ASC")
            rows = cur.fetchall()
            return [(int(r["id"]), self._row_to_reading(r)) for r in rows]
        except Exception as exc:
            raise DatabaseError(f"Failed to fetch all readings: {exc}") from exc

    def get_readings_by_date_range(self, start_date: str, end_date: str) -> List[Tuple[int, MeterReading]]:
        # Accept date/datetime or strings; normalize to ISO strings
        try:
            sd = getattr(start_date, "isoformat", lambda: str(start_date))()
            ed = getattr(end_date, "isoformat", lambda: str(end_date))()
            cur = self.conn.execute(
                """
                SELECT * FROM meter_readings
                WHERE reading_date BETWEEN ? AND ?
                ORDER BY reading_date ASC, id ASC
                """,
                (sd, ed),
            )
            rows = cur.fetchall()
            return [(int(r["id"]), self._row_to_reading(r)) for r in rows]
        except Exception as exc:
            raise DatabaseError(f"Failed to fetch readings by date range: {exc}") from exc

    # CSV backup/restore
    def backup_to_csv(self, file_path: str) -> None:
        try:
            os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
            rows = self.get_all_readings(order_by="reading_date")
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "meter_id",
                        "meter_name",
                        "reading_date",
                        "current_reading",
                        "previous_reading",
                        "meter_type",
                        "consumption",
                    ],
                )
                writer.writeheader()
                for _id, reading in rows:
                    writer.writerow(reading.to_dict())
        except Exception as exc:
            raise DatabaseError(f"Failed to backup to CSV: {exc}") from exc

    def restore_from_csv(self, file_path: str) -> int:
        try:
            inserted = 0
            with open(file_path, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    reading = MeterReading.from_dict(row)
                    self.insert_reading(reading)
                    inserted += 1
            return inserted
        except Exception as exc:
            raise DatabaseError(f"Failed to restore from CSV: {exc}") from exc


