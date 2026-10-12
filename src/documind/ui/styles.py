"""Custom CSS for a clean, ChatGPT-style layout."""

CSS = """
<style>
/* Centre the conversation column like ChatGPT */
.block-container { max-width: 860px; padding-top: 2rem; padding-bottom: 6rem; }

/* Chat bubbles */
[data-testid="stChatMessage"] { border-radius: 14px; padding: 0.9rem 1rem; margin-bottom: 0.4rem; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background: rgba(127,127,127,0.08);
}

/* Citation chips */
.dm-chip {
    display: inline-block; padding: 2px 10px; margin: 2px 4px 2px 0;
    border-radius: 999px; font-size: 0.78rem; font-weight: 500;
    background: rgba(16,163,127,0.12); color: #10a37f; border: 1px solid rgba(16,163,127,0.35);
}
.dm-snippet { font-size: 0.85rem; opacity: 0.85; border-left: 3px solid #10a37f;
              padding-left: 0.6rem; margin: 0.2rem 0 0.8rem 0; }

/* Hero on empty state */
.dm-hero { text-align: center; margin-top: 12vh; }
.dm-hero h1 { font-size: 2.2rem; margin-bottom: 0.2rem; }
.dm-hero p { opacity: 0.7; }

/* Sidebar file rows */
.dm-file { font-size: 0.85rem; padding: 4px 0; border-bottom: 1px solid rgba(127,127,127,0.15); }
.dm-file small { opacity: 0.6; }
</style>
"""
