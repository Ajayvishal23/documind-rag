"""Windowed conversation memory.

Keeps the last ``window`` user/assistant turns as LangChain messages. A sliding
window bounds prompt size (and cost) while giving the model enough context for
follow-up questions. One instance lives in each Streamlit session.
"""

from __future__ import annotations

from collections import deque

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage


class ConversationMemory:
    def __init__(self, window: int = 6) -> None:
        if window < 0:
            raise ValueError("window must be >= 0")
        self.window = window
        self._turns: deque[tuple[str, str]] = deque(maxlen=window or None)

    def add_turn(self, user: str, assistant: str) -> None:
        if self.window == 0:
            return
        self._turns.append((user, assistant))

    def messages(self) -> list[BaseMessage]:
        out: list[BaseMessage] = []
        for user, assistant in self._turns:
            out.append(HumanMessage(content=user))
            out.append(AIMessage(content=assistant))
        return out

    def clear(self) -> None:
        self._turns.clear()

    def __len__(self) -> int:
        return len(self._turns)
