"""Presentation helpers: HTML building blocks + small Streamlit wrappers.

All user- or document-derived strings are HTML-escaped before interpolation.
"""

from __future__ import annotations

import base64
import html
import re
from datetime import datetime, timezone

import streamlit as st

from documind.activity import ActivityEvent
from documind.schemas import SourceCitation

# --------------------------------------------------------------------------- icons
# Minimal stroke icons (Lucide-style, MIT). 16px, currentColor.
_ICON_PATHS = {
    "file": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>',
    "layers": '<path d="m12 3 9 5-9 5-9-5z"/><path d="m3 13 9 5 9-5"/>',
    "pages": '<rect x="4" y="3" width="13" height="17" rx="2"/><path d="M8 21h11a2 2 0 0 0 2-2V7"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    "chart": '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    "upload": '<path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/>',
    "trash": '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12M9 7V4h6v3"/>',
    "check": '<path d="M5 12.5 10 17 19 7"/>',
    "alert": '<path d="M12 9v4M12 17h.01"/>'
    '<path d="M10.3 3.9 2.5 17.5A2 2 0 0 0 4.2 20.5h15.6a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>',
    "folder": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "book": '<path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z"/><path d="M4 19V5"/>',
    "inbox": '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.5 5h13L22 12v6a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-6z"/>',
}
_FEED_COLOR = {
    "upload": "#2563EB",
    "analysis": "#1E293B",
    "delete": "#DC2626",
    "upload_failed": "#DC2626",
    "workspace_cleared": "#DC2626",
    "workspace_created": "#2563EB",
}
_FEED_ICON = {
    "upload": "upload",
    "analysis": "search",
    "delete": "trash",
    "upload_failed": "alert",
    "workspace_cleared": "trash",
    "workspace_created": "folder",
}


def icon(name: str, size: int = 16, color: str = "#2563EB") -> str:
    """Inline icon as a data-URI <img> (st.html's sanitizer strips raw <svg>)."""
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        f"{_ICON_PATHS.get(name, '')}</svg>"
    )
    data = base64.b64encode(svg.encode()).decode()
    return f'<img class="dm-ico" alt="" width="{size}" height="{size}" src="data:image/svg+xml;base64,{data}">'


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def html_block(markup: str) -> None:
    st.html(markup)


# --------------------------------------------------------------------------- formatting
def human_size(n: int | float | None) -> str:
    if not n:
        return "—"
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def parse_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def fmt_date(ts: str | None) -> str:
    dt = parse_ts(ts)
    return dt.strftime("%b %d, %Y") if dt else "—"


def rel_time(ts: str | datetime | None) -> str:
    dt = parse_ts(ts) if isinstance(ts, str) or ts is None else ts
    if not dt:
        return "—"
    secs = (datetime.now(timezone.utc) - dt).total_seconds()
    if secs < 60:
        return "just now"
    if secs < 3600:
        return f"{int(secs // 60)}m ago"
    if secs < 86400:
        return f"{int(secs // 3600)}h ago"
    if secs < 7 * 86400:
        return f"{int(secs // 86400)}d ago"
    return dt.strftime("%b %d")


def workspace_label(slug: str) -> str:
    return slug.replace("-", " ").replace("_", " ").strip().title() or "Workspace"


def initials(name: str) -> str:
    parts = [p for p in re.split(r"\s+", name.strip()) if p]
    return ("".join(p[0] for p in parts[:2]) or "U").upper()


# --------------------------------------------------------------------------- layout blocks
def page_header(title: str, subtitle: str = "", crumbs: list[str] | None = None) -> None:
    crumb_html = ""
    if crumbs:
        parts = [f"<span>{esc(c)}</span>" for c in crumbs[:-1]] + [f'<span class="current">{esc(crumbs[-1])}</span>']
        crumb_html = '<nav class="dm-breadcrumb">' + '<span class="sep">/</span>'.join(parts) + "</nav>"
    sub = f'<p class="dm-page-sub">{esc(subtitle)}</p>' if subtitle else ""
    html_block(f'{crumb_html}<h1 class="dm-page-title">{esc(title)}</h1>{sub}')


def card_title(title: str, subtitle: str = "") -> None:
    sub = f'<p class="dm-card-sub">{esc(subtitle)}</p>' if subtitle else ""
    html_block(f'<div><p class="dm-card-title">{esc(title)}</p>{sub}</div>')


def stat_card(label: str, value: str, foot: str = "", icon_name: str = "file") -> str:
    return (
        f'<div class="dm-stat"><div class="dm-stat-top"><span class="dm-stat-label">{esc(label)}</span>'
        f'<span class="dm-stat-icon">{icon(icon_name)}</span></div>'
        f'<div class="dm-stat-value">{esc(value)}</div><div class="dm-stat-foot">{foot}</div></div>'
    )


