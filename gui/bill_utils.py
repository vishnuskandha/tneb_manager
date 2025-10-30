from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from models import MeterManager
from models.tariff_calculator import TariffCalculator
from models.meter_reading import MeterReading
from .config import get_gui_config


cfg = get_gui_config()


class BillCalculationHelper:
	@staticmethod
	def calculate_meter_bill(meter_reading: MeterReading | None, tariff_calculator: TariffCalculator) -> Dict[str, Any]:
		units = 0.0 if meter_reading is None else float(meter_reading.consumption)
		amount = float(tariff_calculator.calculate_bill(units))
		marginal = float(tariff_calculator.get_marginal_rate(units))
		breakdown = tariff_calculator.get_slab_breakdown(units)
		return {
			"units": units,
			"amount": amount,
			"marginal_rate": marginal,
			"breakdown": breakdown,
		}

	@staticmethod
	def format_currency(amount: float) -> str:
		return cfg.format_currency(float(amount or 0.0))

	@staticmethod
	def format_units(units: float) -> str:
		return cfg.format_units(float(units or 0.0))

	@staticmethod
	def get_threshold_color(consumption: float, threshold: float = 350.0) -> str:
		return cfg.get_threshold_color(float(consumption or 0.0), threshold)

	@staticmethod
	def get_slab_summary(consumption: float, tariff_calculator: TariffCalculator) -> List[Dict[str, float]]:
		return tariff_calculator.get_slab_breakdown(float(consumption or 0.0))


class RotationOptimizer:
	@staticmethod
	def analyze_rotation_opportunities(meter_manager: MeterManager) -> Dict[str, Any]:
		# Delegate to MeterManager to keep a single source for recommendations
		return meter_manager.recommend_rotation(threshold=float(cfg.config["thresholds"]["rotation_threshold"]))

	@staticmethod
	def calculate_potential_savings(current_state: Dict[str, float], tariff_calculator: TariffCalculator) -> Dict[str, float]:
		return tariff_calculator.calculate_savings_from_rotation(current_state)

	@staticmethod
	def format_recommendations(recommendations: List[str]) -> str:
		if not recommendations:
			return "No rotation needed"
		return "\n".join(f"• {r}" for r in recommendations)


class ThresholdMonitor:
	@staticmethod
	def check_all_meters(meter_manager: MeterManager, threshold: float = 350.0) -> List[Dict[str, Any]]:
		rows: List[Dict[str, Any]] = []
		status = meter_manager.get_meter_status(threshold=threshold)
		for row in status:
			rows.append(
				{
					"meter_id": row["meter_id"],
					"consumption": float(row["consumption"]),
					"warning_level": ThresholdMonitor.get_warning_level(float(row["consumption"]), threshold),
				}
			)
		return rows

	@staticmethod
	def get_warning_level(consumption: float, threshold: float) -> str:
		warn_pct = float(cfg.config["thresholds"]["warning_percentage"]) * threshold
		crit_pct = float(cfg.config["thresholds"]["critical_percentage"]) * threshold
		if consumption >= crit_pct:
			return "critical"
		if consumption >= warn_pct:
			return "warning"
		return "safe"

	@staticmethod
	def generate_threshold_alerts(meter_status: List[Dict[str, Any]]) -> List[str]:
		alerts: List[str] = []
		for s in meter_status:
			lvl = s["warning_level"]
			if lvl == "warning":
				alerts.append(f"Meter {s['meter_id']} nearing threshold")
			elif lvl == "critical":
				alerts.append(f"Meter {s['meter_id']} over threshold zone")
		return alerts


# Convenience helpers bridging models and GUI
def get_overall_summary(meter_manager: MeterManager) -> Dict[str, Any]:
	summary = meter_manager.get_consumption_summary()
	calc = meter_manager.tariff_calculator
	savings = calc.calculate_savings_from_rotation(summary["per_meter_units"])  # type: ignore[index]
	return {
		"total_units": float(summary["total_units"]),
		"total_cost": float(summary["total_cost"]),
		"per_meter_units": summary["per_meter_units"],
		"per_meter_cost": summary["per_meter_cost"],
		"rotation_economics": savings,
	}


