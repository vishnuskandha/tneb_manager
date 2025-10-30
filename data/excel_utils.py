"""
Utilities for preparing data and applying formatting for Excel exports.

This module provides helper classes to transform reading histories and
apply consistent formatting to Excel worksheets. It is intentionally
decoupled from any specific writer implementation to support both
openpyxl and xlsxwriter backends used by pandas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Any, Dict, Iterable, List, Optional, Tuple


# Public API surface kept small and explicit
__all__ = [
    "ExcelFormatHelper",
    "DataPreparationHelper",
    "prepare_tangedco_data",
    "calculate_billing_cycle_data",
    "format_excel_date",
    "apply_conditional_formatting",
    "create_summary_charts",
    "validate_export_data",
    "check_date_continuity",
    "verify_consumption_calculations",
]


@dataclass
class TangedcoColumnConfig:
    """Configuration for TANGEDCO style columns.

    The expected layout is:
    Date | First Floor Main (3 Phase) | Diff | 2nd Floor | Diff | First Floor Side Portion | Diff
    """

    date_header: str = "Date"
    meter_headers: Tuple[str, str, str] = (
        "First Floor Main (3 Phase)",
        "2nd Floor",
        "First Floor Side Portion",
    )
    diff_header: str = "Diff"
    id_to_header: Dict[str, str] = field(
        default_factory=lambda: {
            "R": "First Floor Main (3 Phase)",
            "Y": "2nd Floor",
            "B": "First Floor Side Portion",
        }
    )


class ExcelFormatHelper:
    """Helpers for styling and formatting Excel outputs.

    These helpers are backend-agnostic at call sites. When a specific engine
    object (openpyxl Worksheet or xlsxwriter Worksheet) is detected, best-effort
    formatting is applied. Calls are intentionally no-ops if a capability is not
    available so exports never fail due to styling.
    """

    HEADER_FILL_COLOR = "#D9E1F2"  # Light blue
    WARNING_FILL_COLOR = "#FCE4D6"  # Light red
    CURRENCY_FORMAT_INR = "\u20B9#,##0.00"
    DATE_FORMAT_DDMMYYYY = "DD/MM/YYYY"

    @staticmethod
    def format_headers(ws: Any, header_row_index: int = 1) -> None:
        """Apply header styling if supported by the worksheet engine."""
        try:
            from openpyxl.styles import PatternFill, Font, Border, Side, Alignment

            max_col = ws.max_column
            header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
            thin = Side(border_style="thin", color="000000")
            border = Border(left=thin, right=thin, top=thin, bottom=thin)
            for col in range(1, max_col + 1):
                cell = ws.cell(row=header_row_index, column=col)
                cell.fill = header_fill
                cell.font = Font(bold=True)
                cell.border = border
                cell.alignment = Alignment(horizontal="center")
        except Exception:
            # Best-effort; ignore if engine not openpyxl or styling unavailable
            return

    @staticmethod
    def set_column_widths(ws: Any, widths: Dict[int, float]) -> None:
        try:
            for idx, width in widths.items():
                col_letter = getattr(ws, "cell")(row=1, column=idx).column_letter  # type: ignore[attr-defined]
                ws.column_dimensions[col_letter].width = width
        except Exception:
            return

    @staticmethod
    def apply_currency_format(ws: Any, data_range: str) -> None:
        try:
            # openpyxl range like "C2:C100"
            for row in ws[data_range]:
                for cell in row:
                    cell.number_format = ExcelFormatHelper.CURRENCY_FORMAT_INR
        except Exception:
            return

    @staticmethod
    def apply_date_format(ws: Any, data_range: str) -> None:
        try:
            for row in ws[data_range]:
                for cell in row:
                    cell.number_format = ExcelFormatHelper.DATE_FORMAT_DDMMYYYY
        except Exception:
            return


class DataPreparationHelper:
    """Transforms domain objects into tabular structures for Excel."""

    @staticmethod
    def to_rows_for_tangedco(
        readings_by_meter: Dict[str, List[Dict[str, Any]]],
        config: Optional[TangedcoColumnConfig] = None,
    ) -> Tuple[List[str], List[List[Any]]]:
        """Create headers and rows for TANGEDCO format.

        readings_by_meter is a dict with keys being meter names and values
        being a list of dicts containing at least {'date': datetime/date, 'reading': float}.
        The function computes per-meter differences between consecutive readings.
        Rows are aligned by date across meters.
        """
        if config is None:
            config = TangedcoColumnConfig()

        # Determine canonical order of meters based on provided config
        canonical_meters: List[str] = list(config.meter_headers)

        # Build a sorted unique set of dates across all meters
        all_dates: List[date] = sorted(
            {
                (r.get("date").date() if isinstance(r.get("date"), datetime) else r.get("date"))
                for meter_readings in readings_by_meter.values()
                for r in meter_readings
                if r.get("date") is not None
            }
        )

        # Build quick lookup per meter for reading by date
        meter_date_to_reading: Dict[str, Dict[date, float]] = {}
        for meter_name, items in readings_by_meter.items():
            lookup: Dict[date, float] = {}
            for r in items:
                d = r.get("date")
                if isinstance(d, datetime):
                    d = d.date()
                if d is None:
                    continue
                lookup[d] = float(r.get("reading", 0.0))
            meter_date_to_reading[meter_name] = lookup

        # Prepare rows: [date, meter1_reading, meter1_diff, meter2_reading, meter2_diff, meter3_reading, meter3_diff]
        rows: List[List[Any]] = []
        previous_by_meter: Dict[str, Optional[float]] = {m: None for m in canonical_meters}
        for d in all_dates:
            row: List[Any] = [d]
            for meter_name in canonical_meters:
                reading = meter_date_to_reading.get(meter_name, {}).get(d)
                row.append(reading)
                prev = previous_by_meter.get(meter_name)
                diff_value = None
                if reading is not None and prev is not None:
                    diff_value = reading - prev
                row.append(diff_value)
                previous_by_meter[meter_name] = reading if reading is not None else prev
            rows.append(row)

        headers: List[str] = [config.date_header]
        for meter_header in canonical_meters:
            headers.extend([meter_header, config.diff_header])

        return headers, rows


def prepare_tangedco_data(
    readings_history: Dict[str, List[Dict[str, Any]]]
) -> Tuple[List[str], List[List[Any]]]:
    """Transform readings history into TANGEDCO headers and rows."""
    return DataPreparationHelper.to_rows_for_tangedco(readings_history)


def calculate_billing_cycle_data(
    readings: List[Dict[str, Any]], start_date: date, end_date: date
) -> List[Dict[str, Any]]:
    """Return readings within a given bi-monthly billing cycle bounds (inclusive)."""
    results: List[Dict[str, Any]] = []
    for r in readings:
        d = r.get("date")
        if isinstance(d, datetime):
            d = d.date()
        if d is None:
            continue
        if start_date <= d <= end_date:
            results.append(r)
    return results


def format_excel_date(date_obj: date | datetime) -> datetime:
    """Convert a date or datetime to a datetime for Excel writers."""
    if isinstance(date_obj, datetime):
        return date_obj
    return datetime(date_obj.year, date_obj.month, date_obj.day)


def apply_conditional_formatting(ws: Any, data_range: str) -> None:
    """Apply threshold-based conditional formatting if supported by the engine."""
    try:
        from openpyxl.formatting.rule import ColorScaleRule

        rule = ColorScaleRule(start_type="min", start_color="FFFFFF", mid_type="percentile", mid_value=50,
                              mid_color="FFF4B084", end_type="max", end_color="FFE36C0A")
        ws.conditional_formatting.add(data_range, rule)
    except Exception:
        return


def create_summary_charts(ws: Any, data: Any) -> None:
    """Optionally add charts to the worksheet. Best-effort no-op on failure."""
    try:
        # Placeholder: charts can be added in future. Keep a safe no-op here.
        _ = ws
        _ = data
    except Exception:
        return


def validate_export_data(meter_manager: Any) -> Tuple[bool, Optional[str]]:
    """Validate that essential data is present for export."""
    try:
        history = getattr(meter_manager, "get_readings_history")()
        if not history:
            return False, "No readings history available for export."
        return True, None
    except Exception as exc:
        return False, f"Validation failed: {exc}"


def check_date_continuity(readings: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
    """Ensure reading dates are in non-decreasing order."""
    normalized: List[date] = []
    for r in readings:
        d = r.get("date")
        if isinstance(d, datetime):
            d = d.date()
        if d is not None:
            normalized.append(d)
    if normalized != sorted(normalized):
        return False, "Reading dates are not in chronological order."
    return True, None


def verify_consumption_calculations(readings: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
    """Lightweight sanity check for non-negative diffs when strictly increasing."""
    last_value: Optional[float] = None
    for r in readings:
        value = r.get("reading")
        try:
            value_f = float(value) if value is not None else None
        except Exception:
            return False, "Encountered non-numeric reading value."
        if value_f is None:
            continue
        if last_value is not None and value_f < last_value:
            # Allow resets, but flag as warning
            return False, "Reading decreased; possible meter reset detected."
        last_value = value_f
    return True, None


