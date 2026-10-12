"""The RAG pipeline: ingest → retrieve → answer with citations.

This class is UI-agnostic; ``app.py`` is a thin Streamlit layer on top of it,
which keeps the core logic unit-testable and reusable (CLI, FastAPI, etc.).
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from dataclasses import dataclass

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser

from documind.config import Settings
from documind.ingestion import PDFExtractionError, chunk_documents, file_sha256, load_pdf_bytes
from documind.memory import ConversationMemory
from documind.prompts import ANSWER_PROMPT, CONDENSE_PROMPT
from documind.schemas import ChatAnswer, IngestReport, SourceCitation
from documind.vectorstore import VectorStore

logger = logging.getLogger(__name__)

_CITE_RE = re.compile(r"\[(\d+)\]")
NO_DOCS_MESSAGE = "Please upload at least one PDF in the sidebar so I have something to answer from."


def format_context(docs: list[Document]) -> str:
    """Render retrieved chunks as numbered blocks the LLM can cite."""
    blocks = []
    for i, d in enumerate(docs, start=1):
        src = d.metadata.get("source", "unknown")
        page = d.metadata.get("page", "?")
        blocks.append(f"[{i}] (source: {src}, page {page})\n{d.page_content}")
    return "\n\n---\n\n".join(blocks)


def cited_indices(answer: str, n_sources: int) -> list[int]:
    """Indices actually cited in the answer, in order of first appearance."""
    seen: list[int] = []
    for m in _CITE_RE.finditer(answer):
        i = int(m.group(1))
        if 1 <= i <= n_sources and i not in seen:
            seen.append(i)
    return seen


def build_citations(
    answer: str, hits: list[tuple[Document, float | None]], snippet_len: int = 280
) -> list[SourceCitation]:
    """Map [n] markers back to documents. Falls back to all hits if none cited."""
    idx = cited_indices(answer, len(hits)) or list(range(1, len(hits) + 1))
    out = []
    for i in idx:
        doc, score = hits[i - 1]
        text = doc.page_content.strip().replace("\n", " ")
        out.append(
            SourceCitation(
                index=i,
                file_name=doc.metadata.get("source", "unknown"),
                page=int(doc.metadata.get("page", 0)),
                snippet=text[:snippet_len] + ("…" if len(text) > snippet_len else ""),
                score=score,
            )
        )
    return out


@dataclass
class StreamingAnswer:
    """Handle returned by ``ask_stream``: iterate tokens, then call ``finalize``."""

    question: str
    standalone_question: str
    hits: list[tuple[Document, float | None]]
    tokens: Iterator[str]
    _pipeline: RAGPipeline
    _memory: ConversationMemory

    def finalize(self, full_answer: str) -> ChatAnswer:
        sources = build_citations(full_answer, self.hits) if self.hits else []
        self._memory.add_turn(self.question, full_answer)
        return ChatAnswer(self.question, self.standalone_question, full_answer, sources)


class RAGPipeline:
    def __init__(self, settings: Settings, embeddings: Embeddings, llm: BaseChatModel | None,
                 persist: bool = True) -> None:
        self.settings = settings
        self.llm = llm
        self.store = VectorStore(
            embeddings,
            settings.persist_dir if persist else None,
            settings.collection_name,
        )

    # -------------------------------------------------------------- ingestion
    def ingest_pdf(self, data: bytes, file_name: str) -> IngestReport:
        max_bytes = self.settings.max_file_mb * 1024 * 1024
        if len(data) > max_bytes:
            return IngestReport(file_name, 0, 0, skipped=True, reason=f"larger than {self.settings.max_file_mb} MB")

        if self.store.has_file(file_sha256(data)):
            return IngestReport(file_name, 0, 0, skipped=True, reason="already indexed")

        try:
            pages = load_pdf_bytes(data, file_name)
        except PDFExtractionError as exc:
            return IngestReport(file_name, 0, 0, skipped=True, reason=str(exc))

        if not pages:
            return IngestReport(file_name, 0, 0, skipped=True,
                                reason="no extractable text (scanned PDF? try OCR first)")

        chunks = chunk_documents(pages, self.settings.chunk_size, self.settings.chunk_overlap)
        added = self.store.add_chunks(chunks)
        logger.info("Indexed %s: %d pages → %d chunks", file_name, len(pages), added)
        return IngestReport(file_name, pages[0].metadata["total_pages"], added)

    # -------------------------------------------------------------- retrieval
    def condense(self, question: str, memory: ConversationMemory) -> str:
        """Rewrite a follow-up into a standalone question (skipped on turn 1)."""
        if len(memory) == 0 or self.llm is None:
            return question
        chain = CONDENSE_PROMPT | self.llm | StrOutputParser()
        try:
            rewritten = chain.invoke({"history": memory.messages(), "question": question}).strip()
            return rewritten or question
        except Exception as exc:  # noqa: BLE001 – degrade gracefully
            logger.warning("Condense step failed, using raw question: %s", exc)
            return question

    def retrieve(self, query: str, file_hashes: list[str] | None = None) -> list[tuple[Document, float | None]]:
        s = self.settings
        hits = self.store.search(query, k=s.top_k, search_type=s.search_type, fetch_k=s.fetch_k,
                                 file_hashes=file_hashes)
        if s.search_type == "similarity" and s.score_threshold > 0:
            hits = [(d, sc) for d, sc in hits if sc is not None and sc >= s.score_threshold]
        return hits

    # -------------------------------------------------------------- answering
    def ask_stream(self, question: str, memory: ConversationMemory,
                   file_hashes: list[str] | None = None) -> StreamingAnswer:
        if self.llm is None:
            raise RuntimeError("No LLM configured")

        if self.store.count() == 0:
            return StreamingAnswer(question, question, [], iter([NO_DOCS_MESSAGE]), self, memory)

        standalone = self.condense(question, memory)
        hits = self.retrieve(standalone, file_hashes)
        if not hits:
            msg = "I couldn't find anything relevant in the uploaded documents."
            return StreamingAnswer(question, standalone, [], iter([msg]), self, memory)

        chain = ANSWER_PROMPT | self.llm | StrOutputParser()
        tokens = chain.stream({
            "context": format_context([d for d, _ in hits]),
            "history": memory.messages(),
            "question": question,
        })
        return StreamingAnswer(question, standalone, hits, tokens, self, memory)

    def ask(self, question: str, memory: ConversationMemory,
            file_hashes: list[str] | None = None) -> ChatAnswer:
        """Non-streaming convenience wrapper (used by tests / CLI)."""
        handle = self.ask_stream(question, memory, file_hashes)
        return handle.finalize("".join(handle.tokens))
