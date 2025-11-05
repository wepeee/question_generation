# QUESTION_GENERATION/models/gemini.py  — perbaikan konversi usage_metadata (tanpa _asdict)
# -*- coding: utf-8 -*-
import os, time
from typing import List
from .base import LlmModelService, ChatMessage, ChatOutput

import google.generativeai as genai

def _usage_to_dict(usage) -> dict | None:
    if usage is None:
        return None
    fields = (
        "prompt_token_count",
        "candidates_token_count",
        "total_token_count",
        "input_token_count",
        "output_token_count",
        "cached_input_token_count",
    )
    out = {k: getattr(usage, k) for k in fields if hasattr(usage, k)}
    return out or {"repr": repr(usage)}

class GeminiService(LlmModelService):
    def __init__(self, model: str | None = None, api_key_env: str = "GEMINI_API_KEY"):
        key = os.getenv(api_key_env)
        if not key:
            raise RuntimeError("GEMINI_API_KEY kosong")
        genai.configure(api_key=key)
        self.model_name = model or os.getenv("GEMINI_MODEL","gemini-2.0-flash")
        self.name = f"gemini:{self.model_name}"
        self._model = genai.GenerativeModel(self.model_name)

    def chat(self, messages: List[ChatMessage], *, temperature: float = 0.7) -> ChatOutput:
        sys = "\n".join([m["content"] for m in messages if m["role"] == "system"])
        user = "\n".join([m["content"] for m in messages if m["role"] == "user"])
        start = time.time()
        resp = self._model.generate_content(
            [{"role":"user","parts":[(sys + "\n\n" + user) if sys else user]}],
            generation_config={"temperature": float(temperature)}
        )

        # Ambil teks aman
        text = (getattr(resp, "text", None) or "").strip()
        if not text and getattr(resp, "candidates", None):
            for c in resp.candidates:
                if getattr(c, "content", None) and getattr(c.content, "parts", None):
                    for p in c.content.parts:
                        if getattr(p, "text", None):
                            text = p.text.strip()
                            break
                if text:
                    break

        latency = int((time.time() - start)*1000)
        usage_dict = _usage_to_dict(getattr(resp, "usage_metadata", None))
        return ChatOutput(text=text, latency_ms=latency, usage=usage_dict)
