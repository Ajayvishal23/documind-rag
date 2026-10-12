"""DocuMind — document intelligence workspace (multi-PDF RAG)."""

from documind.compat import ensure_modern_sqlite

ensure_modern_sqlite()  # must run before anything imports chromadb

__version__ = "2.1.0"
