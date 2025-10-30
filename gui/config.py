from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple


# Default configuration dictionary
GUI_CONFIG: Dict[str, Any] = {
	"colors": {
		"safe": "#28a745",
		"warning": "#ffc107",
		"critical": "#dc3545",
		"bill_positive": "#155724",
		"bill_negative": "#721c24",
	},
	"thresholds": {
		"rotation_threshold": 350.0,
		"warning_percentage": 0.8,
		"critical_percentage": 0.95,
	},
	"formatting": {
		"currency_symbol": "₹",
		"currency_decimals": 2,
		"units_decimals": 1,
	},
	"fonts": {
		"bill_amount": ("Segoe UI", 12, "bold"),
		"warning_text": ("Segoe UI", 10, "bold"),
		"normal_text": ("Segoe UI", 9),
	},
}


@dataclass
class GUIConfig:
	config: Dict[str, Any]

	def get_threshold_color(self, consumption: float, threshold: float | None = None) -> str:
		th = threshold if threshold is not None else float(self.config["thresholds"]["rotation_threshold"])
		warn_pct = float(self.config["thresholds"]["warning_percentage"])
		crit_pct = float(self.config["thresholds"]["critical_percentage"])
		colors = self.config["colors"]
		if consumption >= crit_pct * th:
			return colors["critical"]
		if consumption >= warn_pct * th:
			return colors["warning"]
		return colors["safe"]

	def format_currency(self, amount: float) -> str:
		symbol = self.config["formatting"]["currency_symbol"]
		decimals = int(self.config["formatting"]["currency_decimals"])
		return f"{symbol}{amount:.{decimals}f}"

	def format_units(self, units: float) -> str:
		decimals = int(self.config["formatting"]["units_decimals"])
		return f"{units:.{decimals}f} units"

	def get_warning_font(self) -> Tuple[str, int, str]:
		return tuple(self.config["fonts"]["warning_text"])  # type: ignore[return-value]

	def get_bill_font(self) -> Tuple[str, int, str]:
		return tuple(self.config["fonts"]["bill_amount"])  # type: ignore[return-value]

	def load_user_preferences(self) -> None:
		# Placeholder for future persistence-backed preferences
		return None

	def save_user_preferences(self) -> None:
		# Placeholder for future persistence-backed preferences
		return None


def get_gui_config() -> GUIConfig:
	return GUIConfig(GUI_CONFIG)


