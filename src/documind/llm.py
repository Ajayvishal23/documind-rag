"""LLM provider factory.

Supported providers (pick with ``LLM_PROVIDER``):

* ``groq``   – free tier, very fast (needs ``GROQ_API_KEY``)
* ``openai`` – any OpenAI model (needs ``OPENAI_API_KEY``)
* ``ollama`` – fully local, no key (needs a running Ollama server)

Imports are lazy so you only install the provider package you use.
"""

from __future__ import annotations

import os

from langchain_core.language_models.chat_models import BaseChatModel

from documind.config import DEFAULT_MODELS, Settings


class LLMConfigError(RuntimeError):
    """Raised when the selected provider is not configured."""


def build_llm(settings: Settings, streaming: bool = True) -> BaseChatModel:
    provider = settings.llm_provider
    model = settings.llm_model or DEFAULT_MODELS.get(provider, "")
    temp = settings.llm_temperature

    if provider == "groq":
        if not os.getenv("GROQ_API_KEY"):
            raise LLMConfigError("GROQ_API_KEY is not set. Get a free key at https://console.groq.com/keys")
        from langchain_groq import ChatGroq

        return ChatGroq(model=model, temperature=temp, streaming=streaming)

    if provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            raise LLMConfigError("OPENAI_API_KEY is not set.")
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=model, temperature=temp, streaming=streaming)

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(model=model, temperature=temp, base_url=settings.ollama_base_url)

    raise LLMConfigError(f"Unknown LLM_PROVIDER '{provider}'. Use groq, openai or ollama.")
