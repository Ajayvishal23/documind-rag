"""Append-only activity log, one JSON-lines file per workspace.

Powers the dashboard statistics, the recent-activity feed, notifications and
the audit-style Activity page. Deliberately simple: no database, safe to delete.
"""

from __future__ import annotations

import json
import logging
import re
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)
_LOCK = threading.Lock()

EVENT_LABELS = {
    "upload": "Document indexed",
    "upload_failed": "Upload skipped",
    "delete": "Document removed",
    "analysis": "Analysis completed",
    "workspace_cleared": "Workspace cleared",
    "workspace_created": "Workspace created",
}


@dataclass
class ActivityEvent:
    kind: str
    title: str
    detail: str = ""
    meta: dict = field(default_factory=dict)
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    @property
    def timestamp(self) -> datetime:
        return datetime.fromisoformat(self.ts)

    @property
    def label(self) -> str:
        return EVENT_LABELS.get(self.kind, self.kind.replace("_", " ").title())


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", name) or "default"


class ActivityLog:
    def __init__(self, root: Path | str, workspace: str) -> None:
        self.path = Path(root) / f"{_safe(workspace)}.jsonl"

    def record(self, kind: str, title: str, detail: str = "", **meta) -> ActivityEvent:
        event = ActivityEvent(kind=kind, title=title, detail=detail, meta=meta)
        try:
            with _LOCK:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(asdict(event)) + "\n")
        except OSError as exc:  # activity is best-effort; never break the app
            logger.warning("Could not write activity log: %s", exc)
        return event

    def events(self, limit: int | None = None, kinds: set[str] | None = None) -> list[ActivityEvent]:
        """Newest first."""
        if not self.path.exists():
            return []
        out: list[ActivityEvent] = []
        with self.path.open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    ev = ActivityEvent(**json.loads(line))
                except (json.JSONDecodeError, TypeError):
                    continue
                if kinds is None or ev.kind in kinds:
                    out.append(ev)
        out.reverse()
        return out[:limit] if limit else out

    def count(self, kind: str) -> int:
        return len(self.events(kinds={kind}))

    def clear(self) -> None:
        self.path.unlink(missing_ok=True)
