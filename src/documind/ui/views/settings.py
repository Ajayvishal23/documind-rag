"""Settings — profile, assistant model, retrieval and workspace administration."""

from __future__ import annotations

import streamlit as st

from documind.config import DEFAULT_MODELS
from documind.ui import actions, state
from documind.ui.components import (
    callout,
    card_title,
    esc,
    html_block,
    human_size,
    kv_list,
    page_header,
    workspace_label,
)

PROVIDER_LABELS = {"groq": "Groq (hosted, free tier)", "openai": "OpenAI", "ollama": "Ollama (self-hosted)"}


def render() -> None:
    ws = workspace_label(state.current_workspace())
    p, s = state.prefs(), state.settings()
    page_header(
        "Settings", "Manage your profile, assistant model, retrieval behaviour and workspace.", [ws, "Settings"]
    )

    general, model, retrieval, workspace = st.tabs(["General", "Assistant model", "Retrieval", "Workspace"])

    with general, st.container(key="card-set-general"):
        card_title("Profile", "Optional. Applies only to your current session; other users never see it.")
        with st.form("profile", border=False):
            c1, c2 = st.columns(2)
            name = c1.text_input("Display name", value=p.display_name, max_chars=60, placeholder="Optional")
            role = c2.text_input("Role", value=p.role, max_chars=60)
            if st.form_submit_button("Save changes", type="primary"):
                p.display_name, p.role = name.strip(), role.strip() or p.role
                st.toast("Profile updated", icon=":material/check_circle:")
                st.rerun()

    with model, st.container(key="card-set-model"):
        card_title(
            "Assistant model",
            "The language model that writes analyses. API keys are read from environment "
            "variables or Streamlit secrets and are never stored in the app.",
        )
        providers = list(DEFAULT_MODELS)
        c1, c2 = st.columns(2)
        provider = c1.selectbox(
            "Provider",
            providers,
            index=providers.index(p.provider) if p.provider in providers else 0,
            format_func=PROVIDER_LABELS.get,
        )
        default_model = p.model if provider == p.provider else DEFAULT_MODELS[provider]
        model_name = c2.text_input("Model", value=default_model, key=f"model-{provider}")
        if (provider, model_name) != (p.provider, p.model):
            p.provider, p.model = provider, model_name.strip() or DEFAULT_MODELS[provider]
        llm, err = state.get_llm()
        html_block(
            kv_list(
                [
                    ("Status", state.model_status_badge()),
                    ("Provider", esc(PROVIDER_LABELS.get(p.provider, p.provider))),
                    ("Model", esc(p.model)),
                ]
            )
        )
        if err:
            st.caption(f":red[{err}]")
        if st.button("Test connection", icon=":material/network_check:", disabled=llm is None):
            with st.spinner("Contacting provider…"):
                ok, msg = state.test_connection()
            if ok:
                st.success(msg, icon=":material/check_circle:")
            else:
                callout(msg, "warning")

    with retrieval, st.container(key="card-set-retrieval"):
        card_title("Retrieval", "How passages are selected as evidence for each analysis.")
        p.top_k = st.slider(
            "Passages per analysis",
            2,
            12,
            p.top_k,
            help="More passages give broader coverage but longer, slower analyses.",
        )
        mode = st.segmented_control(
            "Selection strategy",
            ["Balanced", "Strict relevance"],
            default="Balanced" if p.search_type == "mmr" else "Strict relevance",
            help="Balanced (MMR) avoids near-duplicate passages from repetitive documents. "
            "Strict relevance returns the closest matches only.",
        )
        p.search_type = "mmr" if mode != "Strict relevance" else "similarity"
        html_block(
            kv_list(
                [
                    ("Embedding model", esc(s.embedding_model)),
                    ("Segment size", f"{s.chunk_size:,} characters · {s.chunk_overlap} overlap"),
                    ("Conversation context", f"Last {s.memory_window} analyses"),
                ]
            )
        )
        st.caption(
            "Segment size and embedding model apply at indexing time and are set by the administrator "
            "via environment variables."
        )

    with workspace:
        files = state.pipeline().store.list_files()
        with st.container(key="card-set-ws"):
            card_title("Workspace", "Workspaces isolate documents, analyses and activity.")
            html_block(
                kv_list(
                    [
                        ("Name", esc(ws)),
                        ("Identifier", f"<code>{esc(state.current_workspace())}</code>"),
                        ("Documents", str(len(files))),
                        ("Pages", f"{sum(f['pages'] for f in files):,}"),
                        ("Storage", human_size(sum(f.get("file_size") or 0 for f in files))),
                    ]
                )
            )
            if st.button("Create new workspace", icon=":material/add:"):
                actions.new_workspace_dialog()
        st.space("small")
        with st.container(key="card-set-danger"):
            card_title("Danger zone", "Irreversible actions for this workspace.")
            c1, c2 = st.columns([3, 1.2], vertical_alignment="center")
            c1.markdown("**Clear all documents** — removes every document and its index from this workspace.")
            if c2.button("Clear workspace", icon=":material/delete_forever:", disabled=not files, width="stretch"):
                actions.confirm_clear_workspace()
