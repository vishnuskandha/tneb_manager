"""Application credits shown in the Help -> About dialog."""

__all__ = ["get_credits"]


def get_credits() -> str:
    return (
        "TNEB Meter Reading Manager\n"
        "=====================\n"
        "A desktop app to manage TNEB/TANGEDCO meter readings (R/Y/B),\n"
        "calculate bi-monthly bills by tariff slab, and export reports.\n\n"
        "Built with Python, Tkinter, and pandas.\n\n"
        "Copyright (c) 2025 Vishnu Skandha\n"
        "Released under the MIT License."
    )
