"""Centralised, environment-driven configuration.

Every tunable lives here so the rest of the codebase never reads ``os.environ``
directly. Values can be set in a ``.env`` file, real environment variables, or
Streamlit secrets (copied into the environment by ``app.py``).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:  # optional dependency – fine to run without it
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass


def _env(key: str, default: str) -> str:
    return os.getenv(key, default)


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    """Immutable application settings."""

    # --- Storage -----------------------------------------------------------
    persist_dir: Path = field(default_factory=lambda: Path(_env("CHROMA_PERSIST_DIR", "./data/chroma")))
    collection_name: str = field(default_factory=lambda: _env("CHROMA_COLLECTION", "documind"))

    # --- Embeddings --------------------------------------------------------
    embedding_model: str = field(
        default_factory=lambda: _env("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    )
    embedding_device: str = field(default_factory=lambda: _env("EMBEDDING_DEVICE", "cpu"))

    # --- Chunking ----------------------------------------------------------
    chunk_size: int = field(default_factory=lambda: _env_int("CHUNK_SIZE", 1000))
    chunk_overlap: int = field(default_factory=lambda: _env_int("CHUNK_OVERLAP", 150))

    # --- Retrieval ---------------------------------------------------------
    top_k: int = field(default_factory=lambda: _env_int("TOP_K", 5))
    search_type: str = field(default_factory=lambda: _env("SEARCH_TYPE", "mmr"))  # "mmr" | "similarity"
    fetch_k: int = field(default_factory=lambda: _env_int("FETCH_K", 20))
    score_threshold: float = field(default_factory=lambda: _env_float("SCORE_THRESHOLD", 0.0))

    # --- LLM ---------------------------------------------------------------
    llm_provider: str = field(default_factory=lambda: _env("LLM_PROVIDER", "groq").lower())
    llm_model: str = field(default_factory=lambda: _env("LLM_MODEL", ""))
    llm_temperature: float = field(default_factory=lambda: _env_float("LLM_TEMPERATURE", 0.1))
    ollama_base_url: str = field(default_factory=lambda: _env("OLLAMA_BASE_URL", "http://localhost:11434"))

    # --- Memory ------------------------------------------------------------
    memory_window: int = field(default_factory=lambda: _env_int("MEMORY_WINDOW", 6))  # turns kept

    # --- Upload limits -----------------------------------------------------
    max_file_mb: int = field(default_factory=lambda: _env_int("MAX_FILE_MB", 50))

    def __post_init__(self) -> None:
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
        if self.search_type not in {"mmr", "similarity"}:
            raise ValueError("SEARCH_TYPE must be 'mmr' or 'similarity'")


DEFAULT_MODELS: dict[str, str] = {
    "groq": "llama-3.3-70b-versatile",
    "openai": "gpt-4o-mini",
    "ollama": "llama3.2",
}


def get_settings() -> Settings:
    """Return a fresh settings object (cheap; reads the environment)."""
    return Settings()
