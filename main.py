from __future__ import annotations

import argparse
import os
from datetime import date, timedelta

from models import MeterManager
from data import load_config, create_repository
from gui.config import get_gui_config


def print_breakdown(title: str, breakdown):
	print(f"\n{title}")
	for row in breakdown:
		start = int(row["from"]) if isinstance(row["from"], float) else row["from"]
		end = "∞" if row["to"] == float("inf") else int(row["to"])
		print(f"  {start}-{end} units @ ₹{row['rate']:.2f}: {row['units']} units -> ₹{row['cost']}")


def run_cli_demo(storage: str = "sqlite", db_path: str | None = None, csv_path: str | None = None) -> None:
	repo = create_repository(storage, db_path=db_path, csv_path=csv_path)
	manager = MeterManager(repository=repo)

	today = date.today()

	# Seed previous cycle readings (simulate prior state)
	prior = today - timedelta(days=60)
	manager.add_reading("R", prior, 0)
	manager.add_reading("Y", prior, 0)
	manager.add_reading("B", prior, 0)

	# Current readings sample provided: R:394, Y:583, B:675
	r = manager.add_reading("R", today, 394)
	y = manager.add_reading("Y", today, 583)
	b = manager.add_reading("B", today, 675)

	print("Latest readings:")
	for m_id, reading in manager.get_latest_readings().items():
		print(f"  {m_id}: {reading}")

	print("\nConsumption summary (bi-monthly):")
	summary = manager.get_consumption_summary()
	for m_id, units in summary["per_meter_units"].items():
		print(f"  Meter {m_id}: {units} units -> ₹{summary['per_meter_cost'][m_id]}")
	print(f"  Total: {summary['total_units']} units -> ₹{summary['total_cost']}")

	# Detailed tariff breakdown for one meter example
	print_breakdown("Tariff breakdown for R", manager.tariff_calculator.get_slab_breakdown(r.consumption))

	# Rotation recommendation
	rec = manager.recommend_rotation()
	print("\nRotation recommendations:")
	print(f"  Approaching threshold: {rec['approaching']}")
	if rec["suggestions"]:
		for s in rec["suggestions"]:
			print(f"  Suggestion: {s}")
	econ = rec["economics"]
	print(
		f"  Economics -> Combined: ₹{econ['combined_bill']}, Separate: ₹{econ['separate_bill']}, Potential savings: ₹{econ['potential_savings']}"
	)


def run_gui(storage: str = "sqlite", db_path: str | None = None, csv_path: str | None = None) -> None:
	try:
		from gui.app import TNEBApp
	except Exception as exc:
		print(f"GUI dependencies missing or failed to import: {exc}. Falling back to CLI demo.")
		run_cli_demo(storage=storage, db_path=db_path, csv_path=csv_path)
		return
	app = TNEBApp()
	app.run()


