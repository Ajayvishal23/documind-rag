"""DocuMind — document intelligence workspace.

Run:  streamlit run app.py
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

# Copy Streamlit secrets into env vars so config.py sees them (Streamlit Cloud).
try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, str):
            os.environ.setdefault(_k, _v)
except Exception:  # noqa: BLE001 – no secrets file locally is fine
    pass

from documind.ui import actions, state  # noqa: E402
from documind.ui.components import activity_feed, esc, initials, workspace_label  # noqa: E402
from documind.ui.styles import CSS  # noqa: E402
from documind.ui.views import activity, analysis, dashboard, documents, settings  # noqa: E402

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")

st.set_page_config(
    page_title="DocuMind · Document Intelligence",
    page_icon=str(ROOT / "assets" / "icon.svg"),
    layout="wide",
    initial_sidebar_state="auto",
)
st.html(CSS)
st.logo(str(ROOT / "assets" / "logo.svg"), icon_image=str(ROOT / "assets" / "icon.svg"), size="large")

state.init_session()

# --------------------------------------------------------------------------- navigation
START = os.getenv("DOCUMIND_START_PAGE", "dashboard")  # landing page (also used by UI tests)
pages = {
    "dashboard": st.Page(
        dashboard.render,
        title="Dashboard",
        icon=":material/space_dashboard:",
        url_path="dashboard",
        default=START == "dashboard",
    ),
    "documents": st.Page(
        documents.render,
        title="Documents",
        icon=":material/folder_open:",
        url_path="documents",
        default=START == "documents",
    ),
    "analysis": st.Page(
        analysis.render,
        title="Analysis",
        icon=":material/manage_search:",
        url_path="analysis",
        default=START == "analysis",
    ),
    "activity": st.Page(
        activity.render, title="Activity", icon=":material/history:", url_path="activity", default=START == "activity"
    ),
    "settings": st.Page(
        settings.render, title="Settings", icon=":material/settings:", url_path="settings", default=START == "settings"
    ),
}
state.PAGES.update(pages)
current = st.navigation(
    {
        "Workspace": [pages["dashboard"], pages["documents"], pages["analysis"]],
        "Insights": [pages["activity"]],
        "Administration": [pages["settings"]],
    }
)

if nav_to := st.session_state.pop("_nav_to", None):
    st.switch_page(pages[nav_to])


# --------------------------------------------------------------------------- sidebar footer
def _sidebar() -> None:
    files = state.pipeline().store.list_files()
    n_pages = sum(f["pages"] for f in files)
    capacity = 2000  # soft guide for a single free-tier workspace
    pct = min(100, round(n_pages / capacity * 100))
    with st.sidebar:
        st.space("medium")
        st.html(
            f'<div class="dm-side-card"><b>{esc(workspace_label(state.current_workspace()))}</b><br>'
            f"{len(files)} documents · {n_pages:,} pages"
            f'<div class="dm-side-meter"><span style="width:{max(pct, 2)}%"></span></div>'
            f'<span style="font-size:.75rem;color:#94A3B8">{pct}% of recommended index size</span></div>'
        )
        st.html(
            '<div class="dm-side-foot"><a href="https://github.com/Ajayvishal23/documind-rag" target="_blank">'
            "Documentation</a> · v2.0</div>"
        )


# --------------------------------------------------------------------------- top bar
def _on_search() -> None:
    q = st.session_state.get("global_search", "").strip()
    if q:
        st.session_state.doc_query = q
        st.session_state.global_search = ""
        state.request_nav("documents")


def _on_workspace() -> None:
    choice = st.session_state.ws_select
    if choice != state.current_workspace():
        st.session_state.workspace = choice
        st.toast(f"Switched to {workspace_label(choice)}", icon=":material/swap_horiz:")


def _topbar() -> None:
    p = state.prefs()
    wss = state.workspaces()
    if st.session_state.get("ws_select") != state.current_workspace():
        st.session_state.ws_select = state.current_workspace()  # keep switcher in sync (e.g. after create)
    with st.container(key="topbar"):
        c = st.columns([2.2, 4.2, 3.4], vertical_alignment="center", gap="small", wrap=False)
        with c[0]:
            st.selectbox(
                "Workspace",
                wss,
                key="ws_select",
                format_func=workspace_label,
                label_visibility="collapsed",
                on_change=_on_workspace,
            )
        with c[1]:
            st.text_input(
                "Search",
                key="global_search",
                placeholder="Search documents…",
                icon=":material/search:",
                label_visibility="collapsed",
                on_change=_on_search,
            )
        with c[2], st.container(horizontal=True, horizontal_alignment="right", vertical_alignment="center", wrap=False):
            if st.button("New workspace", icon=":material/add:", type="tertiary", key="topbar-new-ws"):
                actions.new_workspace_dialog()
            with st.popover("", icon=":material/notifications:", help="Notifications", width="content"):
                st.markdown("**Notifications**")
                events = state.activity().events(limit=6)
                if events:
                    st.html(activity_feed(events))
                else:
                    st.caption("You're all caught up.")
                st.page_link(pages["activity"], label="View all activity", icon=":material/history:")
            name = p.display_name.strip()
            with st.popover(
                initials(name) if name else "",
                icon=None if name else ":material/account_circle:",
                help="Account",
                width="content",
            ):
                st.html(
                    f'<div style="font-weight:600">{esc(name or "Your account")}</div>'
                    f'<div style="font-size:.8125rem;color:#64748B">{esc(p.role)} · '
                    f"{esc(workspace_label(state.current_workspace()))}</div>"
                )
                st.divider()
                st.page_link(pages["settings"], label="Settings", icon=":material/settings:")
                st.page_link(pages["activity"], label="Activity log", icon=":material/history:")
                if st.button("Reset analysis session", icon=":material/restart_alt:", type="tertiary"):
                    state.reset_analysis_session()
                    st.rerun()


_sidebar()
_topbar()
current.run()
