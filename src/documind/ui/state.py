"""Session state, cached resources and cross-page navigation helpers."""

from __future__ import annotations

import hashlib
import os
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
def _cached_llm(provider: str, model: str, key_fingerprint: str):  # noqa: ARG001 – part of the cache key
    s = replace(settings(), llm_provider=provider, llm_model=model)
    return build_llm(s)


def _key_fingerprint(provider: str) -> str:
    """Short hash of the provider's API key, so a replaced key builds a fresh client."""
    var = {"groq": "GROQ_API_KEY", "openai": "OPENAI_API_KEY"}.get(provider)
    key = os.getenv(var, "") if var else ""
    return hashlib.sha256(key.encode()).hexdigest()[:12]


_NON_CHAT = ("whisper", "guard", "tts", "orpheus", "safeguard", "distil-whisper", "playai")


@st.cache_data(ttl=600, show_spinner=False)
def _list_models(provider: str, key_fingerprint: str) -> list[str]:  # noqa: ARG001 – cache key
    if provider == "groq" and os.getenv("GROQ_API_KEY"):
        from groq import Groq

        ids = [m.id for m in Groq(api_key=os.environ["GROQ_API_KEY"], timeout=8, max_retries=0).models.list().data]
        return sorted(i for i in ids if not any(t in i.lower() for t in _NON_CHAT))
    return []


_OPENAI_SKIP = ("audio", "realtime", "transcribe", "tts", "image", "search", "embedding", "moderation", "instruct")


@st.cache_data(ttl=600, show_spinner=False)
def _list_openai_models(key_fingerprint: str) -> list[str]:  # noqa: ARG001 – cache key
    from openai import OpenAI

    ids = [m.id for m in OpenAI(timeout=8, max_retries=0).models.list().data]
    return sorted(i for i in ids if i.startswith(("gpt-", "o")) and not any(t in i for t in _OPENAI_SKIP))


# Used when a provider's model list can't be fetched.
FALLBACK_MODELS = {
    "groq": ["llama-3.3-70b-versatile", "openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama-3.1-8b-instant"],
    "openai": ["gpt-4o-mini", "gpt-4o"],
}
# Default ordering: the first available model becomes the default and the first fallback.
PREFERRED = [
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-120b",
    "gpt-4o-mini",
    "openai/gpt-oss-20b",
    "llama-3.1-8b-instant",
    "gpt-4o",
]


def model_catalog() -> list[tuple[str, str]]:
    """Every (provider, model) the configured API keys can use, best defaults first."""
    out: list[tuple[str, str]] = []
    if os.getenv("GROQ_API_KEY"):
        out += [("groq", m) for m in (available_models("groq") or FALLBACK_MODELS["groq"])]
    if os.getenv("OPENAI_API_KEY"):
        try:
            models = _list_openai_models(_key_fingerprint("openai"))
        except Exception:  # noqa: BLE001
            models = []
        out += [("openai", m) for m in (models or FALLBACK_MODELS["openai"])]
    p = prefs()
    if p.provider == "ollama":
        out.append(("ollama", p.model))
    rank = {m: i for i, m in enumerate(PREFERRED)}
    return sorted(out, key=lambda pm: rank.get(pm[1], len(rank)))


def model_label(provider: str, model: str) -> str:
    return f"{'OpenAI' if provider == 'openai' else provider.title()} · {model}"


def ensure_valid_model() -> None:
    """If the chosen model isn't offered by any configured key, switch to the best one that is."""
    p, cat = prefs(), model_catalog()
    if cat and (p.provider, p.model) not in cat:
        p.provider, p.model = cat[0]


def llm_for(provider: str, model: str):
    """Return (llm, error_message) for an explicit provider/model."""
    try:
        return _cached_llm(provider, model, _key_fingerprint(provider)), None
    except LLMConfigError as exc:
        return None, str(exc)
    except ImportError as exc:
        return None, f"Provider package not installed ({exc})."


def is_model_unavailable(exc: Exception) -> bool:
    low = str(exc).lower()
    return "model" in low and any(
        t in low for t in ("not found", "does not exist", "decommissioned", "access", "model_not_found")
    )


def available_models(provider: str) -> list[str]:
    """Chat models this API key can use (empty if unknown or the lookup fails)."""
    try:
        return _list_models(provider, _key_fingerprint(provider))
    except Exception:  # noqa: BLE001 – the list is a convenience; fall back to free text
        return []


def test_connection() -> tuple[bool, str]:
    """Make a tiny real request to the provider. Returns (ok, html_message)."""
    llm, err = get_llm()
    if llm is None:
        return False, esc_text(err or "No model configured.")
    try:
        llm.invoke("Reply with the single word OK.")
    except Exception as exc:  # noqa: BLE001
        return False, explain_llm_error(exc)
    st.session_state.llm_auth_failed = False
    return True, f"Connected to {esc_text(prefs().provider.title())} · {esc_text(prefs().model)}"


def esc_text(value: str) -> str:
    from documind.ui.components import esc

    return esc(value)


def get_llm():
    """Return (llm, error_message)."""
    p = prefs()
    try:
        fp = _key_fingerprint(p.provider)
        if st.session_state.get("_key_fp") != fp:  # key changed: forget a previous rejection
            st.session_state._key_fp = fp
            st.session_state.llm_auth_failed = False
        return _cached_llm(p.provider, p.model, fp), None
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
    if is_model_unavailable(exc):
        return (
            f"<b>The model “{esc(prefs().model)}” is not available to this API key.</b> Open "
            "Settings → Assistant model and pick one from the list of models your key can use."
            f'<br><span style="font-size:.75rem;opacity:.8">Provider said: {esc(text[:300])}</span>'
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
