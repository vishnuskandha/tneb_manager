from __future__ import annotations

import datetime as _dt
from dataclasses import asdict
from typing import Optional, Callable, Dict, Any

import tkinter as tk
from tkinter import ttk, messagebox

try:
	from tkcalendar import DateEntry
	_HAS_TKCALENDAR = True
except Exception:
	# Fallback to simple Entry if tkcalendar not installed
	DateEntry = None  # type: ignore
	_HAS_TKCALENDAR = False


class ValidationMixin:
	"""Common validation helpers for entries and dates."""

	def parse_date(self, value: str) -> Optional[_dt.date]:
		try:
			day, month, year = [int(p) for p in value.strip().split("/")]
			return _dt.date(year, month, day)
		except Exception:
			return None

	def format_date(self, d: _dt.date) -> str:
		return d.strftime("%d/%m/%Y")

	def parse_number(self, value: str) -> Optional[float]:
		try:
			return float(value)
		except Exception:
			return None

	def set_entry_valid(self, entry: tk.Entry | ttk.Entry, valid: bool) -> None:
		try:
			entry.configure(foreground=("#155724" if valid else "#721c24"))
		except Exception:
			# Fallback: some ttk widgets may not support foreground directly
			pass

	def show_error(self, msg: str) -> None:
		messagebox.showerror("Input Error", msg)

	# Enhancements for formatting and color coding
	def format_currency(self, amount: float) -> str:
		try:
			from gui.config import get_gui_config
			return get_gui_config().format_currency(float(amount or 0.0))
		except Exception:
			return f"₹{float(amount or 0.0):.2f}"

	def format_units(self, units: float) -> str:
		try:
			from gui.config import get_gui_config
			return get_gui_config().format_units(float(units or 0.0))
		except Exception:
			return f"{float(units or 0.0):.1f} units"

	def threshold_color(self, consumption: float, threshold: float = 350.0) -> str:
		try:
			from gui.config import get_gui_config
			return get_gui_config().get_threshold_color(float(consumption or 0.0), threshold)
		except Exception:
			return "#28a745"


class DatePicker(ttk.Frame, ValidationMixin):
	"""Date input with optional calendar popup and validation (DD/MM/YYYY)."""

	def __init__(self, master: tk.Widget, *, value: Optional[_dt.date] = None):
		super().__init__(master)
		self._var = tk.StringVar()
		if _HAS_TKCALENDAR and DateEntry is not None:
			self._widget = DateEntry(self, date_pattern="dd/mm/yyyy")  # type: ignore[assignment]
			self._widget.pack(fill=tk.X, expand=True)
			if value:
				self.set_date(value)
		else:
			self._widget = ttk.Entry(self, textvariable=self._var)
			self._widget.pack(fill=tk.X, expand=True)
			if value:
				self._var.set(self.format_date(value))

	def get_date(self) -> Optional[_dt.date]:
		if _HAS_TKCALENDAR and hasattr(self._widget, "get_date"):
			try:
				return self._widget.get_date()  # type: ignore[return-value]
			except Exception:
				pass
		text = self._widget.get()
		return self.parse_date(text)

	def set_date(self, value: _dt.date) -> None:
		if _HAS_TKCALENDAR and hasattr(self._widget, "set_date"):
			self._widget.set_date(value)  # type: ignore[attr-defined]
		else:
			self._var.set(self.format_date(value))

	def validate_date(self) -> bool:
		ok = self.get_date() is not None
		self.set_entry_valid(self._widget, ok)
		return ok


