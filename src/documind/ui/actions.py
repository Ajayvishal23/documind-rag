"""Shared actions and modal dialogs used across pages."""

from __future__ import annotations

import streamlit as st

from documind.ui import state
from documind.ui.components import (
    badge,
    esc,
    fmt_date,
    html_block,
    human_size,
    kv_list,
    workspace_label,
)


# --------------------------------------------------------------------------- upload
def upload_zone(key_prefix: str = "main") -> bool:
    """Drag-and-drop zone + index button. Returns True when files were indexed."""
    ss = st.session_state
    files = st.file_uploader(
        "Upload PDF documents",
        type=["pdf"],
        accept_multiple_files=True,
        key=f"{key_prefix}-uploader-{ss.uploader_nonce}",
        label_visibility="collapsed",
        help=f"PDF only · up to {state.settings().max_file_mb} MB per file",
    )
    if not files:
        return False

    total = sum(f.size for f in files)
    cols = st.columns([3, 1.3], vertical_alignment="center")
    cols[0].caption(f"{len(files)} file{'s' if len(files) != 1 else ''} selected · {human_size(total)}")
    if not cols[1].button(
        f"Index {len(files)} file{'s' if len(files) != 1 else ''}",
        type="primary",
        icon=":material/upload:",
        width="stretch",
        key=f"{key_prefix}-index",
    ):
        return False

    index_files(files)
    ss.uploader_nonce += 1
    return True


def index_files(files) -> None:
    pipe, log = state.pipeline(), state.activity()
    progress = st.progress(0.0, text="Preparing…")
    ok, skipped = 0, []
    for i, f in enumerate(files):
        progress.progress(i / len(files), text=f"Processing {f.name} ({i + 1} of {len(files)})")
        report = pipe.ingest_pdf(f.getvalue(), f.name)
        if report.skipped:
            skipped.append((f.name, report.reason))
            log.record("upload_failed", f.name, report.reason)
        else:
            ok += 1
            log.record(
                "upload",
                f.name,
                f"{report.pages} pages · {report.chunks} segments",
                pages=report.pages,
                chunks=report.chunks,
            )
    progress.progress(1.0, text="Complete")
    msg = f"{ok} document{'s' if ok != 1 else ''} indexed"
    if skipped:
        msg += f" · {len(skipped)} skipped"
    st.toast(msg, icon=":material/check_circle:" if not skipped else ":material/info:")
    for name, reason in skipped:
        st.toast(f"{name}: {reason}", icon=":material/warning:")


@st.dialog("Upload documents", width="large")
def upload_dialog() -> None:
    st.caption(f"Files are added to **{workspace_label(state.current_workspace())}** and indexed for analysis.")
    if upload_zone("dialog"):
        st.rerun()


# --------------------------------------------------------------------------- documents
@st.dialog("Remove document")
def confirm_delete(file: dict) -> None:
    html_block(
        f'<p style="margin:0 0 .5rem">Remove <b>{esc(file["file_name"])}</b> from this workspace?</p>'
        '<p style="color:#64748B;font-size:.875rem;margin:0">Its indexed content will be deleted and it '
        "will no longer appear in analyses. This can't be undone.</p>"
    )
    st.space("small")
    c1, c2 = st.columns(2)
    if c1.button("Cancel", width="stretch"):
        st.rerun()
    if c2.button("Remove document", type="primary", width="stretch", icon=":material/delete:"):
        state.pipeline().store.delete_file(file["file_hash"])
        state.activity().record("delete", file["file_name"], "Removed from workspace")
        st.session_state.analysis_scope = [h for h in st.session_state.analysis_scope if h != file["file_hash"]]
        st.toast(f"{file['file_name']} removed", icon=":material/delete:")
        st.rerun()


@st.dialog("Document details", width="medium")
def document_details(file: dict) -> None:
    html_block(
        f'<p style="font-weight:600;font-size:1rem;margin:0 0 .25rem">{esc(file["file_name"])}</p>'
        + kv_list(
            [
                ("Status", badge("Indexed", "success")),
                ("Type", "PDF document"),
                ("Size", human_size(file.get("file_size"))),
                ("Pages", str(file["pages"])),
                ("Indexed segments", str(file["chunks"])),
                ("Uploaded", fmt_date(file.get("uploaded_at"))),
                ("Workspace", esc(workspace_label(state.current_workspace()))),
                ("Content hash", f'<code style="font-size:.75rem">{esc(file["file_hash"][:16])}…</code>'),
            ]
        )
    )
    st.space("small")
    if st.button("Analyze this document", type="primary", icon=":material/manage_search:", width="stretch"):
        st.session_state.analysis_scope = [file["file_hash"]]
        state.go("analysis")


# --------------------------------------------------------------------------- workspaces
@st.dialog("Create workspace")
def new_workspace_dialog() -> None:
    st.caption("Workspaces keep documents and analyses separate — for example per client, matter or project.")
    name = st.text_input("Workspace name", placeholder="e.g. Acme Corp — Due Diligence", max_chars=50)
    slug = state.slugify_workspace(name) if name.strip() else ""
    if slug in state.workspaces():
        st.caption(":orange[A workspace with this name already exists.]")
    c1, c2 = st.columns(2)
    if c1.button("Cancel", width="stretch"):
        st.rerun()
    if c2.button("Create workspace", type="primary", width="stretch", disabled=not slug or slug in state.workspaces()):
        st.session_state.workspace = slug
        state.get_pipeline(slug)  # creates the collection
        state.activity(slug).record("workspace_created", workspace_label(slug), "New workspace")
        st.toast(f"Workspace “{workspace_label(slug)}” created", icon=":material/check_circle:")
        st.rerun()


@st.dialog("Clear workspace")
def confirm_clear_workspace() -> None:
    ws = workspace_label(state.current_workspace())
    st.markdown(f"This permanently removes **all documents** from **{ws}**.")
    confirm = st.text_input(f"Type **{ws}** to confirm")
    c1, c2 = st.columns(2)
    if c1.button("Cancel", width="stretch"):
        st.rerun()
    if c2.button("Clear workspace", type="primary", width="stretch", disabled=confirm.strip() != ws):
        state.pipeline().store.reset()
        state.reset_analysis_session()
        state.activity().record("workspace_cleared", ws, "All documents removed")
        st.toast("Workspace cleared", icon=":material/delete:")
        st.rerun()
