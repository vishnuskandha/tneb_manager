from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import Any, Dict, Optional


VALID_METER_TYPES = {"3_phase", "single_phase"}


def _coerce_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        # Accept common formats: YYYY-MM-DD, DD/MM/YYYY
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    raise ValueError("reading_date must be a date, datetime, or parseable string")


def _validate_positive_number(name: str, value: Optional[float]) -> float:
    if value is None:
        raise ValueError(f"{name} is required")
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number") from None
    if numeric < 0:
        raise ValueError(f"{name} must be non-negative")
    return numeric


@dataclass
class MeterReading:
    """Represents a single meter reading entry for a meter.

    Attributes:
        meter_id: Short identifier such as "R", "Y", or "B".
        meter_name: Human-friendly name of the meter.
        reading_date: Date of the reading.
        current_reading: Current cumulative kWh reading.
        previous_reading: Previous cumulative kWh reading, if available.
        meter_type: Either "3_phase" or "single_phase".
        consumption: Derived field representing units consumed between readings.
    """

    meter_id: str
    meter_name: str
    reading_date: date
    current_reading: float
    previous_reading: Optional[float] = None
    meter_type: str = "single_phase"
    consumption: float = field(init=False, default=0.0)

    def __post_init__(self) -> None:
        if not self.meter_id or not isinstance(self.meter_id, str):
            raise ValueError("meter_id is required and must be a string")
        if not self.meter_name or not isinstance(self.meter_name, str):
            raise ValueError("meter_name is required and must be a string")

        self.reading_date = _coerce_date(self.reading_date)
        self.current_reading = _validate_positive_number("current_reading", self.current_reading)

        if self.previous_reading is not None:
            self.previous_reading = _validate_positive_number("previous_reading", self.previous_reading)
            if self.current_reading < self.previous_reading:
                raise ValueError("current_reading must be greater than or equal to previous_reading")

        if self.meter_type not in VALID_METER_TYPES:
            raise ValueError(f"meter_type must be one of {sorted(VALID_METER_TYPES)}")

        self.consumption = self.calculate_consumption()

    def calculate_consumption(self) -> float:
        """Calculate consumption as current - previous if previous is available, else 0."""
        if self.previous_reading is None:
            return 0.0
        return max(0.0, self.current_reading - self.previous_reading)

    def is_approaching_limit(self, threshold: float = 350.0) -> bool:
        """Return True if the consumption is approaching a threshold (default 350 units)."""
        return self.consumption >= 0.9 * threshold

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["reading_date"] = self.reading_date.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MeterReading":
        # Copy and sanitize incoming data: ignore unknown keys and normalize fields
        incoming: Dict[str, Any] = dict(data)

        # Normalize reading_date
        if "reading_date" in incoming:
            incoming["reading_date"] = _coerce_date(incoming["reading_date"])

        # Normalize previous_reading: treat "", "None" as None
        if "previous_reading" in incoming:
            prev_val = incoming["previous_reading"]
            if prev_val in ("", "None", None):
                incoming["previous_reading"] = None

        # Whitelist known constructor args; ignore extras like 'consumption'
        allowed_keys = {
            "meter_id",
            "meter_name",
            "reading_date",
            "current_reading",
            "previous_reading",
            "meter_type",
        }
        kwargs: Dict[str, Any] = {k: v for k, v in incoming.items() if k in allowed_keys}
        return cls(**kwargs)

    def __str__(self) -> str:
        prev = "None" if self.previous_reading is None else f"{self.previous_reading:.2f}"
        return (
            f"MeterReading(meter_id={self.meter_id}, name={self.meter_name}, "
            f"date={self.reading_date.isoformat()}, current={self.current_reading:.2f}, "
            f"previous={prev}, consumption={self.consumption:.2f}, type={self.meter_type})"
        )


