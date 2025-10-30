"""Core models package for TNEB meter management.

This package contains:
- MeterReading: Data model representing a single meter reading entry
- TariffCalculator: Implements TNEB bi-monthly tariff slab calculations
- MeterManager: Coordinates readings across multiple meters
"""

# Re-export key classes for convenient imports like:
# from models import MeterReading, TariffCalculator, MeterManager

from .meter_reading import MeterReading  # noqa: F401
from .tariff_calculator import TariffCalculator  # noqa: F401
from .meter_manager import MeterManager  # noqa: F401


