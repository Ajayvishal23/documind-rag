"""ChromaDB persistence layer.

Wraps ``langchain_chroma.Chroma`` with the few operations the app needs:
add (idempotent), dedupe by file hash, list / delete documents, and search.
"""

from __future__ import annotations

import logging
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

logger = logging.getLogger(__name__)

_BATCH = 256  # Chroma has a max batch size; stay well under it.


class VectorStore:
    def __init__(self, embeddings: Embeddings, persist_dir: Path | str | None, collection: str) -> None:
        kwargs: dict = {
            "collection_name": collection,
            "embedding_function": embeddings,
            "collection_metadata": {"hnsw:space": "cosine"},
        }
        if persist_dir is not None:
            Path(persist_dir).mkdir(parents=True, exist_ok=True)
            kwargs["persist_directory"] = str(persist_dir)
        self._db = Chroma(**kwargs)

    # ------------------------------------------------------------------ write
    def add_chunks(self, chunks: list[Document]) -> int:
        if not chunks:
            return 0
        ids = [c.metadata["chunk_id"] for c in chunks]
        # De-duplicate ids within the batch (identical text at identical offset).
        seen: set[str] = set()
        uniq_docs, uniq_ids = [], []
        for doc, id_ in zip(chunks, ids, strict=True):
            if id_ not in seen:
                seen.add(id_)
                uniq_docs.append(doc)
                uniq_ids.append(id_)
        for i in range(0, len(uniq_docs), _BATCH):
            self._db.add_documents(uniq_docs[i : i + _BATCH], ids=uniq_ids[i : i + _BATCH])
        return len(uniq_docs)

    def has_file(self, file_hash: str) -> bool:
        got = self._db.get(where={"file_hash": file_hash}, limit=1, include=[])
        return bool(got.get("ids"))

    def delete_file(self, file_hash: str) -> None:
        self._db.delete(where={"file_hash": file_hash})

    def reset(self) -> None:
        self._db.reset_collection()

    # ------------------------------------------------------------------- read
    def list_files(self) -> list[dict]:
        """Return one row per ingested file: name, hash, pages, chunks."""
        got = self._db.get(include=["metadatas"])
        files: dict[str, dict] = {}
        for meta in got.get("metadatas") or []:
            h = meta.get("file_hash", "?")
            row = files.setdefault(
                h,
                {"file_name": meta.get("source", "?"), "file_hash": h,
                 "pages": meta.get("total_pages", 0), "chunks": 0},
            )
            row["chunks"] += 1
        return sorted(files.values(), key=lambda r: r["file_name"].lower())

    def count(self) -> int:
        return self._db._collection.count()  # noqa: SLF001

    def search(
        self,
        query: str,
        k: int = 5,
        search_type: str = "mmr",
        fetch_k: int = 20,
        file_hashes: list[str] | None = None,
    ) -> list[tuple[Document, float | None]]:
        """Semantic search. Returns (doc, relevance score or None for MMR)."""
        if self.count() == 0:
            return []
        flt = None
        if file_hashes:
            flt = {"file_hash": file_hashes[0]} if len(file_hashes) == 1 else {"file_hash": {"$in": file_hashes}}

        if search_type == "mmr":
            docs = self._db.max_marginal_relevance_search(
                query, k=k, fetch_k=max(fetch_k, k), lambda_mult=0.6, filter=flt
            )
            return [(d, None) for d in docs]
        return self._db.similarity_search_with_relevance_scores(query, k=k, filter=flt)
