from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Optional
from datetime import date
import os

from models import MeterManager
from gui.widgets import MeterInputFrame, ReadingDisplayFrame, BillDisplayFrame, RotationRecommendationFrame, ThresholdWarningWidget, SummaryPanel, ResultsPanel
from gui.bill_utils import get_overall_summary
from credits import get_credits
from gui.config import get_gui_config


class MainWindow(ttk.Frame):
	"""Primary GUI window with tabs for each meter (R, Y, B)."""

	def __init__(self, master: tk.Tk):
		super().__init__(master)
		self.master = master
		self.pack(fill=tk.BOTH, expand=True)

		self.manager = MeterManager()
		self.gui_cfg = get_gui_config()
		self.auto_calculate = os.environ.get("TNEB_AUTO_CALCULATE") == "1"
		self.show_recommendations = os.environ.get("TNEB_SHOW_RECOMMENDATIONS") == "1"
		self.gui_cfg = get_gui_config()

		self._build_menu()
		self._build_statusbar()
		self._build_tabs()
		self.refresh_displays()

	def _build_menu(self):
		menubar = tk.Menu(self.master)
		file_menu = tk.Menu(menubar, tearoff=0)
		file_menu.add_command(label="Exit", command=self.master.destroy)
		menubar.add_cascade(label="File", menu=file_menu)

		view_menu = tk.Menu(menubar, tearoff=0)
		# Placeholder for future view options
		menubar.add_cascade(label="View", menu=view_menu)

		export_menu = tk.Menu(menubar, tearoff=0)
		export_menu.add_command(label="Export to Excel (TANGEDCO Format)", command=self.on_export_tangedco, accelerator="Ctrl+E")
		export_menu.add_command(label="Export Summary Report", command=self.on_export_summary)
		export_menu.add_command(label="Export Detailed History", command=self.on_export_detailed)

		export_menu.add_separator()
		export_menu.add_command(label="Export All (Multi-sheet)", command=self.on_export_all)
		menubar.add_cascade(label="Export", menu=export_menu)

		help_menu = tk.Menu(menubar, tearoff=0)
		help_menu.add_command(label="About", command=lambda: messagebox.showinfo("About", get_credits()))
		menubar.add_cascade(label="Help", menu=help_menu)

		self.master.config(menu=menubar)

	def _build_statusbar(self):
		self.status_var = tk.StringVar(value="Ready")
		bar = ttk.Label(self, textvariable=self.status_var, anchor="w")
		bar.pack(side=tk.BOTTOM, fill=tk.X)

	def _build_tabs(self):
		nb = ttk.Notebook(self)
		nb.pack(fill=tk.BOTH, expand=True)
		nb.bind("<<NotebookTabChanged>>", self.on_tab_changed)

		self.tab_to_widgets: Dict[str, Dict[str, object]] = {}

		for meter_id in self.manager.meters.keys():
			frame = ttk.Frame(nb)
			nb.add(frame, text=meter_id)

			frame.columnconfigure(0, weight=1)
			frame.rowconfigure(2, weight=1)

			# Header with threshold warning
			header = ttk.Frame(frame)
			header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 4))
			header.columnconfigure(0, weight=1)
			lbl = ttk.Label(header, text=f"Meter {meter_id}", font=("Segoe UI", 12, "bold"))
			lbl.grid(row=0, column=0, sticky="w")
			tw = ThresholdWarningWidget(header, threshold=float(self.gui_cfg.config["thresholds"]["rotation_threshold"]))
			tw.grid(row=0, column=1, sticky="e")

			# Input area (left)
			mi = MeterInputFrame(frame, meter_id=meter_id, validate_reading=self._validate_reading, on_change=(self._on_input_change if self.auto_calculate else None))
			mi.grid(row=1, column=0, sticky="ew", padx=10)

			# Reading table (left, grows)
			rd = ReadingDisplayFrame(frame)
			rd.grid(row=2, column=0, sticky="nsew", padx=10, pady=(8, 10))

			# Bill display (right column)
			bill = BillDisplayFrame(frame, tariff_calculator=self.manager.tariff_calculator, title="Bill")
			bill.grid(row=1, column=1, rowspan=2, sticky="nsew", padx=(0, 10), pady=(0, 10))
			frame.columnconfigure(1, weight=1)

			# Buttons
			btns = ttk.Frame(frame)
			btns.grid(row=3, column=0, sticky="e", padx=10, pady=(0, 10))
			btn_calc = ttk.Button(btns, text="Calculate", command=lambda m=meter_id: self.on_calculate(m))
			btn_save = ttk.Button(btns, text="Save Reading", command=lambda m=meter_id: self.on_save_reading(m))
			btn_clear = ttk.Button(btns, text="Clear", command=lambda m=meter_id: self.on_clear(m))
			btn_calc.grid(row=0, column=0, padx=4)
			btn_save.grid(row=0, column=1, padx=4)
			btn_clear.grid(row=0, column=2, padx=4)

			self.tab_to_widgets[meter_id] = {
				"input": mi,
				"display": rd,
				"bill": bill,
				"threshold": tw,
			}

		# Summary tab
		summary_tab = ttk.Frame(nb)
		nb.add(summary_tab, text="Summary")
		summary_tab.rowconfigure(1, weight=1)
		summary_tab.columnconfigure(0, weight=1)
		summary_tab.columnconfigure(1, weight=1)
		sp = SummaryPanel(summary_tab)
		sp.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 6))
		rr = RotationRecommendationFrame(summary_tab)
		if self.show_recommendations:
			rr.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=(0, 10))
		self.summary_panel = sp
		self.rotation_frame = rr

		self.notebook = nb

		# Results tab after Summary
		results_tab = ttk.Frame(nb)
		nb.add(results_tab, text="Results")
		results_tab.rowconfigure(0, weight=1)
		results_tab.columnconfigure(0, weight=1)
		self.results_panel = ResultsPanel(results_tab, meter_manager=self.manager)
		self.results_panel.grid(row=0, column=0, sticky="nsew")

		# Keyboard shortcuts
		self.master.bind_all("<Control-e>", lambda _e: self.on_export_tangedco())
		self.master.bind_all("<Control-r>", lambda _e: self.refresh_results_panel())
		self.master.bind_all("<F5>", lambda _e: self.refresh_displays())

	def _validate_reading(self, meter_id: str, reading: float) -> bool:
		try:
			ok, _ = self.manager.validate_reading(meter_id, reading)
			return bool(ok)
		except Exception:
			return False

	def on_tab_changed(self, _event=None):
		self.refresh_displays()

	def _get_latest_prev(self, meter_id: str) -> Optional[float]:
		latest_map = self.manager.get_latest_readings()
		prev = latest_map.get(meter_id)
		return prev.current_reading if prev else None

	def refresh_displays(self):
		try:
			latest_map = self.manager.get_latest_readings()
			for meter_id, widgets in self.tab_to_widgets.items():
				mi: MeterInputFrame = widgets["input"]  # type: ignore[assignment]
				rd: ReadingDisplayFrame = widgets["display"]  # type: ignore[assignment]
				bill: BillDisplayFrame = widgets.get("bill")  # type: ignore[assignment]
				tw: ThresholdWarningWidget = widgets.get("threshold")  # type: ignore[assignment]
				latest = latest_map.get(meter_id)
				latest_prev = None if latest is None else latest.previous_reading
				mi.set_previous_reading(latest_prev)
				hist = [r for r in self.manager.reading_history if r.meter_id == meter_id]
				rd.update_from_history(hist)
				mi.update_diff(latest_prev)
				# Update bill/threshold using latest consumption
				units = 0.0 if latest is None else latest.consumption
				if bill:
					bill.update_display(units)
				if tw:
					tw.update_status(units)
			# Update summary and rotation recommendations
			summary = get_overall_summary(self.manager)
			self.summary_panel.set_summary(summary)
			if self.show_recommendations:
				self.rotation_frame.set_recommendations(self.manager.recommend_rotation(threshold=float(self.gui_cfg.config["thresholds"]["rotation_threshold"])) )
			self.status_var.set("Displays refreshed")
			self.refresh_results_panel()
		except Exception as exc:
			messagebox.showerror("Error", f"Failed to refresh displays: {exc}")

	def refresh_results_panel(self) -> None:
		try:
			if hasattr(self, "results_panel") and self.results_panel is not None:
				self.results_panel.refresh()
				self.status_var.set("Results updated")
		except Exception:
			pass

	def _asksave(self, title: str, defaultext: str = ".xlsx") -> Optional[str]:
		try:
			from tkinter import filedialog
			from datetime import datetime
			default_name = f"TNEB_{datetime.now().strftime('%Y%m%d_%H%M')}" + defaultext
			return filedialog.asksaveasfilename(title=title, defaultextension=defaultext, filetypes=[("Excel", ".xlsx"), ("CSV", ".csv")], initialfile=default_name)
		except Exception:
			return None

	def on_export_tangedco(self):
		path = self._asksave("Export to Excel (TANGEDCO Format)")
		if not path:
			return
		self.status_var.set("Exporting...")
		self.update_idletasks()
		try:
			from data.excel_exporter import ExcelExporter
			exporter = ExcelExporter()
			exporter.export_tangedco_format(path, self.manager)
			messagebox.showinfo("Export", f"Exported to {path}")
			self.status_var.set("Export complete")
		except Exception as exc:
			messagebox.showerror("Export Failed", f"Could not export: {exc}")
			self.status_var.set("Export failed")

	def on_export_summary(self):
		path = self._asksave("Export Summary Report")
		if not path:
			return
		self.status_var.set("Exporting summary...")
		self.update_idletasks()
		try:
			from data.excel_exporter import ExcelExporter
			exporter = ExcelExporter()
			exporter.export_summary_report(path, self.manager)
			messagebox.showinfo("Export", f"Summary exported to {path}")
			self.status_var.set("Export complete")
		except Exception as exc:
			messagebox.showerror("Export Failed", f"Could not export summary: {exc}")
			self.status_var.set("Export failed")

	def on_export_detailed(self):
		path = self._asksave("Export Detailed History")
		if not path:
			return
		self.status_var.set("Exporting detailed history...")
		self.update_idletasks()
		try:
			from data.excel_exporter import ExcelExporter
			exporter = ExcelExporter()
			exporter.export_detailed_history(path, self.manager)
			messagebox.showinfo("Export", f"Detailed history exported to {path}")
			self.status_var.set("Export complete")
		except Exception as exc:
			messagebox.showerror("Export Failed", f"Could not export detailed history: {exc}")
			self.status_var.set("Export failed")

	def on_export_all(self):
		path = self._asksave("Export All (Multi-sheet)")
		if not path:
			return
		self.status_var.set("Exporting all...")
		self.update_idletasks()
		try:
			from data.excel_exporter import ExcelExporter
			exporter = ExcelExporter()
			exporter.create_workbook_with_multiple_sheets(path, self.manager)
			messagebox.showinfo("Export", f"All data exported to {path}")
			self.status_var.set("Export complete")
		except Exception as exc:
			messagebox.showerror("Export Failed", f"Could not export all: {exc}")
			self.status_var.set("Export failed")

	def _on_input_change(self, meter_id: str) -> None:
		try:
			widgets = self.tab_to_widgets.get(meter_id)
			if not widgets:
				return
			mi: MeterInputFrame = widgets["input"]  # type: ignore[assignment]
			bill: BillDisplayFrame = widgets.get("bill")  # type: ignore[assignment]
			tw: ThresholdWarningWidget = widgets.get("threshold")  # type: ignore[assignment]
			prev = self._get_latest_prev(meter_id) or 0.0
			current = mi.parse_number(mi.var_reading.get()) or 0.0
			units = max(0.0, current - prev)
			if bill:
				bill.update_display(units)
			if tw:
				tw.update_status(units)
		except Exception:
			pass

	def on_calculate(self, meter_id: str):
		widgets = self.tab_to_widgets[meter_id]
		mi: MeterInputFrame = widgets["input"]  # type: ignore[assignment]
		if not mi.validate_input():
			self.status_var.set("Invalid input")
			return
		prev = self._get_latest_prev(meter_id) or 0.0
		current = mi.parse_number(mi.var_reading.get()) or 0.0
		units = max(0.0, current - prev)
		mi.update_diff(prev)
		cost = self.manager.tariff_calculator.calculate_bill(units)
		self.status_var.set(f"Calculated: {units:.0f} units -> ₹{cost:.2f}")
		# Update bill and threshold immediately
		bill: BillDisplayFrame = widgets.get("bill")  # type: ignore[assignment]
		if bill:
			bill.update_display(units)
		tw: ThresholdWarningWidget = widgets.get("threshold")  # type: ignore[assignment]
		if tw:
			tw.update_status(units)

	def on_save_reading(self, meter_id: str):
		widgets = self.tab_to_widgets[meter_id]
		mi: MeterInputFrame = widgets["input"]  # type: ignore[assignment]
		data = mi.get_reading_data()
		if not mi.validate_input() or data["date"] is None or data["reading"] is None:
			messagebox.showwarning("Validation", "Please enter a valid date and reading")
			return
		try:
			reading_obj = self.manager.add_reading(meter_id, data["date"], float(data["reading"]))
			self.refresh_displays()
			mi.clear_inputs()
			self.status_var.set(f"Saved reading for meter {meter_id}")
		except Exception as exc:
			messagebox.showerror("Save Failed", f"Could not save reading: {exc}")

	def on_clear(self, meter_id: str):
		widgets = self.tab_to_widgets[meter_id]
		mi: MeterInputFrame = widgets["input"]  # type: ignore[assignment]
		mi.clear_inputs()
		self.status_var.set("Cleared inputs")

	# New helper methods (stubs for future expansion)
	def update_bill_displays(self) -> None:
		self.refresh_displays()

	def update_rotation_recommendations(self) -> None:
		self.refresh_displays()

	def check_threshold_warnings(self) -> None:
		self.refresh_displays()

	def show_tariff_breakdown(self) -> None:
		self.refresh_displays()
