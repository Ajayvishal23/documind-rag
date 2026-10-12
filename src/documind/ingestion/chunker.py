"""Document chunking.

``RecursiveCharacterTextSplitter`` tries paragraph → line → sentence → word
boundaries in order, so chunks stay semantically coherent. Page metadata is
inherited by every chunk, and each chunk gets a deterministic id so re-ingesting
the same file is idempotent.
"""

from __future__ import annotations

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

SEPARATORS = ["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ", ""]


def build_splitter(chunk_size: int, chunk_overlap: int) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=SEPARATORS,
        length_function=len,
        add_start_index=True,
    )


def chunk_documents(docs: list[Document], chunk_size: int, chunk_overlap: int) -> list[Document]:
    """Split page documents into overlapping chunks with stable ids."""
    splitter = build_splitter(chunk_size, chunk_overlap)
    chunks = splitter.split_documents(docs)
    for n, chunk in enumerate(chunks):
        meta = chunk.metadata
        meta["chunk_id"] = f"{meta.get('file_hash', 'nohash')[:16]}-p{meta.get('page', 0)}-{meta.get('start_index', n)}"
    return chunks
