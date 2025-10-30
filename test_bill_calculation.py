from __future__ import annotations

import unittest

from models import MeterManager
from models.tariff_calculator import TariffCalculator
from models.meter_reading import MeterReading
from gui.bill_utils import BillCalculationHelper, RotationOptimizer, ThresholdMonitor, get_overall_summary


class TestBillCalculationHelpers(unittest.TestCase):
	def setUp(self):
		self.calc = TariffCalculator()

	def test_bill_under_100(self):
		mr = MeterReading(meter_id="R", meter_name="R", reading_date="2025-01-01", current_reading=120, previous_reading=50)
		res = BillCalculationHelper.calculate_meter_bill(mr, self.calc)
		self.assertEqual(res["units"], 70.0)
		self.assertAlmostEqual(res["amount"], 0.0, places=2)

	def test_marginal_rate_progression(self):
		self.assertEqual(self.calc.get_marginal_rate(0), 0.0)
		self.assertEqual(self.calc.get_marginal_rate(100), 2.30)
		self.assertEqual(self.calc.get_marginal_rate(200), 4.60)


class TestRotationAndThreshold(unittest.TestCase):
	def setUp(self):
		self.manager = MeterManager()
		# Seed prior reading to enable consumption
		from datetime import date, timedelta
		prior = date.today() - timedelta(days=60)
		self.manager.add_reading("R", prior, 100)
		self.manager.add_reading("Y", prior, 100)
		self.manager.add_reading("B", prior, 100)

	def test_rotation_recommendation(self):
		from datetime import date
		self.manager.add_reading("R", date.today(), 500)  # 400 units
		self.manager.add_reading("Y", date.today(), 350)  # 250 units
		self.manager.add_reading("B", date.today(), 200)  # 100 units
		rec = self.manager.recommend_rotation()
		self.assertIn("economics", rec)
		self.assertIn("approaching", rec)

	def test_threshold_monitor(self):
		status = ThresholdMonitor.check_all_meters(self.manager, threshold=350.0)
		self.assertIsInstance(status, list)


class TestOverallSummary(unittest.TestCase):
	def test_summary_structure(self):
		mm = MeterManager()
		summary = get_overall_summary(mm)
		self.assertIn("total_units", summary)
		self.assertIn("total_cost", summary)
		self.assertIn("rotation_economics", summary)


if __name__ == "__main__":
	unittest.main()


