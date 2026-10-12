"""Document Analysis — question composer, report cards and a references panel."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

import streamlit as st

from documind.ui import actions, state
from documind.ui.components import (
    callout,
    card_title,
    empty_state,
    esc,
    format_answer,
    html_block,
    page_header,
    reference_card,
    rel_time,
    skeleton,
    workspace_label,
)

logger = logging.getLogger(__name__)

TEMPLATES = {
    "Executive summary": "Provide an executive summary of the documents in scope: purpose, key points and conclusions.",
    "Obligations & risks": "Identify the key obligations, risks, liabilities and deadlines "
    "described in these documents.",
    "Figures & dates": "Extract all important figures, amounts, percentages and dates, with what each refers to. "
    "Present them as a table.",
    "Compare documents": "Compare the documents in scope: where do they agree, where do they differ, and what is "
    "unique to each?",
}


def _report_meta(r: dict) -> str:
    chips = [
        f'<span class="dm-tag">{esc(r["scope"])}</span>',
        f'<span class="dm-tag">{len(r["sources"])} reference{"s" if len(r["sources"]) != 1 else ""}</span>',
        f'<span class="dm-tag">{r["duration"]:.1f}s</span>',
    ]
    return f'<div class="dm-report-meta">{"".join(chips)}</div>'


def _report_header(r: dict) -> str:
    rewrite = ""
    if r["standalone"] and r["standalone"].strip() != r["question"].strip():
        rewrite = f'<div class="dm-report-rewrite">Interpreted as: {esc(r["standalone"])}</div>'
    return (
        f'<div class="dm-report-label"><span class="id">Analysis {r["id"]:02d}</span>'
        f"<span>·</span><span>{rel_time(r['created_at'])}</span></div>"
        f'<div class="dm-report-q">{esc(r["question"])}</div>{rewrite}'
    )


def _to_markdown(r: dict) -> str:
    refs = "\n".join(f"- [{c.index}] {c.file_name}, page {c.page}" for c in r["sources"])
    return (
        f"# Analysis {r['id']:02d}\n\n**Question:** {r['question']}\n\n**Scope:** {r['scope']}\n\n"
        f"**Generated:** {r['created_at']}\n\n---\n\n{r['answer']}\n\n## References\n\n{refs}\n"
    )


def _render_report(r: dict) -> None:
    with st.container(key=f"report-{r['id']}"):
        html_block(_report_header(r) + _report_meta(r) + '<div class="dm-report-divider"></div>')
        st.markdown(format_answer(r["answer"]), unsafe_allow_html=True)
        with st.container(horizontal=True, gap="small"):
            if st.button(
                "View references",
                icon=":material/format_quote:",
                type="tertiary",
                key=f"refs-{r['id']}",
                disabled=not r["sources"],
            ):
                st.session_state.selected_report = r["id"]
                st.rerun()
            st.download_button(
                "Export",
                data=_to_markdown(r),
                file_name=f"analysis-{r['id']:02d}.md",
                mime="text/markdown",
                icon=":material/download:",
                type="tertiary",
                key=f"dl-{r['id']}",
            )


def _run_analysis(question: str, scope_hashes: list[str] | None, scope_label: str, llm) -> None:
    p, reports = state.prefs(), state.reports()
    rid = (reports[-1]["id"] + 1) if reports else 1
    started = time.perf_counter()
    with st.container(key=f"report-{rid}"):
        html_block(
            f'<div class="dm-report-label"><span class="id">Analysis {rid:02d}</span><span>·</span>'
            f'<span>in progress</span></div><div class="dm-report-q">{esc(question)}</div>'
            '<div class="dm-report-divider"></div>'
        )
        body = st.empty()
        body.html(skeleton(4, "Searching documents and gathering evidence…"))
        try:
            handle = state.pipeline().ask_stream(
                question, state.memory(), scope_hashes, llm=llm, top_k=p.top_k, search_type=p.search_type
            )
            body.html(skeleton(3, f"Drafting analysis from {len(handle.hits)} passages…"))
            parts: list[str] = []
            for tok in handle.tokens:
                parts.append(tok)
                body.markdown(format_answer("".join(parts)) + " ▍", unsafe_allow_html=True)
            full = "".join(parts)
            result = handle.finalize(full)
            st.session_state.llm_auth_failed = False
        except Exception as exc:  # noqa: BLE001
            logger.exception("Analysis failed")
            body.empty()
            callout(state.explain_llm_error(exc), "warning")
            return

    duration = time.perf_counter() - started
    reports.append(
        {
            "id": rid,
            "question": question,
            "standalone": result.standalone_question,
            "answer": full,
            "sources": result.sources,
            "scope": scope_label,
            "duration": duration,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
    )
    st.session_state.selected_report = rid
    state.activity().record(
        "analysis", question[:120], f"{len(result.sources)} references · {scope_label}", duration=round(duration, 2)
    )
    st.rerun()


def _references_panel(reports: list[dict]) -> None:
    with st.container(key="card-references"):
        card_title("References", "Source passages cited in the analysis")
        if not reports:
            empty_state(
                "No references yet", "Run an analysis to see the exact passages and pages it relies on.", "book"
            )
            return
        ids = [r["id"] for r in reversed(reports)]
        sel = st.session_state.get("selected_report", ids[0])
        if sel not in ids:
            sel = ids[0]
        sel = st.selectbox(
            "Analysis",
            ids,
            index=ids.index(sel),
            format_func=lambda i: f"Analysis {i:02d} — " + next(r["question"] for r in reports if r["id"] == i)[:48],
            label_visibility="collapsed",
        )
        st.session_state.selected_report = sel
        report = next(r for r in reports if r["id"] == sel)
        if not report["sources"]:
            empty_state("No references", "This analysis did not cite any passages.", "book")
            return
        files = sorted({c.file_name for c in report["sources"]})
        st.caption(f"{len(report['sources'])} passages from {len(files)} document{'s' if len(files) != 1 else ''}")
        st.html("".join(reference_card(c) for c in report["sources"]))


def render() -> None:
    pipe = state.pipeline()
    ws = workspace_label(state.current_workspace())
    files = pipe.store.list_files()
    reports = state.reports()
    llm, llm_error = state.get_llm()

    head, btns = st.columns([3, 1.4], vertical_alignment="bottom")
    with head:
        page_header(
            "Document Analysis",
            "Ask questions across your documents. Every finding is referenced to its source page.",
            [ws, "Analysis"],
        )
    with btns, st.container(horizontal=True, horizontal_alignment="right"):
        if st.button(
            "New session",
            icon=":material/restart_alt:",
            disabled=not reports,
            help="Clear analyses and context for this workspace",
        ):
            state.reset_analysis_session()
            st.rerun()

    if not files:
        with st.container(key="card-analysis-empty"):
            empty_state(
                "Add documents to start analyzing",
                "Upload documents to this workspace, then ask questions across all of them at once.",
                "folder",
            )
            _, mid, _ = st.columns([1, 1, 1])
            if mid.button("Upload documents", type="primary", icon=":material/upload:", width="stretch"):
                actions.upload_dialog()
        return

    main, side = st.columns([1.75, 1], gap="medium")

    with main:
        with st.container(key="card-composer"):
            names = {f["file_hash"]: f["file_name"] for f in files}
            scope = [h for h in st.session_state.analysis_scope if h in names]
            scope = st.multiselect(
                "Scope", list(names), default=scope, format_func=names.get, placeholder=f"All documents ({len(files)})"
            )
            st.session_state.analysis_scope = scope
            scope_label = (
                "All documents" if not scope else names[scope[0]] if len(scope) == 1 else f"{len(scope)} documents"
            )

            template = st.pills("Templates", list(TEMPLATES), label_visibility="collapsed", key="template")
            if template and st.session_state.get("_last_template") != template:
                st.session_state.question_box = TEMPLATES[template]
            st.session_state._last_template = template

            with st.form("composer", clear_on_submit=True, border=False):
                question = st.text_area(
                    "Question",
                    key="question_box",
                    height=96,
                    label_visibility="collapsed",
                    placeholder="e.g. What are the termination conditions across these agreements?",
                )
                c1, c2 = st.columns([3, 1.2], vertical_alignment="center")
                c1.caption("Follow-up questions automatically use context from earlier analyses.")
                submitted = c2.form_submit_button(
                    "Run analysis", type="primary", icon=":material/play_arrow:", width="stretch", disabled=llm is None
                )
            if llm_error:
                callout(
                    f"Assistant not configured: {esc(llm_error)} Add the key to your environment or "
                    "Streamlit secrets, then reload.",
                    "warning",
                )

        st.space("small")
        if submitted and question.strip():
            _run_analysis(question.strip(), scope or None, scope_label, llm)

        if reports:
            for r in reversed(reports):
                _render_report(r)
        else:
            with st.container(key="card-no-reports"):
                empty_state(
                    "No analyses in this session",
                    "Choose a template or write a question above. Results appear here as structured "
                    "reports with source references.",
                    "search",
                )

    with side:
        _references_panel(reports)
