# TNEB Meter Reading Manager

Desktop app to manage TNEB/TANGEDCO electricity meter readings (R/Y/B), calculate bi‑monthly bills with tariff slabs, and export reports to Excel.

## Features
- Clean Tkinter GUI for reading input and validation
- Bill calculation with slab breakdown and threshold warnings
- Results panel and rotation recommendations
- Exports: TANGEDCO format, summary, and detailed history (Excel/CSV)
- Storage: SQLite (default) or CSV, with backup/restore

## Quick start

Requirements: Python 3.8+ and Tk support.

Install dependencies:
```powershell
python -m pip install -r requirements.txt
```

Run the app:
```powershell
python main.py
```

## Build a Windows exe (PyInstaller)
A helper script builds a single-file exe:
```powershell
./build_exe.ps1
```
Output: `dist\tneb_manager.exe`

Notes:
- If `tkinter` is missing on Linux, install it via your package manager (e.g., `sudo apt-get install python3-tk`).
- If you add new resource folders, update `build_exe.ps1` to include them via `--add-data`.

## Project layout
```
models/   # billing logic and models
gui/      # Tkinter UI components
data/     # persistence, exports, and config helpers
main.py   # entrypoint
```

## Credits
See Help → About in the app. Credits are defined in `credits.py`.

## License
MIT — see `LICENSE`.

## Repository hygiene
This repo excludes build and runtime artifacts via `.gitignore`:
- `dist/`, `build/`, `*.spec`, `.venv/`, `__pycache__/`
- Runtime data under `data/` (DB, backups, CSVs, config)
