# QUESTION_GENERATION/models/groq.py
from __future__ import annotations
import os, time, requests
from typing import List
from .base import LlmModelService, ChatMessage, ChatOutput

# Groq OpenAI-compatible endpoint
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

class GroqService(LlmModelService):
    """
    Env:
      GROQ_API_KEY
      GROQ_MODEL (mis. 'qwen-2.5-72b-instruct', 'llama-3.1-70b-versatile', dll)
    """
    def __init__(self, model_env: str = "GROQ_MODEL"):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY belum di-set")
        self.model = os.getenv(model_env)
        if not self.model:
            raise RuntimeError(f"{model_env} belum di-set")
        self.name = f"groq:{self.model}"

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
        r = requests.post(GROQ_URL, headers=headers, json=payload, timeout=120)
        r.raise_for_status()
        data = r.json()
        text = (data["choices"][0]["message"]["content"] or "").strip()
        latency = int((time.time() - t0) * 1000)
        usage = data.get("usage")
        return ChatOutput(text=text, latency_ms=latency, usage=usage)
