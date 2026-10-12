"""Prompt templates.

Two-step conversational RAG:
1. CONDENSE – rewrite a follow-up ("what about its limitations?") into a
   standalone question using chat history, so retrieval sees the full intent.
2. ANSWER   – answer strictly from numbered context blocks and cite them as [n].
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

CONDENSE_SYSTEM = (
    "Given the chat history and the latest user message, rewrite the latest message "
    "as a single standalone question that can be understood without the history. "
    "Resolve pronouns and references (it, they, that paper, the second one). "
    "Do NOT answer the question. If it is already standalone, return it unchanged. "
    "Output only the question."
)

CONDENSE_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", CONDENSE_SYSTEM),
        MessagesPlaceholder("history"),
        ("human", "{question}"),
    ]
)

ANSWER_SYSTEM = """You are DocuMind, a precise research assistant that answers questions \
about the user's uploaded PDF documents.

Rules:
- Use ONLY the information in the numbered context blocks below. Never invent facts.
- Cite every factual claim with the block number in square brackets, e.g. [1] or [2][4].
- If the context does not contain the answer, say: "I couldn't find that in the uploaded \
documents." Then briefly mention what the documents do cover, if relevant.
- When documents disagree, point out the disagreement and cite both.
- Be concise and well structured. Use Markdown (bullet lists, bold, tables) when it helps.
- You may use the conversation history to understand the question, but facts must come \
from the context.

Context:
{context}"""

ANSWER_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", ANSWER_SYSTEM),
        MessagesPlaceholder("history"),
        ("human", "{question}"),
    ]
)
