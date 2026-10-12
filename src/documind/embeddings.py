"""Sentence-Transformers embeddings via LangChain.

The model is loaded once per process (``lru_cache``); in Streamlit we also wrap
the pipeline in ``st.cache_resource`` so reruns don't reload it.
"""

from __future__ import annotations

from functools import lru_cache

from langchain_core.embeddings import Embeddings


@lru_cache(maxsize=4)
def get_embeddings(model_name: str, device: str = "cpu") -> Embeddings:
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": device},
        # Normalised vectors -> cosine similarity == dot product.
        encode_kwargs={"normalize_embeddings": True, "batch_size": 32},
    )
