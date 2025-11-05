# QUESTION_GENERATION/models/base.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, TypedDict

class ChatMessage(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: str

@dataclass
class ChatOutput:
    text: str
    latency_ms: int
    usage: Dict[str, Any] | None = None

class LlmModelService:
    name: str
    def chat(self, messages: List[ChatMessage], *, temperature: float = 0.7) -> ChatOutput:
        raise NotImplementedError
