"""DocuMind — Streamlit entry point.

Run:  streamlit run app.py
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import streamlit as st

# Make ``src/`` importable without installing the package (Streamlit Cloud friendly).
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Copy Streamlit secrets into env vars so config.py sees them (Streamlit Cloud).
try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, str):
            os.environ.setdefault(_k, _v)
except Exception:  # noqa: BLE001 – no secrets file locally is fine
    pass

from documind.config import DEFAULT_MODELS, get_settings  # noqa: E402
from documind.embeddings import get_embeddings  # noqa: E402
from documind.llm import LLMConfigError, build_llm  # noqa: E402
from documind.memory import ConversationMemory  # noqa: E402
from documind.pipeline import RAGPipeline  # noqa: E402
from documind.ui.components import render_empty_state, render_file_list, render_sources  # noqa: E402
from documind.ui.styles import CSS  # noqa: E402

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")

st.set_page_config(page_title="DocuMind · Chat with your PDFs", page_icon="📚", layout="centered")
st.markdown(CSS, unsafe_allow_html=True)

settings = get_settings()


# --------------------------------------------------------------------------- resources
@st.cache_resource(show_spinner="Loading embedding model…")
def load_pipeline() -> RAGPipeline:
    embeddings = get_embeddings(settings.embedding_model, settings.embedding_device)
    return RAGPipeline(settings, embeddings, llm=None)


@st.cache_resource(show_spinner=False)
def load_llm(provider: str, model: str):
    os.environ["LLM_PROVIDER"] = provider
    os.environ["LLM_MODEL"] = model
    return build_llm(get_settings())


pipeline = load_pipeline()

# --------------------------------------------------------------------------- session state
ss = st.session_state
ss.setdefault("messages", [])  # list[dict(role, content, sources)]
ss.setdefault("memory", ConversationMemory(settings.memory_window))
ss.setdefault("uploader_key", 0)

# --------------------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("## 📚 DocuMind")
    if st.button("➕  New chat", use_container_width=True):
        ss.messages = []
        ss.memory.clear()
        st.rerun()

    st.markdown("### Documents")
    uploads = st.file_uploader(
        "Upload PDFs", type=["pdf"], accept_multiple_files=True,
        key=f"uploader-{ss.uploader_key}", label_visibility="collapsed",
    )
    if uploads and st.button("Index documents", type="primary", use_container_width=True):
        progress = st.progress(0.0, text="Starting…")
        for i, f in enumerate(uploads, start=1):
            progress.progress((i - 1) / len(uploads), text=f"Indexing {f.name}…")
            report = pipeline.ingest_pdf(f.getvalue(), f.name)
            if report.skipped:
                st.warning(f"**{f.name}** skipped — {report.reason}")
            else:
                st.success(f"**{f.name}**: {report.pages} pages → {report.chunks} chunks")
        progress.progress(1.0, text="Done")
        ss.uploader_key += 1  # clear the uploader
        st.rerun()

    files = pipeline.store.list_files()
    selected_hashes: list[str] | None = None
    if files:
        render_file_list(files)
        names = {f["file_name"]: f["file_hash"] for f in files}
        chosen = st.multiselect("Search only in", list(names), placeholder="All documents")
        selected_hashes = [names[n] for n in chosen] or None

        with st.expander("Manage"):
            to_del = st.selectbox("Remove a document", ["—"] + list(names))
            if to_del != "—" and st.button("Remove", use_container_width=True):
                pipeline.store.delete_file(names[to_del])
                st.rerun()
            if st.button("🗑️ Clear all documents", use_container_width=True):
                pipeline.store.reset()
                ss.messages = []
                ss.memory.clear()
                st.rerun()

    st.markdown("### Model")
    providers = list(DEFAULT_MODELS)
    provider = st.selectbox("Provider", providers, index=providers.index(settings.llm_provider)
                            if settings.llm_provider in providers else 0)
    model = st.text_input("Model", value=settings.llm_model if provider == settings.llm_provider and
                          settings.llm_model else DEFAULT_MODELS[provider])
    st.caption(f"Embeddings: `{settings.embedding_model.split('/')[-1]}` · top-k {settings.top_k} · "
               f"{settings.search_type.upper()}")

# --------------------------------------------------------------------------- LLM
try:
    pipeline.llm = load_llm(provider, model)
    llm_error = None
except LLMConfigError as exc:
    pipeline.llm, llm_error = None, str(exc)
except ImportError as exc:
    pipeline.llm, llm_error = None, f"Provider package missing: {exc}. Run `pip install -r requirements.txt`."

# --------------------------------------------------------------------------- chat history
suggestion = None
if not ss.messages:
    suggestion = render_empty_state(has_docs=bool(files))

for msg in ss.messages:
    with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "📚"):
        st.markdown(msg["content"])
        if msg.get("sources"):
            render_sources(msg["sources"])

# --------------------------------------------------------------------------- input
prompt = st.chat_input("Ask anything about your documents…", disabled=llm_error is not None) or suggestion
if llm_error:
    st.error(llm_error)

if prompt:
    ss.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="📚"):
        try:
            with st.spinner("Searching your documents…"):
                handle = pipeline.ask_stream(prompt, ss.memory, selected_hashes)
            full = st.write_stream(handle.tokens)
            full = full if isinstance(full, str) else "".join(map(str, full))
            result = handle.finalize(full)
            render_sources(result.sources)
            if result.standalone_question != prompt:
                st.caption(f"🔎 Searched for: *{result.standalone_question}*")
            ss.messages.append({"role": "assistant", "content": full, "sources": result.sources})
        except Exception as exc:  # noqa: BLE001 – surface errors in the chat
            logging.exception("Answer failed")
            err = f"⚠️ Something went wrong: `{exc}`"
            st.error(err)
            ss.messages.append({"role": "assistant", "content": err, "sources": []})
