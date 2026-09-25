# TNEB Meter Reading Manager


<!-- README polish: repository metadata badges -->
<p>
  <a href="https://github.com/vishnuskandha/tneb_manager"><img alt="GitHub stars" src="https://img.shields.io/github/stars/vishnuskandha/tneb_manager?style=for-the-badge&logo=github&label=Stars"></a>
  <a href="https://github.com/vishnuskandha/tneb_manager/fork"><img alt="GitHub forks" src="https://img.shields.io/github/forks/vishnuskandha/tneb_manager?style=for-the-badge&logo=github&label=Forks"></a>
  <a href="https://github.com/vishnuskandha/tneb_manager/issues"><img alt="GitHub issues" src="https://img.shields.io/github/issues/vishnuskandha/tneb_manager?style=for-the-badge&logo=github&label=Issues"></a>
  <a href="https://github.com/vishnuskandha/tneb_manager/commits"><img alt="Last commit" src="https://img.shields.io/github/last-commit/vishnuskandha/tneb_manager?style=for-the-badge&logo=git&label=Updated"></a>
</p>
<!-- End README polish -->

[![CI](https://github.com/vishnuskandha/tneb_manager/actions/workflows/ci.yml/badge.svg)](https://github.com/vishnuskandha/tneb_manager/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A desktop application to manage TNEB/TANGEDCO electricity meter readings for the three-meter (R/Y/B) residential setup. It records readings across billing cycles, calculates bi-monthly bills using the current TNEB tariff slabs, recommends load rotation to stay under higher slab rates, and exports reports in the official TANGEDCO Excel format.

## Features

- **Tkinter GUI** for entering and validating meter readings (R, Y, B) with a date picker.
- **Slab-based bill calculation** with a per-meter tariff breakdown and marginal-rate tracking.
- **Rotation recommendations** that flag meters approaching the slab threshold and estimate combined vs. separate billing economics.
- **Reports and exports**: TANGEDCO-format Excel workbook, summary report, and detailed history in XLSX or CSV.
- **Flexible storage**: SQLite (default), CSV, or in-memory, with backup/restore and migration between backends.
- **CLI mode** for scripted use: reading demo, exports, backups, restores, and storage migration all available from `main.py --cli`.

## Screenshots

Screenshots are not currently included. To add some, capture the main window and results panel and place the images under a `docs/` or `screenshots/` folder, then link them here.

## Requirements

- Python 3.8+ with Tk support (see [build notes](#build-a-windows-exe-pyinstaller) for Tk on Linux).
- Dependencies listed in `requirements.txt`.

## Quick start

Run from source:

```powershell
python -m pip install -r requirements.txt
python main.py
```

Run the CLI demo instead of the GUI:

```powershell
python main.py --cli
```

## Running tests

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

## Build a Windows exe (PyInstaller)

The `build_exe.ps1` helper creates a virtual environment, installs dependencies plus PyInstaller, and produces a single-file, windowed executable:

```powershell
./build_exe.ps1
```

Output: `dist\tneb_manager.exe`

Notes:

- If `tkinter` is missing on Linux, install it via your package manager (e.g., `sudo apt-get install python3-tk`).
- If you add new resource folders, update `build_exe.ps1` to include them via `--add-data`.

## Project layout

```
main.py                 # Entry point (GUI + CLI)
models/                 # Billing logic, tariff calculator, and meter models
gui/                    # Tkinter UI components (main window, widgets, bill utils)
data/                   # Persistence (SQLite/CSV), Excel export, and config helpers
test_*.py               # pytest test suite (bill calc, persistence, export)
```

## Storage and runtime data

Runtime artifacts (database, CSV backups, and generated config) live under `data/` and are excluded from version control via `.gitignore`. The app writes:

- `data/tneb_readings.db` — default SQLite database
- `data/backups/` — CSV backups
- `data/config.json` — generated configuration

## Credits

Credits are shown in Help -> About in the app and are defined in `credits.py`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and the [Security Policy](SECURITY.md).

## License

MIT — see [LICENSE](LICENSE).
