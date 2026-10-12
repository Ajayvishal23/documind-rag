"""Headless UI tests for every page using Streamlit's AppTest."""

from pathlib import Path

import pytest

st_testing = pytest.importorskip("streamlit.testing.v1")

APP = str(Path(__file__).resolve().parents[1] / "app.py")


@pytest.fixture
def app_env(monkeypatch, tmp_path):
    import streamlit as st

    import documind.embeddings
    import documind.ui.state
    from conftest import HashEmbeddings, fake_llm

    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(tmp_path / "chroma"))
    monkeypatch.setenv("CHROMA_COLLECTION", "general")
    monkeypatch.setenv("GROQ_API_KEY", "test")
    monkeypatch.setenv("DOCUMIND_START_PAGE", "dashboard")
    monkeypatch.setattr(documind.embeddings, "get_embeddings", lambda *a, **k: HashEmbeddings())
    monkeypatch.setattr(documind.ui.state, "get_embeddings", lambda *a, **k: HashEmbeddings())
    monkeypatch.setattr(
        documind.ui.state, "build_llm", lambda *a, **k: fake_llm(*(["Panels are 18–22% efficient [1]."] * 5))
    )
    st.cache_resource.clear()
    return tmp_path


def _seed(pdf: bytes, name: str = "solar.pdf"):
    from conftest import HashEmbeddings
    from documind.activity import ActivityLog
    from documind.config import get_settings
    from documind.pipeline import RAGPipeline

    s = get_settings()
    rep = RAGPipeline(s, HashEmbeddings(), llm=None).ingest_pdf(pdf, name)
    ActivityLog(s.persist_dir.parent / "activity", "general").record("upload", name, f"{rep.pages} pages")


def _texts(at) -> str:
    html = " ".join(str(getattr(h, "proto", "")) for h in at.get("html"))
    md = " ".join(m.value for m in at.markdown)
    return html + " " + md


def _open(page: str):
    """Open a page. Function-based st.Page routes can't use AppTest.switch_page, so we
    set the app's configurable landing page instead."""
    import os

    os.environ["DOCUMIND_START_PAGE"] = page
    return st_testing.AppTest.from_file(APP, default_timeout=60).run()


@pytest.mark.parametrize("page", ["dashboard", "documents", "analysis", "activity", "settings"])
def test_every_page_renders_empty_workspace(app_env, page):
    at = _open(page)
    assert not at.exception, at.exception


@pytest.mark.parametrize("page", ["dashboard", "documents", "analysis", "activity", "settings"])
def test_every_page_renders_with_documents(app_env, solar_pdf, page):
    _seed(solar_pdf)
    at = _open(page)
    assert not at.exception, at.exception
    if page in {"dashboard", "documents"}:
        assert "solar.pdf" in _texts(at)


def test_analysis_produces_report_with_references(app_env, solar_pdf):
    _seed(solar_pdf)
    at = _open("analysis")
    at.text_area(key="question_box").set_value("How efficient are solar panels?")
    at.button[[b.label for b in at.button].index("Run analysis")].click()
    at.run()
    assert not at.exception, at.exception
    out = _texts(at)
    assert "dm-cite" in out  # styled citation marker in report card
    assert "Analysis 01" in out  # report card header
    assert "solar.pdf" in out and "Page 1" in out  # references panel
