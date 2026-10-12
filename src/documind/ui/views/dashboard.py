"""Dashboard — workspace overview."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import altair as alt
import pandas as pd
import streamlit as st

from documind.ui import actions, state
from documind.ui.components import (
    activity_feed,
    badge,
    card_title,
    documents_table,
    empty_state,
    esc,
    html_block,
    human_size,
    icon,
    kv_list,
    stat_card,
    workspace_label,
)


def _activity_chart(events) -> alt.Chart:
    today = datetime.now(timezone.utc).date()
    days = [today - timedelta(days=i) for i in range(13, -1, -1)]
    rows = []
    for d in days:
        day_events = [e for e in events if e.timestamp.date() == d]
        rows.append(
            {"day": pd.Timestamp(d), "Type": "Documents indexed", "count": sum(e.kind == "upload" for e in day_events)}
        )
        rows.append(
            {"day": pd.Timestamp(d), "Type": "Analyses", "count": sum(e.kind == "analysis" for e in day_events)}
        )
    df = pd.DataFrame(rows)
    return (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3, size=14)
        .encode(
            x=alt.X(
                "day:T",
                title=None,
                scale=alt.Scale(padding=14),
                axis=alt.Axis(
                    format="%b %d",
                    labelAngle=0,
                    tickCount=7,
                    grid=False,
                    labelColor="#64748B",
                    domainColor="#E2E8F0",
                    tickColor="#E2E8F0",
                ),
            ),
            y=alt.Y(
                "sum(count):Q",
                title=None,
                axis=alt.Axis(tickMinStep=1, labelColor="#64748B", gridColor="#F1F5F9", domain=False, ticks=False),
            ),
            color=alt.Color(
                "Type:N",
                scale=alt.Scale(domain=["Analyses", "Documents indexed"], range=["#2563EB", "#93C5FD"]),
                legend=alt.Legend(orient="top", title=None, labelColor="#475569", symbolType="circle"),
            ),
            tooltip=[alt.Tooltip("day:T", format="%b %d"), "Type:N", alt.Tooltip("count:Q", title="Count")],
        )
        .properties(height=230)
        .configure_view(strokeWidth=0)
        .configure(font="Inter", background="transparent")
    )


def render() -> None:
    pipe, log, p = state.pipeline(), state.activity(), state.prefs()
    ws = workspace_label(state.current_workspace())
    files = pipe.store.list_files()
    events = log.events()
    llm, llm_error = state.get_llm()

    n_docs = len(files)
    n_pages = sum(f["pages"] for f in files)
    n_chunks = sum(f["chunks"] for f in files)
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    analyses = [e for e in events if e.kind == "analysis"]
    analyses_week = sum(e.timestamp >= week_ago for e in analyses)
    uploads_week = sum(e.kind == "upload" and e.timestamp >= week_ago for e in events)

    # ---- Welcome + quick actions -------------------------------------------
    with st.container(key="card-welcome"):
        left, right = st.columns([3, 2], vertical_alignment="center")
        with left:
            first = p.display_name.split()[0] if p.display_name.strip() else ""
            greeting = f"Welcome back, {first}" if first else "Welcome back"
            html_block(
                f'<div class="dm-eyebrow">{esc(ws)} workspace</div>'
                f'<h1 class="dm-page-title" style="margin-top:.35rem">{esc(greeting)}</h1>'
                f'<p class="dm-page-sub">{datetime.now().strftime("%A, %B %d")} · '
                f"{n_docs} document{'s' if n_docs != 1 else ''} ready for analysis</p>"
            )
        with right, st.container(horizontal=True, horizontal_alignment="right", gap="small"):
            if st.button("Upload documents", type="primary", icon=":material/upload:"):
                actions.upload_dialog()
            if st.button("New analysis", icon=":material/manage_search:", disabled=n_docs == 0):
                state.go("analysis")
            if st.button("View documents", icon=":material/folder_open:", type="tertiary"):
                state.go("documents")

    st.space("small")

    # ---- Stat cards --------------------------------------------------------
    cards = [
        stat_card(
            "Documents",
            f"{n_docs:,}",
            f'<span class="up">+{uploads_week}</span> this week' if uploads_week else "In this workspace",
            "file",
        ),
        stat_card(
            "Pages indexed", f"{n_pages:,}", f"{human_size(sum(f.get('file_size') or 0 for f in files))} total", "pages"
        ),
        stat_card("Searchable segments", f"{n_chunks:,}", "Semantic index", "layers"),
        stat_card(
            "Analyses",
            f"{len(analyses):,}",
            f'<span class="up">+{analyses_week}</span> this week' if analyses_week else "No analyses yet",
            "chart",
        ),
    ]
    st.html(f'<div class="dm-stat-grid">{"".join(cards)}</div>')

    st.space("small")

    # ---- Chart + overview --------------------------------------------------
    left, right = st.columns([2, 1])
    with left, st.container(key="card-activity-chart"):
        card_title("Workspace activity", "Documents indexed and analyses run · last 14 days")
        if events:
            st.altair_chart(_activity_chart(events), width="stretch", theme=None)
        else:
            empty_state("No activity yet", "Upload documents and run analyses to see trends here.", "chart")

    with right, st.container(key="card-overview"):
        card_title("Workspace overview")
        status = badge("Ready", "success") if n_docs else badge("Awaiting documents", "warning")
        model_status = badge("Connected", "success") if llm else badge("Not configured", "danger")
        s = state.settings()
        html_block(
            kv_list(
                [
                    ("Index status", status),
                    ("Assistant", model_status),
                    ("Model", esc(p.model or "—")),
                    ("Embeddings", esc(s.embedding_model.split("/")[-1])),
                    (
                        "Retrieval",
                        esc(f"{'Balanced (MMR)' if p.search_type == 'mmr' else 'Similarity'} · top {p.top_k}"),
                    ),
                ]
            )
        )
        if llm_error:
            st.page_link(state.PAGES["settings"], label="Configure assistant", icon=":material/settings:")

    st.space("small")

    # ---- Recent documents + activity --------------------------------------
    left, right = st.columns([2, 1])
    with left, st.container(key="card-recent-docs"):
        head_l, head_r = st.columns([3, 1], vertical_alignment="center")
        with head_l:
            card_title("Recent documents", f"{n_docs} total")
        with head_r:
            if n_docs and st.button(
                "View all", type="tertiary", icon=":material/arrow_forward:", icon_position="right", key="dash-view-all"
            ):
                state.go("documents")
        if files:
            recent = sorted(files, key=lambda f: f.get("uploaded_at") or "", reverse=True)[:5]
            st.html(documents_table(recent))
        else:
            empty_state(
                "No documents yet", "Upload contracts, reports, policies or research papers to get started.", "folder"
            )
            _, mid, _ = st.columns([1, 1.2, 1])
            if mid.button(
                "Upload documents", type="primary", icon=":material/upload:", width="stretch", key="dash-empty-upload"
            ):
                actions.upload_dialog()

    with right, st.container(key="card-recent-activity"):
        card_title("Recent activity")
        if events:
            st.html(activity_feed(events[:6]))
            st.page_link(state.PAGES["activity"], label="View all activity", icon=":material/history:")
        else:
            empty_state("Nothing here yet", "Uploads, analyses and changes will appear here.", "clock")

    # ---- Onboarding checklist (until complete) -----------------------------
    steps = [
        ("Create a workspace", True),
        ("Upload your first document", n_docs > 0),
        ("Connect an assistant model", llm is not None),
        ("Run your first analysis", len(analyses) > 0),
    ]
    done = sum(d for _, d in steps)
    if done < len(steps):
        st.space("small")
        with st.container(key="card-onboarding"):
            card_title("Get started", f"{done} of {len(steps)} steps complete")
            st.progress(done / len(steps))
            st.html(
                "".join(
                    f'<div class="dm-check {"done" if d else ""}"><span class="box">'
                    f"{icon('check', 12, '#FFFFFF') if d else ''}</span>{esc(label)}</div>"
                    for label, d in steps
                )
            )
