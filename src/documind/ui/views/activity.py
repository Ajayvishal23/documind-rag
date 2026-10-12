"""Activity — audit-style timeline of workspace events."""

from __future__ import annotations

import csv
import io

import streamlit as st

from documind.ui import state
from documind.ui.components import activity_feed, empty_state, page_header, workspace_label

FILTERS = {
    "All": None,
    "Uploads": {"upload", "upload_failed"},
    "Analyses": {"analysis"},
    "Removals": {"delete", "workspace_cleared"},
}


def _csv(events) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["timestamp_utc", "event", "subject", "detail"])
    for e in events:
        w.writerow([e.ts, e.label, e.title, e.detail])
    return buf.getvalue()


def render() -> None:
    ws = workspace_label(state.current_workspace())
    log = state.activity()

    head, btns = st.columns([3, 1.4], vertical_alignment="bottom")
    with head:
        page_header(
            "Activity", "A complete record of uploads, analyses and changes in this workspace.", [ws, "Activity"]
        )
    all_events = log.events()
    with btns, st.container(horizontal=True, horizontal_alignment="right"):
        st.download_button(
            "Export CSV",
            _csv(all_events),
            file_name=f"{state.current_workspace()}-activity.csv",
            mime="text/csv",
            icon=":material/download:",
            disabled=not all_events,
        )

    choice = st.segmented_control("Filter", list(FILTERS), default="All", label_visibility="collapsed") or "All"
    events = log.events(kinds=FILTERS[choice])

    with st.container(key="card-activity"):
        if events:
            st.html(activity_feed(events[:200], group_by_day=True))
            if len(events) > 200:
                st.caption(f"Showing the latest 200 of {len(events)} events. Export CSV for the full log.")
        else:
            empty_state("No activity to show", "Events matching this filter will appear here.", "clock")
