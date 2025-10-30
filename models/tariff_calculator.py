from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple
from decimal import Decimal, ROUND_HALF_UP
import math


@dataclass(frozen=True)
class TariffSlab:
    upper_limit: float  # inclusive upper bound for the slab; use float('inf') for no upper bound
    rate: float         # INR per unit for units in this slab


class TariffCalculator:
    """Implements TNEB 2025 bi-monthly tariff slabs.

    Slabs implemented as per provided structure:
      - 0-100:   ₹0.00
      - 101-200: ₹2.30
      - 201-400: ₹4.60
      - 401-500: ₹6.45
      - 501-600: ₹8.55
      - 601-800: ₹9.50
      - 801-1000: ₹10.50
      - >1000:   ₹11.50
    """

    # Define slabs with cumulative upper bounds
    _SLABS: Tuple[TariffSlab, ...] = (
        TariffSlab(100, 0.00),
        TariffSlab(200, 2.30),
        TariffSlab(400, 4.60),
        TariffSlab(500, 6.45),
        TariffSlab(600, 8.55),
        TariffSlab(800, 9.50),
        TariffSlab(1000, 10.50),
        TariffSlab(float("inf"), 11.50),
    )

    def __init__(self, fixed_charge: float = 0.0) -> None:
        # Store as Decimal internally to avoid floating point drift
        self.fixed_charge: Decimal = Decimal(str(max(0.0, float(fixed_charge))))

    def get_tariff_slabs(self) -> List[Dict[str, float]]:
        return [
            {"upper_limit": slab.upper_limit, "rate": slab.rate} for slab in self._SLABS
        ]

    def calculate_bill(self, consumption_units: float) -> float:
        """Calculate total bill for given units.

        Uses Decimal internally; returns float quantized to 2 decimals.
        """
        if consumption_units is None or consumption_units <= 0:
            return float(self.fixed_charge.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

        remaining = Decimal(str(float(consumption_units)))
        total_cost = Decimal("0")
        previous_limit = Decimal("0")
        for slab in self._SLABS:
            slab_upper = Decimal(str(slab.upper_limit))
            capacity = slab_upper - previous_limit
            slab_units = remaining if remaining < capacity else capacity
            if slab_units > 0:
                rate = Decimal(str(slab.rate))
                total_cost += slab_units * rate
                remaining -= slab_units
                previous_limit = slab_upper
            if remaining <= 0:
                break
        total_with_fixed = (total_cost + self.fixed_charge).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return float(total_with_fixed)

    def get_slab_breakdown(self, consumption_units: float) -> List[Dict[str, float]]:
        breakdown: List[Dict[str, float]] = []
        if consumption_units is None or consumption_units <= 0:
            return breakdown
        remaining = Decimal(str(float(consumption_units)))
        previous_limit = Decimal("0")
        for slab in self._SLABS:
            slab_upper = Decimal(str(slab.upper_limit))
            capacity = slab_upper - previous_limit
            slab_units = remaining if remaining < capacity else capacity
            if slab_units > 0:
                rate = Decimal(str(slab.rate))
                cost = (slab_units * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                breakdown.append(
                    {
                        "from": float(previous_limit + 1) if previous_limit > 0 else 0.0,
                        "to": slab.upper_limit,
                        "units": float(slab_units),
                        "rate": slab.rate,
                        "cost": float(cost),
                    }
                )
                remaining -= slab_units
                previous_limit = slab_upper
            if remaining <= 0:
                break
        return breakdown

    def get_marginal_rate(self, consumption_units: float) -> float:
        """Return the slab rate applicable to the NEXT unit of consumption.

        Example: if current consumption is 200.4, this returns the rate for unit 201.
        """
        if consumption_units is None or consumption_units < 0:
            return 0.0
        next_unit = max(0, math.floor(float(consumption_units or 0)) + 1)
        for slab in self._SLABS:
            if next_unit <= slab.upper_limit:
                return slab.rate
        return self._SLABS[-1].rate

    def calculate_savings_from_rotation(self, current_consumptions: Dict[str, float]) -> Dict[str, float]:
        """Estimate potential savings by separating combined consumption across meters.

        Given a dict of meter_id -> consumption units, compute:
        - combined_bill: bill if all units were on a single meter
        - separate_bill: sum of individual bills per meter
        - potential_savings: combined_bill - separate_bill (>0 indicates benefit of separation)
        """
        total_units = sum(max(0.0, float(v or 0.0)) for v in current_consumptions.values())
        combined_bill = self.calculate_bill(total_units)
        separate_bill = sum(self.calculate_bill(max(0.0, float(v or 0.0))) for v in current_consumptions.values())
        potential_savings_dec = (Decimal(str(combined_bill)) - Decimal(str(separate_bill))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return {
            "combined_bill": float(Decimal(str(combined_bill)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "separate_bill": float(Decimal(str(separate_bill)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "potential_savings": float(potential_savings_dec),
        }

    # Optional comparison helper
    def compare_scenarios(self, scenarios: Dict[str, float]) -> List[Dict[str, float]]:
        """Return a list of {scenario, units, cost} sorted by units."""
        rows: List[Dict[str, float]] = []
        for name, units in scenarios.items():
            rows.append({"scenario": name, "units": float(units), "cost": self.calculate_bill(float(units))})
        return sorted(rows, key=lambda r: r["units"])


