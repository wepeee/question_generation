# QUESTION_GENERATION/models/openrouter.py
from __future__ import annotations
import os, time, requests
from typing import List
from .base import LlmModelService, ChatMessage, ChatOutput

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

class OpenRouterService(LlmModelService):
    """
    Generic service untuk model-model via OpenRouter.
    Gunakan env:
      OPENROUTER_API_KEY
      OPENROUTER_MODEL_<ALIAS> (contoh: OPENROUTER_MODEL_QWEN, OPENROUTER_MODEL_GEMMA, OPENROUTER_MODEL_DEEPSEEK)
    """
    def __init__(self, alias_env_suffix: str):
        self.alias = alias_env_suffix.upper()
        self.model = os.getenv(f"OPENROUTER_MODEL_{self.alias}")
        if not self.model:
            raise RuntimeError(f"OPENROUTER_MODEL_{self.alias} belum di-set")
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY belum di-set")
        self.name = f"openrouter:{self.alias}:{self.model}"

    def chat(self, messages: List[ChatMessage], *, temperature: float = 0.7) -> ChatOutput:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": float(temperature),
        }
        t0 = time.time()
        r = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=120)
        r.raise_for_status()
        data = r.json()
        text = (data["choices"][0]["message"]["content"] or "").strip()
        latency = int((time.time() - t0) * 1000)
        usage = data.get("usage")
        return ChatOutput(text=text, latency_ms=latency, usage=usage)
