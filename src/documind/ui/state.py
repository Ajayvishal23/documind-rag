"""Session state, cached resources and cross-page navigation helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

import streamlit as st

from documind.activity import ActivityLog
from documind.config import DEFAULT_MODELS, Settings, get_settings
from documind.embeddings import get_embeddings
from documind.llm import LLMConfigError, build_llm
from documind.memory import ConversationMemory
from documind.pipeline import RAGPipeline
from documind.vectorstore import list_workspaces

PAGES: dict[str, st.Page] = {}  # filled by app.py; used for st.switch_page


@dataclass
class Prefs:
    display_name: str = ""  # per-session and optional; the app greets everyone generically by default
    role: str = "Member"
    provider: str = ""
    model: str = ""
    top_k: int = 5
    search_type: str = "mmr"


def settings() -> Settings:
    return get_settings()


# --------------------------------------------------------------------------- resources
@st.cache_resource(show_spinner="Preparing workspace…")
def get_pipeline(workspace: str) -> RAGPipeline:
    s = settings()
    embeddings = get_embeddings(s.embedding_model, s.embedding_device)
    return RAGPipeline(replace(s, collection_name=workspace), embeddings, llm=None)


@st.cache_resource(show_spinner=False)
def _cached_llm(provider: str, model: str):
    s = replace(settings(), llm_provider=provider, llm_model=model)
    return build_llm(s)


def get_llm():
    """Return (llm, error_message)."""
    p = prefs()
    try:
        return _cached_llm(p.provider, p.model), None
    except LLMConfigError as exc:
        return None, str(exc)
    except ImportError as exc:
        return None, f"Provider package not installed ({exc})."


def model_status_badge() -> str:
    """Status shown on the dashboard and in Settings."""
    from documind.ui.components import badge

    llm, _ = get_llm()
    if llm is None:
        return badge("Not configured", "danger")
    if st.session_state.get("llm_auth_failed"):
        return badge("Key rejected", "danger")
    return badge("Key configured", "success")


KEY_HELP = {
    "groq": ("GROQ_API_KEY", "https://console.groq.com/keys"),
    "openai": ("OPENAI_API_KEY", "https://platform.openai.com/api-keys"),
}


def explain_llm_error(exc: Exception) -> str:
    """Turn provider exceptions into an actionable, user-facing message (HTML-safe)."""
    from documind.ui.components import esc

    text = str(exc)
    low = text.lower()
    provider = prefs().provider
    var, url = KEY_HELP.get(provider, ("the provider API key", ""))
    if "401" in low or "invalid_api_key" in low or "invalid api key" in low or "unauthorized" in low:
        st.session_state.llm_auth_failed = True
        where = f' Create a new key at <a href="{url}" target="_blank">{url}</a>.' if url else ""
        return (
            f"<b>The {esc(provider.title())} API key was rejected.</b> Update <code>{var}</code> in your "
            "environment or Streamlit secrets (Manage app → Settings → Secrets), save, then reboot the app."
            f"{where}"
        )
    if "429" in low or "rate limit" in low or "rate_limit" in low:
        return "<b>The model provider's rate limit was reached.</b> Wait a minute and run the analysis again."
    if "connect" in low or "timeout" in low or "timed out" in low:
        return "<b>The model provider could not be reached.</b> Check your connection and try again."
    if "model" in low and ("not found" in low or "does not exist" in low or "decommissioned" in low):
        return (
            f"<b>The model “{esc(prefs().model)}” is not available.</b> Choose another model in "
            "Settings → Assistant model."
        )
    return f"The analysis could not be completed: <code>{esc(text[:400])}</code>"


def activity(workspace: str | None = None) -> ActivityLog:
    s = settings()
    return ActivityLog(s.persist_dir.parent / "activity", workspace or current_workspace())


# --------------------------------------------------------------------------- session
def init_session() -> None:
    ss = st.session_state
    s = settings()
    ss.setdefault("workspace", s.collection_name)
    ss.setdefault(
        "prefs",
        Prefs(
            provider=s.llm_provider,
            model=s.llm_model or DEFAULT_MODELS.get(s.llm_provider, ""),
            top_k=s.top_k,
            search_type=s.search_type,
        ),
    )
    ss.setdefault("memories", {})
    ss.setdefault("reports", {})
    ss.setdefault("doc_query", "")
    ss.setdefault("analysis_scope", [])
    ss.setdefault("uploader_nonce", 0)


def prefs() -> Prefs:
    return st.session_state.prefs


def current_workspace() -> str:
    return st.session_state.workspace


def pipeline() -> RAGPipeline:
    return get_pipeline(current_workspace())


def memory() -> ConversationMemory:
    mems = st.session_state.memories
    ws = current_workspace()
    if ws not in mems:
        mems[ws] = ConversationMemory(settings().memory_window)
    return mems[ws]


def reports() -> list[dict]:
    return st.session_state.reports.setdefault(current_workspace(), [])


def reset_analysis_session() -> None:
    memory().clear()
    st.session_state.reports[current_workspace()] = []


def workspaces() -> list[str]:
    names = set(list_workspaces(settings().persist_dir))
    names.add(settings().collection_name)
    names.add(current_workspace())
    return sorted(names)


_SLUG = re.compile(r"[^a-z0-9]+")


def slugify_workspace(name: str) -> str:
    """Chroma collection names: 3–63 chars of [a-z0-9-], alphanumeric at both ends."""
    slug = _SLUG.sub("-", name.lower()).strip("-")[:60]
    return slug if len(slug) >= 3 else f"{slug}-ws".strip("-")


def go(page_key: str) -> None:
    """Navigate to a page by key (call outside widget callbacks)."""
    st.switch_page(PAGES[page_key])


def request_nav(page_key: str) -> None:
    """Safe to call inside callbacks: navigation happens on the next run."""
    st.session_state["_nav_to"] = page_key
