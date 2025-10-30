from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk, messagebox

from gui.main_window import MainWindow


class TNEBApp:
	"""Application bootstrap: styles, window, and lifecycle."""

	def __init__(self):
		self.root = tk.Tk()
		self.root.title("TNEB Meter Reading Manager")
		self._center_window(1000, 700)
		self.root.minsize(800, 600)
		self.setup_styles()

		self.main_window = None
		self.create_main_window()
		self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

	def _center_window(self, width: int, height: int) -> None:
		sw = self.root.winfo_screenwidth()
		sh = self.root.winfo_screenheight()
		x = int((sw - width) / 2)
		y = int((sh - height) / 2)
		self.root.geometry(f"{width}x{height}+{x}+{y}")

	def setup_styles(self) -> None:
		style = ttk.Style(self.root)
		# Use system default or 'clam' on Windows for a clean look
		try:
			style.theme_use("clam")
		except Exception:
			pass
		style.configure("TButton", padding=6)
		style.configure("Treeview", rowheight=22)

	def create_main_window(self) -> None:
		self.main_window = MainWindow(self.root)

	def run(self) -> None:
		try:
			self.root.mainloop()
		except Exception as exc:
			messagebox.showerror("Application Error", str(exc))

	def on_closing(self) -> None:
		try:
			# Attempt to gracefully close repository if available
			if self.main_window is not None:
				repo = getattr(self.main_window.manager, "repository", None)
				if repo is not None and hasattr(repo, "close"):
					try:
						repo.close()  # type: ignore[call-arg]
					except Exception:
						pass
		except Exception:
			pass
		self.root.destroy()


def main():
	app = TNEBApp()
	app.run()


if __name__ == "__main__":
	main()
