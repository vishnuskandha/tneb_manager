# Contributing to tneb_manager

Thanks for your interest in contributing. This document covers the workflow,
code standards, and how to run the test suite.

## Getting started

1. Fork the repository and clone your fork.
2. Create a branch for your work:
   ```powershell
   git checkout -b feature/your-change
   ```
3. Set up a virtual environment and install dependencies:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements-dev.txt
   ```

## Running tests

```powershell
python -m pytest -q
```

The suite covers bill calculation, rotation recommendations, persistence across
storage backends, and Excel/CSV export. All tests should pass before you submit
a pull request.

## Code style

- Follow the existing style: 4-space indentation in `data/` and 4-space
  indentation with tabs in `main.py`/`models/`/`gui/` files. Match the style of
  the file you are editing.
- Keep functions focused and documented with docstrings where behavior is not
  obvious.
- Do not commit secrets, databases, backups, or generated configuration from
  `data/` (see `.gitignore`).

## Type hints

Code uses `from __future__ import annotations` and standard library type hints.
Use `Optional[X]` or `X | None` consistently with the surrounding file.

## Submitting changes

1. Run the test suite and make sure everything passes.
2. Commit with a concise, descriptive message.
3. Push your branch and open a pull request against `main` describing what
   changed and why.

## Build the Windows executable

See the README "Build a Windows exe" section for `build_exe.ps1` usage.
