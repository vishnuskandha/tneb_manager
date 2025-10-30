"""Persistence package for database and CSV storage backends.

Modules:
- config: Application-level configuration for storage.
- database_manager: Low-level SQLite operations.
- csv_manager: CSV import/export utilities.
- repository: Unified repository interfaces and implementations.
"""

from .config import AppConfig, load_config, save_config
from .repository import (
    DataRepository,
    SQLiteRepository,
    CSVRepository,
    MemoryRepository,
    create_repository,
)

__all__ = [
    "AppConfig",
    "load_config",
    "save_config",
    "DataRepository",
    "SQLiteRepository",
    "CSVRepository",
    "MemoryRepository",
    "create_repository",
]