def main():
	parser = argparse.ArgumentParser(description="TNEB Meter Reading Manager")
	parser.add_argument("--cli", "-c", action="store_true", help="Run CLI demo instead of GUI")
	parser.add_argument("--threshold", type=float, default=None, help="Set custom rotation threshold (default: 350)")
	parser.add_argument("--auto-calculate", action="store_true", help="Enable automatic bill calculation on input")
	parser.add_argument("--show-recommendations", action="store_true", help="Enable rotation recommendations display")
	parser.add_argument("--storage", choices=["sqlite", "csv", "memory"], default=None, help="Choose storage backend")
	parser.add_argument("--db-path", dest="db_path", default=None, help="Path to SQLite database file")
	parser.add_argument("--backup", dest="backup", default=None, help="Create backup at path (CSV)")
	parser.add_argument("--restore", dest="restore", default=None, help="Restore data from CSV path")
	parser.add_argument("--migrate-to", dest="migrate_to", choices=["sqlite", "csv"], default=None, help="Migrate data to backend")
	# Export-related CLI options
	parser.add_argument("--export-tangedco", dest="export_tangedco", default=None, help="Export in TANGEDCO Excel format to PATH")
	parser.add_argument("--export-summary", dest="export_summary", default=None, help="Export summary report to PATH")
	parser.add_argument("--export-detailed", dest="export_detailed", default=None, help="Export detailed history to PATH")
	parser.add_argument("--export-all", dest="export_all", default=None, help="Export multi-sheet workbook to PATH")
	parser.add_argument("--export-format", dest="export_format", choices=["xlsx", "csv"], default=None, help="Force export format")
	parser.add_argument("--billing-cycle", nargs=2, metavar=("START_DDMMYYYY", "END_DDMMYYYY"), default=None, help="Specify billing cycle for export (optional)")
	args = parser.parse_args()
	# Credits are only shown in the GUI About dialog

	cfg = load_config()
	backend = args.storage or cfg.data["storage"].get("backend", "sqlite")
	db_path = args.db_path or cfg.data["storage"].get("database_path")
	csv_dir = cfg.data["storage"].get("csv_backup_path")
	csv_path = None
	if backend == "csv":
		csv_path = os.path.join(csv_dir, "readings.csv")

	repo = create_repository(backend, db_path=db_path, csv_path=csv_path)
	manager = MeterManager(repository=repo)

	# Apply GUI configuration threshold if provided
	if args.threshold is not None:
		gc = get_gui_config()
		gc.config["thresholds"]["rotation_threshold"] = float(args.threshold)

	if args.backup:
		manager.create_backup(args.backup)
		print(f"Backup created at {args.backup}")
		return

	if args.restore:
		count = manager.restore_from_backup(args.restore)
		print(f"Restored {count} readings from {args.restore}")
		return

	if args.migrate_to:
		target_repo = create_repository(args.migrate_to, db_path=db_path, csv_path=csv_path)
		count = manager.migrate_between_repositories(repo, target_repo)
		print(f"Migrated {count} readings to {args.migrate_to}")
		return

	# Handle export-only flows
	if any([args.export_tangedco, args.export_summary, args.export_detailed, args.export_all]):
		try:
			from data.excel_exporter import ExcelExporter
		except Exception as exc:
			print(f"Excel export unavailable: {exc}")
			return

		exporter = ExcelExporter()

		start = None
		end = None
		if args.billing_cycle:
			from datetime import datetime as _dt
			try:
				start = _dt.strptime(args.billing_cycle[0], "%d%m%Y").date()
				end = _dt.strptime(args.billing_cycle[1], "%d%m%Y").date()
			except Exception as exc:
				print(f"Invalid --billing-cycle: {exc}")

		def ensure_ext(path: str, preferred: str) -> str:
			if args.export_format == "csv":
				if not path.lower().endswith(".csv"):
					path = f"{os.path.splitext(path)[0]}.csv"
			else:
				if preferred == "xlsx" and not path.lower().endswith(".xlsx"):
					path = f"{os.path.splitext(path)[0]}.xlsx"
			return path

		if args.export_tangedco:
			path = ensure_ext(args.export_tangedco, "xlsx")
			out = exporter.export_tangedco_format(path, manager, start, end)
			print(f"TANGEDCO export complete: {out}")
			return
		if args.export_summary:
			path = ensure_ext(args.export_summary, "xlsx")
			out = exporter.export_summary_report(path, manager)
			print(f"Summary export complete: {out}")
			return
		if args.export_detailed:
			path = ensure_ext(args.export_detailed, "xlsx")
			out = exporter.export_detailed_history(path, manager, start, end)
			print(f"Detailed history export complete: {out}")
			return
		if args.export_all:
			path = ensure_ext(args.export_all, "xlsx")
			out = exporter.create_workbook_with_multiple_sheets(path, manager, start, end)
			print(f"All-in-one export complete: {out}")
			return

	if args.cli:
		run_cli_demo(storage=backend, db_path=db_path, csv_path=csv_path)
	else:
		# Environment toggles for GUI behavior (read by GUI components if implemented later)
		if args.auto_calculate:
			os.environ["TNEB_AUTO_CALCULATE"] = "1"
		if args.show_recommendations:
			os.environ["TNEB_SHOW_RECOMMENDATIONS"] = "1"
		run_gui(storage=backend, db_path=db_path, csv_path=csv_path)


if __name__ == "__main__":
	main()


