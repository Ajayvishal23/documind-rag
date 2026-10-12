"""PDF text extraction.

Uses ``pypdf`` (pure Python, no system deps) and keeps one LangChain
``Document`` per page so every chunk can later be cited by page number.
"""

from __future__ import annotations

import hashlib
import io
import logging
import re

from langchain_core.documents import Document
from pypdf import PdfReader
from pypdf.errors import PdfReadError

logger = logging.getLogger(__name__)


class PDFExtractionError(RuntimeError):
    """Raised when a PDF cannot be read at all."""


def file_sha256(data: bytes) -> str:
    """Stable content hash used for de-duplication."""
    return hashlib.sha256(data).hexdigest()


_WS = re.compile(r"[ \t]+")
_HYPHEN_BREAK = re.compile(r"(\w)-\n(\w)")
_MULTI_NL = re.compile(r"\n{3,}")


def clean_text(text: str) -> str:
    """Normalise whitespace and re-join words hyphenated across line breaks."""
    text = text.replace("\x00", "")
    text = _HYPHEN_BREAK.sub(r"\1\2", text)
    text = _WS.sub(" ", text)
    text = _MULTI_NL.sub("\n\n", text)
    return text.strip()


def load_pdf_bytes(data: bytes, file_name: str) -> list[Document]:
    """Extract text from an in-memory PDF.

    Returns one ``Document`` per non-empty page with metadata:
    ``source`` (file name), ``page`` (1-based), ``file_hash`` and ``total_pages``.
    """
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as exc:  # noqa: BLE001
                raise PDFExtractionError(f"{file_name} is password-protected") from exc
        pages = reader.pages
    except PdfReadError as exc:
        raise PDFExtractionError(f"Could not read {file_name}: {exc}") from exc

    file_hash = file_sha256(data)
    total = len(pages)
    docs: list[Document] = []
    for i, page in enumerate(pages, start=1):
        try:
            raw = page.extract_text() or ""
        except Exception as exc:  # noqa: BLE001 – one bad page shouldn't kill the file
            logger.warning("Failed to extract page %s of %s: %s", i, file_name, exc)
            continue
        text = clean_text(raw)
        if not text:
            continue
        docs.append(
            Document(
                page_content=text,
                metadata={
                    "source": file_name,
                    "page": i,
                    "file_hash": file_hash,
                    "total_pages": total,
                },
            )
        )
    logger.info("Extracted %d/%d text pages from %s", len(docs), total, file_name)
    return docs
