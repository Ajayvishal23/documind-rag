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
    monkeypatch.setattr(
        documind.ui.state, "available_models", lambda provider: ["llama-3.3-70b-versatile", "openai/gpt-oss-120b"]
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


def test_rejected_api_key_shows_actionable_message(app_env, solar_pdf, monkeypatch):
    from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

    import documind.ui.state

    class RejectingLLM(GenericFakeChatModel):
        def _stream(self, *a, **k):
            raise RuntimeError("Error code: 401 - {'error': {'message': 'Invalid API Key', 'code': 'invalid_api_key'}}")

        def _generate(self, *a, **k):
            raise RuntimeError("Error code: 401 - invalid_api_key")

    monkeypatch.setattr(documind.ui.state, "build_llm", lambda *a, **k: RejectingLLM(messages=iter([])))
    _seed(solar_pdf)
    at = _open("analysis")
    at.text_area(key="question_box").set_value("Summarise")
    at.button[[b.label for b in at.button].index("Run analysis")].click()
    at.run()
    assert not at.exception, at.exception
    out = _texts(at)
    assert "API key was rejected" in out and "GROQ_API_KEY" in out
    assert at.session_state["llm_auth_failed"] is True


def test_unavailable_model_falls_back_to_next(app_env, solar_pdf, monkeypatch):
    from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

    import documind.ui.state
    from conftest import fake_llm

    class Missing(GenericFakeChatModel):
        def _stream(self, *a, **k):
            raise RuntimeError(
                "Error code: 404 - The model `llama-3.3-70b-versatile` does not exist or you do not have access to it."
            )

    def build(settings, **_):
        if settings.llm_model == "llama-3.3-70b-versatile":
            return Missing(messages=iter([]))
        return fake_llm("Summary of the solar document [1].")

    monkeypatch.setattr(documind.ui.state, "build_llm", build)
    _seed(solar_pdf)
    at = _open("analysis")
    assert [s for s in at.selectbox if s.label == "Model"], "model picker should be shown"
    at.text_area(key="question_box").set_value("Summarise")
    at.button[[b.label for b in at.button].index("Run analysis")].click()
    at.run()
    assert not at.exception, at.exception
    report = at.session_state["reports"]["general"][0]
    assert report["model"] == "openai/gpt-oss-120b"
    assert report["fallback_from"] == ["llama-3.3-70b-versatile"]
    assert at.session_state["prefs"].model == "openai/gpt-oss-120b"