class MeterInputFrame(ttk.Frame, ValidationMixin):
	"""Composite widget for a meter input: date, current reading, previous and consumption display."""

	def __init__(self, master: tk.Widget, *, meter_id: str, validate_reading: Callable[[str, float], bool], on_change: Optional[Callable[[str], None]] = None):
		super().__init__(master)
		self.meter_id = meter_id
		self._validate_reading_cb = validate_reading
		self._on_change_cb = on_change

		self.columnconfigure(1, weight=1)

		# Labels
		self.lbl_meter = ttk.Label(self, text=f"Meter {meter_id}", font=("Segoe UI", 10, "bold"))
		self.lbl_meter.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

		# Date
		self.lbl_date = ttk.Label(self, text="Date")
		self.lbl_date.grid(row=1, column=0, sticky="w")
		self.date_picker = DatePicker(self)
		self.date_picker.grid(row=1, column=1, sticky="ew", padx=(6, 0))

		# Current reading
		self.lbl_reading = ttk.Label(self, text="Reading")
		self.lbl_reading.grid(row=2, column=0, sticky="w", pady=(6, 0))
		self.var_reading = tk.StringVar()
		self.ent_reading = ttk.Entry(self, textvariable=self.var_reading)
		self.ent_reading.grid(row=2, column=1, sticky="ew", padx=(6, 0), pady=(6, 0))
		self.ent_reading.bind("<KeyRelease>", self._on_input_change)

		# Previous reading (display)
		self.lbl_prev = ttk.Label(self, text="Previous")
		self.lbl_prev.grid(row=3, column=0, sticky="w", pady=(6, 0))
		self.var_prev = tk.StringVar(value="-")
		self.ent_prev = ttk.Entry(self, textvariable=self.var_prev, state="readonly")
		self.ent_prev.grid(row=3, column=1, sticky="ew", padx=(6, 0), pady=(6, 0))

		# Consumption (diff)
		self.lbl_diff = ttk.Label(self, text="Diff")
		self.lbl_diff.grid(row=4, column=0, sticky="w", pady=(6, 0))
		self.var_diff = tk.StringVar(value="-")
		self.ent_diff = ttk.Entry(self, textvariable=self.var_diff, state="readonly")
		self.ent_diff.grid(row=4, column=1, sticky="ew", padx=(6, 0), pady=(6, 0))

	def _on_input_change(self, _event=None):
		self.validate_input()
		try:
			if callable(self._on_change_cb):
				self._on_change_cb(self.meter_id)
		except Exception:
			pass

	def get_reading_data(self) -> Dict[str, Any]:
		return {
			"meter_id": self.meter_id,
			"date": self.date_picker.get_date(),
			"reading": self.parse_number(self.var_reading.get()),
		}

	def set_previous_reading(self, value: Optional[float]) -> None:
		self.var_prev.set("-" if value is None else f"{value}")

	def clear_inputs(self) -> None:
		self.var_reading.set("")
		self.var_diff.set("-")

	def validate_input(self) -> bool:
		data = self.get_reading_data()
		ok_date = data["date"] is not None
		ok_num = data["reading"] is not None
		if ok_num:
			try:
				ok_num = self._validate_reading_cb(self.meter_id, float(data["reading"]))
			except Exception:
				ok_num = False
		self.date_picker.set_entry_valid(self.date_picker._widget, ok_date)
		self.set_entry_valid(self.ent_reading, ok_num)
		return ok_date and ok_num

	def update_diff(self, previous: Optional[float]) -> None:
		current = self.parse_number(self.var_reading.get())
		if current is None or previous is None:
			self.var_diff.set("-")
			return
		try:
			self.var_diff.set(f"{max(0.0, current - previous):.0f}")
		except Exception:
			self.var_diff.set("-")


class ReadingDisplayFrame(ttk.Frame):
	"""Scrollable table-like display for reading history: Date, Reading, Diff."""

	COLUMNS = ("date", "reading", "diff")

	def __init__(self, master: tk.Widget):
		super().__init__(master)
		self.tree = ttk.Treeview(self, columns=self.COLUMNS, show="headings", height=8)
		self.tree.heading("date", text="Date")
		self.tree.heading("reading", text="Reading")
		self.tree.heading("diff", text="Diff")
		self.tree.column("date", width=110, anchor="center")
		self.tree.column("reading", width=100, anchor="e")
		self.tree.column("diff", width=80, anchor="e")

		sb = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
		self.tree.configure(yscrollcommand=sb.set)
		self.tree.grid(row=0, column=0, sticky="nsew")
		sb.grid(row=0, column=1, sticky="ns")
		self.columnconfigure(0, weight=1)
		self.rowconfigure(0, weight=1)

	def clear_display(self) -> None:
		for iid in self.tree.get_children():
			self.tree.delete(iid)

	def add_reading_row(self, d: _dt.date, reading: float, diff: float) -> None:
		self.tree.insert("", tk.END, values=(d.strftime("%d/%m/%Y"), f"{reading}", f"{diff}"))

	def update_from_history(self, history: list) -> None:
		self.clear_display()
		def keyfunc(r):
			try:
				return getattr(r, "reading_date", r.get("reading_date"))
			except Exception:
				return None
		sorted_hist = sorted(history, key=keyfunc)
		for r in sorted_hist:
			try:
				if hasattr(r, "reading_date"):
					d = r.reading_date
					reading = r.current_reading
					diff = r.consumption
				else:
					d = r.get("reading_date")
					reading = r.get("current_reading")
					diff = r.get("consumption")
			except Exception:
				continue
			if isinstance(d, str):
				try:
					d = _dt.datetime.strptime(d, "%Y-%m-%d").date()
				except Exception:
					continue
			self.add_reading_row(d, reading, diff)


