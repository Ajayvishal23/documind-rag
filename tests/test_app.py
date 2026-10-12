"""Smoke-test the Streamlit UI headlessly with Streamlit's AppTest."""

from pathlib import Path

import pytest

st_testing = pytest.importorskip("streamlit.testing.v1")

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def _patch(monkeypatch, tmp_path):
    import documind.embeddings
    import documind.llm
    from conftest import HashEmbeddings, fake_llm

    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(tmp_path / "chroma"))
    monkeypatch.setenv("GROQ_API_KEY", "test")
    monkeypatch.setattr(documind.embeddings, "get_embeddings", lambda *a, **k: HashEmbeddings())
    monkeypatch.setattr(documind.llm, "build_llm", lambda *a, **k: fake_llm("Answer [1]."))
    import streamlit as st

    st.cache_resource.clear()


def test_app_renders_empty_state(monkeypatch, tmp_path):
    _patch(monkeypatch, tmp_path)
    at = st_testing.AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    assert any("Upload one or more PDFs" in i.value for i in at.info)
    assert at.chat_input[0] is not None


def test_chat_turn_shows_answer_and_citations(monkeypatch, tmp_path, solar_pdf):
    from conftest import HashEmbeddings
    from documind.config import get_settings
    from documind.pipeline import RAGPipeline

    _patch(monkeypatch, tmp_path)
    RAGPipeline(get_settings(), HashEmbeddings(), llm=None).ingest_pdf(solar_pdf, "solar.pdf")

    at = st_testing.AppTest.from_file(APP, default_timeout=60).run()
    at.chat_input[0].set_value("How efficient are solar panels?").run()
    assert not at.exception
    md = " ".join(m.value for m in at.markdown)
    assert "Answer [1]." in md
    assert "solar.pdf" in md  # citation chip
