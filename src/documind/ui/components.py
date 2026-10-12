"""Reusable Streamlit rendering helpers."""

from __future__ import annotations

import html

import streamlit as st

from documind.schemas import SourceCitation

SUGGESTIONS = [
    "Summarise each document in 3 bullet points",
    "What are the key findings?",
    "Compare the documents — where do they agree or differ?",
    "List any numbers, dates or metrics mentioned",
]


def render_sources(sources: list[SourceCitation]) -> None:
    if not sources:
        return
    chips = "".join(f'<span class="dm-chip">{html.escape(s.label)}</span>' for s in sources)
    st.markdown(chips, unsafe_allow_html=True)
    with st.expander(f"View {len(sources)} source excerpt{'s' if len(sources) != 1 else ''}"):
        for s in sources:
            score = f" · relevance {s.score:.2f}" if s.score is not None else ""
            st.markdown(f"**{html.escape(s.label)}**{score}")
            st.markdown(f'<div class="dm-snippet">{html.escape(s.snippet)}</div>', unsafe_allow_html=True)


def render_empty_state(has_docs: bool) -> str | None:
    """Hero + suggestion buttons. Returns a suggestion if one was clicked."""
    st.markdown(
        '<div class="dm-hero"><h1>📚 DocuMind</h1>'
        "<p>Chat with your PDFs. Answers are grounded in your documents, with page-level citations.</p></div>",
        unsafe_allow_html=True,
    )
    if not has_docs:
        st.info("⬅️ Upload one or more PDFs in the sidebar to get started.")
        return None
    cols = st.columns(2)
    for i, text in enumerate(SUGGESTIONS):
        if cols[i % 2].button(text, use_container_width=True, key=f"sugg-{i}"):
            return text
    return None


def render_file_list(files: list[dict]) -> None:
    for f in files:
        st.markdown(
            f'<div class="dm-file">📄 {html.escape(f["file_name"])}<br>'
            f'<small>{f["pages"]} pages · {f["chunks"]} chunks</small></div>',
            unsafe_allow_html=True,
        )