class BillDisplayFrame(ttk.Frame, ValidationMixin):
	"""Displays bill amount, marginal rate, and slab breakdown for a meter."""

	def __init__(self, master: tk.Widget, *, tariff_calculator, title: str = "Bill"):
		super().__init__(master)
		self.tariff_calculator = tariff_calculator
		self.columnconfigure(0, weight=1)

		self.lbl_title = ttk.Label(self, text=title, font=("Segoe UI", 10, "bold"))
		self.lbl_title.grid(row=0, column=0, sticky="w")

		self.var_amount = tk.StringVar(value="-")
		self.var_units = tk.StringVar(value="-")
		self.var_marginal = tk.StringVar(value="-")

		self.lbl_amount = ttk.Label(self, textvariable=self.var_amount, font=("Segoe UI", 12, "bold"))
		self.lbl_amount.grid(row=1, column=0, sticky="w", pady=(4, 2))

		self.lbl_units = ttk.Label(self, textvariable=self.var_units)
		self.lbl_units.grid(row=2, column=0, sticky="w")

		self.lbl_marginal = ttk.Label(self, textvariable=self.var_marginal)
		self.lbl_marginal.grid(row=3, column=0, sticky="w", pady=(0, 6))

		self.tree = ttk.Treeview(self, columns=("range", "units", "rate", "cost"), show="headings", height=5)
		for col, text in [("range", "Tariff Slab"), ("units", "Units"), ("rate", "Rate"), ("cost", "Cost")]:
			self.tree.heading(col, text=text)
			self.tree.column(col, anchor="e", width=100)
		self.tree.column("range", anchor="w", width=160)
		self.tree.grid(row=4, column=0, sticky="nsew")
		self.rowconfigure(4, weight=1)

	def update_display(self, consumption: float) -> None:
		units = float(consumption or 0.0)
		amount = float(self.tariff_calculator.calculate_bill(units))
		marginal = float(self.tariff_calculator.get_marginal_rate(units))
		self.var_amount.set(f"Amount: {self.format_currency(amount)}")
		self.var_units.set(f"Consumption: {self.format_units(units)}")
		self.var_marginal.set(f"Next unit rate: {self.format_currency(marginal)}")
		try:
			color = self.threshold_color(units)
			self.lbl_amount.configure(foreground=color)
		except Exception:
			pass
		for iid in self.tree.get_children():
			self.tree.delete(iid)
		for row in self.tariff_calculator.get_slab_breakdown(units):
			start = int(row["from"]) if isinstance(row["from"], float) else row["from"]
			end = "∞" if row["to"] == float("inf") else int(row["to"])
			range_text = f"{start}-{end}"
			self.tree.insert("", tk.END, values=(range_text, f"{row['units']:.1f}", f"{self.format_currency(row['rate'])}", f"{self.format_currency(row['cost'])}"))


class RotationRecommendationFrame(ttk.Frame, ValidationMixin):
	"""Displays rotation suggestions and economics."""

	def __init__(self, master: tk.Widget):
		super().__init__(master)
		self.columnconfigure(0, weight=1)
		self.var_title = tk.StringVar(value="Rotation Recommendations")
		self.lbl_title = ttk.Label(self, textvariable=self.var_title, font=("Segoe UI", 10, "bold"))
		self.lbl_title.grid(row=0, column=0, sticky="w")
		self.txt = tk.Text(self, height=8, wrap="word")
		self.txt.grid(row=1, column=0, sticky="nsew", pady=(4, 0))
		self.rowconfigure(1, weight=1)

	def set_recommendations(self, rec: dict) -> None:
		self.txt.delete("1.0", tk.END)
		if not rec:
			self.txt.insert(tk.END, "No data available")
			return
		appr = rec.get("approaching", [])
		suggestions = rec.get("suggestions", [])
		econ = rec.get("economics", {})
		if appr:
			self.txt.insert(tk.END, f"Approaching threshold: {', '.join(appr)}\n")
		for s in suggestions:
			self.txt.insert(tk.END, f"- {s}\n")
		if econ:
			self.txt.insert(tk.END, f"Combined: {self.format_currency(econ.get('combined_bill', 0))}\n")
			self.txt.insert(tk.END, f"Separate: {self.format_currency(econ.get('separate_bill', 0))}\n")
			self.txt.insert(tk.END, f"Potential savings: {self.format_currency(econ.get('potential_savings', 0))}\n")


