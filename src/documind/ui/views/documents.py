"""Documents — upload zone and file management table."""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from documind.ui import actions, state
from documind.ui.components import (
    activity_feed,
    badge,
    card_title,
    empty_state,
    file_cell,
    fmt_date,
    human_size,
    page_header,
    workspace_label,
)

SORTS = {
    "Newest first": (lambda f: f.get("uploaded_at") or "", True),
    "Oldest first": (lambda f: f.get("uploaded_at") or "", False),
    "Name (A–Z)": (lambda f: f["file_name"].lower(), False),
    "Most pages": (lambda f: f["pages"], True),
}


COLS = [4.2, 1, 1.6, 1.4, 1.5]


def _table(files: list[dict]) -> None:
    with st.container(key="doctable", gap=None):
        with st.container(key="dochead"):
            h = st.columns(COLS, vertical_alignment="center", wrap=False)
            for col, label in zip(h, ["File name", "Type", "Uploaded", "Status", "Actions"], strict=True):
                align = "text-align:right;padding-right:.35rem" if label == "Actions" else ""
                col.html(f'<div class="dm-th" style="{align}">{label}</div>')
        for i, f in enumerate(files):
            with st.container(key=f"docrow-{i}"):
                c = st.columns(COLS, vertical_alignment="center", wrap=False)
                c[0].html(file_cell(f["file_name"], f"{human_size(f.get('file_size'))} · {f['pages']} pages"))
                c[1].html('<span class="dm-tag">PDF</span>')
                c[2].html(f'<span class="dm-td">{fmt_date(f.get("uploaded_at"))}</span>')
                c[3].html(badge("Indexed", "success"))
                with c[4], st.container(horizontal=True, gap=None, horizontal_alignment="right", wrap=False):
                    if st.button(
                        "", icon=":material/manage_search:", key=f"an-{f['file_hash']}", help="Analyze", type="tertiary"
                    ):
                        st.session_state.analysis_scope = [f["file_hash"]]
                        state.go("analysis")
                    if st.button(
                        "", icon=":material/info:", key=f"in-{f['file_hash']}", help="Details", type="tertiary"
                    ):
                        actions.document_details(f)
                    if st.button(
                        "", icon=":material/delete:", key=f"rm-{f['file_hash']}", help="Remove", type="tertiary"
                    ):
                        actions.confirm_delete(f)


def _insights(files: list[dict]) -> None:
    if not files:
        empty_state("No insights yet", "Charts appear once documents are indexed.", "chart")
        return
    df = pd.DataFrame([{"Document": f["file_name"], "Pages": f["pages"], "Segments": f["chunks"]} for f in files])
    df = df.sort_values("Pages", ascending=False).head(12)
    left, right = st.columns(2)
    axis = {"labelColor": "#64748B", "domainColor": "#E2E8F0", "tickColor": "#E2E8F0", "gridColor": "#F1F5F9"}
    for col, field, title, color in [
        (left, "Pages", "Pages per document", "#2563EB"),
        (right, "Segments", "Indexed segments per document", "#1E293B"),
    ]:
        with col, st.container(key=f"card-ins-{field}"):
            card_title(title)
            chart = (
                alt.Chart(df)
                .mark_bar(cornerRadiusEnd=3, color=color, size=14)
                .encode(
                    y=alt.Y(
                        "Document:N",
                        sort="-x",
                        title=None,
                        axis=alt.Axis(labelLimit=180, **{k: v for k, v in axis.items() if k != "gridColor"}),
                    ),
                    x=alt.X(f"{field}:Q", title=None, axis=alt.Axis(**axis)),
                    tooltip=["Document", field],
                )
                .properties(height=max(120, 32 * len(df)))
                .configure_view(strokeWidth=0)
                .configure(font="Inter", background="transparent")
            )
            st.altair_chart(chart, width="stretch", theme=None)


def render() -> None:
    pipe = state.pipeline()
    ws = workspace_label(state.current_workspace())
    files = pipe.store.list_files()
    n_pages = sum(f["pages"] for f in files)

    head, btns = st.columns([3, 1.4], vertical_alignment="bottom")
    with head:
        page_header("Documents", f"{len(files)} documents · {n_pages:,} pages indexed", [ws, "Documents"])
    with btns, st.container(horizontal=True, horizontal_alignment="right"):
        if st.button("New analysis", icon=":material/manage_search:", disabled=not files):
            state.go("analysis")

    # ---- Upload zone ------------------------------------------------------
    with st.container(key="card-upload"):
        card_title(
            "Add documents",
            "Drag and drop PDF files, or browse to upload. Text is extracted, segmented and indexed automatically.",
        )
        if actions.upload_zone("page"):
            st.rerun()

    st.space("small")

    tab_all, tab_insights, tab_history = st.tabs([f"All documents ({len(files)})", "Insights", "Upload history"])

    with tab_all:
        if not files:
            with st.container(key="card-docs-empty"):
                empty_state(
                    "Your document library is empty",
                    "Upload contracts, financial statements, policies, clinical guidelines or research — "
                    "then analyze them together.",
                    "folder",
                )
        else:
            f1, f2 = st.columns([3, 1.2], vertical_alignment="center")
            query = f1.text_input(
                "Filter",
                key="doc_query",
                placeholder="Filter by file name…",
                icon=":material/search:",
                label_visibility="collapsed",
            )
            sort = f2.selectbox("Sort", list(SORTS), label_visibility="collapsed")
            keyf, rev = SORTS[sort]
            shown = sorted([f for f in files if query.lower() in f["file_name"].lower()], key=keyf, reverse=rev)
            if shown:
                _table(shown)
                st.caption(f"Showing {len(shown)} of {len(files)} documents")
            else:
                with st.container(key="card-docs-nomatch"):
                    empty_state("No matching documents", f"Nothing matches “{query}”. Try a different name.", "search")

    with tab_insights:
        _insights(files)

    with tab_history:
        events = state.activity().events(kinds={"upload", "upload_failed", "delete"})
        with st.container(key="card-upload-history"):
            if events:
                st.html(activity_feed(events[:50], group_by_day=True))
            else:
                empty_state("No upload history", "Uploads and removals will be listed here.", "clock")
