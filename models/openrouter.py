# QUESTION_GENERATION/models/openrouter.py
from __future__ import annotations
import os
import time
import requests
from typing import List

from .base import LlmModelService, ChatMessage, ChatOutput

# Ollama OpenAI-compatible endpoint
OLLAMA_OPENAI_URL = os.getenv(
    "OLLAMA_OPENAI_URL",
    "http://localhost:11434/v1/chat/completions"
)


class OpenRouterService(LlmModelService):
    """
    Drop-in replacement untuk service OpenRouter lama,
    sekarang pakai Ollama OpenAI-compatible API.

    Interface SENGAJA tetap sama:
      - __init__(alias_env_suffix: str)
      - chat(messages: List[ChatMessage], temperature=0.7) -> ChatOutput

    Konfigurasi model:
      OPENROUTER_MODEL_QWEN      = nama model di Ollama (mis. "qwen2.5:7b")
      OPENROUTER_MODEL_GEMMA     = nama model di Ollama (mis. "gemma3:4b-it-qat")
      OPENROUTER_MODEL_DEEPSEEK  = nama model di Ollama (mis. "deepseek-r1:7b")
    """

    def __init__(self, alias_env_suffix: str):
        self.alias = alias_env_suffix.upper()
        self.model = os.getenv(f"OPENROUTER_MODEL_{self.alias}")
        if not self.model:
            raise RuntimeError(
                f"OPENROUTER_MODEL_{self.alias} belum di-set "
                f"(isi dengan nama model Ollama, mis. 'qwen2.5:7b')."
            )

        # cuma label buat logging
        self.name = f"ollama_openai:{self.alias}:{self.model}"
        print(f"[OpenRouterService] init alias={self.alias} model={self.model} endpoint={OLLAMA_OPENAI_URL}")

    def chat(self, messages: List[ChatMessage], *, temperature: float = 0.7) -> ChatOutput:
        """
        Kirim chat ke Ollama (OpenAI-compatible) dan kembalikan ChatOutput.

        messages: list of {"role": "system"|"user"|"assistant", "content": "..."}
        temperature: forwarded ke Ollama.
        """
        headers = {
            "Content-Type": "application/json",
            # OpenAI-compat di Ollama butuh header Authorization, tapi nilainya bebas
            "Authorization": "Bearer ollama",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": float(temperature),
            "keep_alive": "1h",  # biar model nggak unload tiap request
            "options": {
                # JANGAN terlalu besar; ini angka masuk akal buat prompt kamu
                "num_ctx": 2048,      # konteks maksimum (prompt + output)
                "num_predict": 512,   # batasi panjang jawaban
                "num_thread": 8       # sesuaikan sama jumlah core CPU kamu
            },
        }
        
        t0 = time.time()
        resp = requests.post(OLLAMA_OPENAI_URL, headers=headers, json=payload, timeout=600)
        resp.raise_for_status()
        data = resp.json()

        text = (data["choices"][0]["message"]["content"] or "").strip()
        latency = int((time.time() - t0) * 1000)
        usage = data.get("usage") or {
            "backend": "ollama-openai",
            "model": self.model,
        }

        return ChatOutput(
            text=text,
            latency_ms=latency,
            usage=usage,
        )