class ThresholdWarningWidget(ttk.Frame, ValidationMixin):
	"""Simple color-coded threshold indicator for a meter."""

	def __init__(self, master: tk.Widget, *, threshold: float = 350.0):
		super().__init__(master)
		self.threshold = threshold
		self.var = tk.StringVar(value="Threshold status: safe")
		self.lbl = ttk.Label(self, textvariable=self.var, font=("Segoe UI", 9, "bold"))
		self.lbl.pack(side=tk.LEFT, anchor="w")

	def update_status(self, consumption: float) -> None:
		units = float(consumption or 0.0)
		color = self.threshold_color(units, self.threshold)
		status = "safe"
		# Align with MeterReading.is_approaching_limit (>= 90% threshold) and critical at >= threshold
		try:
			if units >= self.threshold:
				status = "critical"
			elif units >= 0.9 * self.threshold:
				status = "approaching"
		except Exception:
			pass
		self.var.set(f"Threshold status: {status}")
		try:
			self.lbl.configure(foreground=color)
		except Exception:
			pass


class SummaryPanel(ttk.Frame, ValidationMixin):
	"""Shows overall consumption, total bill, and per-meter quick status."""

	def __init__(self, master: tk.Widget):
		super().__init__(master)
		self.columnconfigure(0, weight=1)
		self.lbl_title = ttk.Label(self, text="Summary", font=("Segoe UI", 12, "bold"))
		self.lbl_title.grid(row=0, column=0, sticky="w")

		self.var_total_units = tk.StringVar(value="-")
		self.var_total_cost = tk.StringVar(value="-")
		lbl_units = ttk.Label(self, textvariable=self.var_total_units)
		lbl_cost = ttk.Label(self, textvariable=self.var_total_cost, font=("Segoe UI", 10, "bold"))
		lbl_units.grid(row=1, column=0, sticky="w")
		lbl_cost.grid(row=2, column=0, sticky="w", pady=(0, 6))

		self.tree = ttk.Treeview(self, columns=("meter", "units", "cost", "status"), show="headings", height=6)
		for col, text in [("meter", "Meter"), ("units", "Units"), ("cost", "Cost"), ("status", "Status")]:
			self.tree.heading(col, text=text)
			self.tree.column(col, anchor="center", width=120)
		self.tree.column("meter", anchor="w", width=140)
		self.tree.grid(row=3, column=0, sticky="nsew")
		self.rowconfigure(3, weight=1)

	def set_summary(self, summary: dict) -> None:
		self.var_total_units.set(f"Total: {self.format_units(summary.get('total_units', 0.0))}")
		self.var_total_cost.set(f"Total Bill: {self.format_currency(summary.get('total_cost', 0.0))}")
		for iid in self.tree.get_children():
			self.tree.delete(iid)
		per_units = summary.get("per_meter_units", {})
		per_cost = summary.get("per_meter_cost", {})
		try:
			from gui.bill_utils import ThresholdMonitor
			threshold = float(summary.get("rotation_economics", {}).get("threshold", 350.0))
		except Exception:
			threshold = 350.0
		for m_id, units in per_units.items():
			units_f = float(units or 0.0)
			# Determine status label
			warn_label = "safe"
			if units_f >= threshold:
				warn_label = "critical"
			elif units_f >= 0.9 * threshold:
				warn_label = "approaching"
			self.tree.insert("", tk.END, values=(m_id, f"{units_f:.1f}", self.format_currency(per_cost.get(m_id, 0.0)), warn_label))


