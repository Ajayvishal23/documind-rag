"""Shared fixtures.

Tests run fully offline: a deterministic hashing embedder replaces
Sentence-Transformers and a scripted fake chat model replaces the LLM.
"""

from __future__ import annotations

import hashlib
import io
import math
import re
import sys
from pathlib import Path

import pytest
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from documind.config import Settings  # noqa: E402


class HashEmbeddings(Embeddings):
    """Bag-of-words hashing embedder — cheap, deterministic, semantically crude."""

    dim = 256

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * self.dim
        for tok in re.findall(r"[a-z0-9]+", text.lower()):
            v[int(hashlib.md5(tok.encode()).hexdigest(), 16) % self.dim] += 1.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)


def make_pdf(pages: list[str]) -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_font("Helvetica", size=11)
    for text in pages:
        pdf.add_page()
        pdf.multi_cell(0, 6, text)
    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()


def fake_llm(*replies: str) -> GenericFakeChatModel:
    return GenericFakeChatModel(messages=iter([AIMessage(content=r) for r in replies]))


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(persist_dir=tmp_path / "chroma", collection_name=f"test{abs(hash(tmp_path)) % 10**8}",
                    chunk_size=300, chunk_overlap=40, top_k=3, search_type="similarity")


@pytest.fixture
def embeddings() -> HashEmbeddings:
    return HashEmbeddings()


@pytest.fixture
def solar_pdf() -> bytes:
    return make_pdf([
        "Solar panels convert sunlight into electricity using photovoltaic cells. "
        "Typical residential panel efficiency is between 18 and 22 percent.",
        "The main limitation of solar power is intermittency: panels produce nothing at night "
        "and output drops on cloudy days, so battery storage is often required.",
    ])


@pytest.fixture
def wind_pdf() -> bytes:
    return make_pdf([
        "Wind turbines generate electricity from moving air. Offshore wind farms benefit from "
        "stronger and more consistent wind speeds than onshore sites.",
    ])
