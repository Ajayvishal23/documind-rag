"""Runtime compatibility shims.

ChromaDB requires SQLite >= 3.35. Some hosts (including Streamlit Community Cloud
and older Debian/Ubuntu images) ship an older system SQLite, which makes
``import chromadb`` fail at startup. When that happens we swap in the bundled
``pysqlite3-binary`` build. This must run before chromadb is imported.
"""

from __future__ import annotations

import sqlite3
import sys

MIN_SQLITE = (3, 35, 0)


def ensure_modern_sqlite() -> bool:
    """Replace the stdlib sqlite3 module if it is too old. Returns True if swapped."""
    if sqlite3.sqlite_version_info >= MIN_SQLITE:
        return False
    try:
        import pysqlite3  # type: ignore[import-not-found]
    except ImportError:
        return False  # chromadb will raise a clear error explaining the requirement
    sys.modules["sqlite3"] = pysqlite3
    return True