class ResultsPanel(ttk.Frame, ValidationMixin):
	"""Consolidated results view with multiple sub-tabs.

	Tabs: Overview, Detailed Bills, Rotation Analysis, Historical Trends
	"""

	def __init__(self, master: tk.Widget, *, meter_manager):
		super().__init__(master)
		self.manager = meter_manager
		self.columnconfigure(0, weight=1)
		self.rowconfigure(0, weight=1)

		self.nb = ttk.Notebook(self)
		self.nb.grid(row=0, column=0, sticky="nsew")

		self._build_overview_tab()
		self._build_detailed_bills_tab()
		self._build_rotation_analysis_tab()
		self._build_historical_trends_tab()

	def _build_overview_tab(self) -> None:
		frame = ttk.Frame(self.nb)
		frame.columnconfigure(0, weight=1)
		frame.rowconfigure(1, weight=1)
		self.nb.add(frame, text="Overview")

		self.ov_title = ttk.Label(frame, text="Overview", font=("Segoe UI", 12, "bold"))
		self.ov_title.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 6))

		self.ov_totals = ttk.Label(frame, text="-", font=("Segoe UI", 10, "bold"))
		self.ov_totals.grid(row=0, column=1, sticky="e", padx=10, pady=(10, 6))

		cols = ("meter", "reading", "units", "bill", "status")
		self.ov_tree = ttk.Treeview(frame, columns=cols, show="headings", height=8)
		for c, text in [("meter", "Meter"), ("reading", "Current"), ("units", "Consumption"), ("bill", "Bill"), ("status", "Status")]:
			self.ov_tree.heading(c, text=text)
			self.ov_tree.column(c, width=120, anchor=("w" if c == "meter" else "e"))
		self.ov_tree.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=(0, 10))

	def _build_detailed_bills_tab(self) -> None:
		frame = ttk.Frame(self.nb)
		frame.columnconfigure(0, weight=1)
		frame.rowconfigure(1, weight=1)
		self.nb.add(frame, text="Detailed Bills")

		self.db_container = ttk.Frame(frame)
		self.db_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
		self.db_container.columnconfigure(0, weight=1)

		# One BillDisplayFrame per meter
		self.db_bill_frames = {}
		row = 0
		for meter_id in self.manager.meters.keys():
			lbl = ttk.Label(self.db_container, text=f"Meter {meter_id}", font=("Segoe UI", 10, "bold"))
			lbl.grid(row=row, column=0, sticky="w", pady=(0, 2))
			row += 1
			bill = BillDisplayFrame(self.db_container, tariff_calculator=self.manager.tariff_calculator, title="Bill")
			bill.grid(row=row, column=0, sticky="nsew", pady=(0, 10))
			self.db_bill_frames[meter_id] = bill
			row += 1

	def _build_rotation_analysis_tab(self) -> None:
		frame = ttk.Frame(self.nb)
		frame.columnconfigure(0, weight=1)
		frame.rowconfigure(1, weight=1)
		self.nb.add(frame, text="Rotation Analysis")

		self.ra_frame = RotationRecommendationFrame(frame)
		self.ra_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

	def _build_historical_trends_tab(self) -> None:
		frame = ttk.Frame(self.nb)
		frame.columnconfigure(0, weight=1)
		frame.rowconfigure(0, weight=1)
		self.nb.add(frame, text="Historical Trends")

		self.hist_tables = {}
		container = ttk.Frame(frame)
		container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
		for meter_id in self.manager.meters.keys():
			grp = ttk.LabelFrame(container, text=f"Meter {meter_id}")
			grp.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
			table = ReadingDisplayFrame(grp)
			table.pack(fill=tk.BOTH, expand=True)
			self.hist_tables[meter_id] = table

	def refresh(self) -> None:
		# Overview
		try:
			latest = self.manager.get_latest_readings()
			summary = self.manager.get_consumption_summary()
			for iid in self.ov_tree.get_children():
				self.ov_tree.delete(iid)
			per_units = summary.get("per_meter_units", {})
			per_cost = summary.get("per_meter_cost", {})
			for m_id in self.manager.meters.keys():
				latest_r = latest.get(m_id)
				current = "-" if latest_r is None else f"{latest_r.current_reading}"
				units = 0.0 if latest_r is None else float(latest_r.consumption)
				status = "safe"
				try:
					from gui.config import get_gui_config
					thr = float(get_gui_config().config["thresholds"]["rotation_threshold"])  # type: ignore[index]
					if units >= thr:
						status = "critical"
					elif units >= 0.9 * thr:
						status = "approaching"
				except Exception:
					pass
				self.ov_tree.insert("", tk.END, values=(m_id, current, f"{units:.1f}", self.format_currency(per_cost.get(m_id, 0.0)), status))
			self.ov_totals.configure(text=f"Total: {self.format_units(summary.get('total_units', 0.0))} | {self.format_currency(summary.get('total_cost', 0.0))}")
		except Exception:
			pass

		# Detailed bills
		try:
			latest = self.manager.get_latest_readings()
			for m_id, bill in self.db_bill_frames.items():
				units = 0.0 if latest.get(m_id) is None else float(latest[m_id].consumption)
				bill.update_display(units)
		except Exception:
			pass

		# Rotation analysis
		try:
			from gui.config import get_gui_config
			thr = float(get_gui_config().config["thresholds"]["rotation_threshold"])  # type: ignore[index]
			rec = self.manager.recommend_rotation(threshold=thr)
			self.ra_frame.set_recommendations(rec)
		except Exception:
			pass

		# Historical trends
		try:
			for m_id, table in self.hist_tables.items():
				hist = [r for r in self.manager.reading_history if r.meter_id == m_id]
				table.update_from_history(hist)
		except Exception:
			pass