def badge(text: str, tone: str = "neutral") -> str:
    return f'<span class="dm-badge {tone}">{esc(text)}</span>'


def empty_state(title: str, body: str, icon_name: str = "inbox") -> None:
    html_block(
        f'<div class="dm-empty"><div class="dm-empty-icon">{icon(icon_name, 22, "#64748B")}</div>'
        f"<h4>{esc(title)}</h4><p>{esc(body)}</p></div>"
    )


def skeleton(lines: int = 4, status: str = "") -> str:
    status_html = f'<div class="dm-status-line"><span class="dm-spinner"></span>{esc(status)}</div>' if status else ""
    widths = [92, 100, 84, 96, 70, 88]
    bars = "".join(f'<span class="dm-skel" style="width:{widths[i % len(widths)]}%"></span>' for i in range(lines))
    return f'<div>{status_html}<span class="dm-skel h"></span>{bars}</div>'


def callout(text: str, tone: str = "info") -> None:
    ico = icon("alert", 16, "#B45309") if tone == "warning" else icon("book", 16, "#1E40AF")
    html_block(f'<div class="dm-callout {tone}">{ico}<div>{text}</div></div>')


def kv_list(rows: list[tuple[str, str]]) -> str:
    return "".join(f'<div class="dm-kv"><span>{esc(k)}</span><span>{v}</span></div>' for k, v in rows)


def file_cell(name: str, sub: str = "") -> str:
    return (
        f'<div class="dm-file"><span class="dm-file-icon">PDF</span><div style="min-width:0">'
        f'<div class="dm-file-name" title="{esc(name)}">{esc(name)}</div>'
        f'<div class="dm-file-sub">{esc(sub)}</div></div></div>'
    )


def documents_table(files: list[dict]) -> str:
    rows = "".join(
        f"<tr><td>{file_cell(f['file_name'], human_size(f.get('file_size')))}</td>"
        f'<td class="dm-hide-sm"><span class="dm-tag">PDF</span></td>'
        f'<td class="dm-hide-sm">{fmt_date(f.get("uploaded_at"))}</td>'
        f"<td>{badge('Indexed', 'success')}</td></tr>"
        for f in files
    )
    return (
        '<table class="dm-table"><thead><tr><th>File name</th><th class="dm-hide-sm">Type</th>'
        '<th class="dm-hide-sm">Uploaded</th><th>Status</th></tr></thead>'
        f"<tbody>{rows}</tbody></table>"
    )


def activity_feed(events: list[ActivityEvent], group_by_day: bool = False) -> str:
    out, last_group = [], None
    today = datetime.now(timezone.utc).date()
    for ev in events:
        if group_by_day:
            d = ev.timestamp.date()
            delta = (today - d).days
            group = "Today" if delta == 0 else "Yesterday" if delta == 1 else d.strftime("%A, %b %d")
            if group != last_group:
                if out:
                    out.append("</ul>")
                out.append(f'<div class="dm-feed-group">{esc(group)}</div><ul class="dm-feed">')
                last_group = group
        elif not out:
            out.append('<ul class="dm-feed">')
        feed_icon = icon(_FEED_ICON.get(ev.kind, "clock"), 14, _FEED_COLOR.get(ev.kind, "#64748B"))
        out.append(
            f'<li><span class="dm-feed-icon {esc(ev.kind)}">{feed_icon}</span>'
            f'<div class="dm-feed-body"><div class="dm-feed-title">{esc(ev.label)} · {esc(ev.title)}</div>'
            f'<div class="dm-feed-detail">{esc(ev.detail)}</div></div>'
            f'<span class="dm-feed-time">{rel_time(ev.timestamp)}</span></li>'
        )
    if out:
        out.append("</ul>")
    return "".join(out)


def reference_card(c: SourceCitation) -> str:
    score = ""
    if c.score is not None:
        pct = max(0, min(100, round(c.score * 100)))
        score = (
            f'<div class="dm-ref-score">Relevance<span class="dm-ref-bar"><span style="width:{pct}%"></span>'
            f"</span>{pct}%</div>"
        )
    return (
        f'<div class="dm-ref"><div class="dm-ref-head"><span class="dm-ref-num">{c.index}</span>'
        f'<span class="dm-ref-file" title="{esc(c.file_name)}">{esc(c.file_name)}</span>'
        f'<span class="dm-ref-page">Page {c.page}</span></div>'
        f'<div class="dm-ref-snip">{esc(c.snippet)}</div>{score}</div>'
    )


_CITE = re.compile(r"\[(\d{1,3})\]")


def format_answer(answer: str) -> str:
    """Make LLM markdown safe to render with HTML enabled, and style [n] markers."""
    safe = answer.replace("&", "&amp;").replace("<", "&lt;")
    return _CITE.sub(r'<span class="dm-cite">\1</span>', safe)
