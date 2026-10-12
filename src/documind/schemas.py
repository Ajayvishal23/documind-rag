"""Typed data objects shared across layers."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SourceCitation:
    """A single piece of evidence shown to the user under an answer."""

    index: int  # the [n] marker used in the answer
    file_name: str
    page: int  # 1-based page number
    snippet: str
    score: float | None = None

    @property
    def label(self) -> str:
        return f"[{self.index}] {self.file_name} — p.{self.page}"


@dataclass
class ChatAnswer:
    """What the pipeline returns for one user turn."""

    question: str
    standalone_question: str
    answer: str
    sources: list[SourceCitation] = field(default_factory=list)


@dataclass(frozen=True)
class IngestReport:
    """Outcome of ingesting one PDF."""

    file_name: str
    pages: int
    chunks: int
    skipped: bool = False
    reason: str = ""
