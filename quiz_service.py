# QUESTION_GENERATION/quiz_service.py
from __future__ import annotations
from typing import Dict
import time, os
from models.base import LlmModelService
from prompting import build_messages_single, TopicKey, PromptStructKey
from json_utils import extract_json_array
from normalize import normalize_quiz, extract_avoid_terms
from validator_gemini import verify_with_gemini

class QuizService:
    def __init__(self, model_map: Dict[str, LlmModelService]):
        self.model_map = model_map

    def _svc(self, key: str) -> LlmModelService:
        svc = self.model_map.get(key)
        if not svc:
            raise RuntimeError(f"Layanan '{key}' belum dikonfigurasi / API key kosong")
        return svc

    def ask_once(self, model_key: str, struktur: PromptStructKey, topic: TopicKey, temperature: float = 0.7) -> str:
        svc = self._svc(model_key)
        messages = build_messages_single(struktur, topic)
        out = svc.chat(messages, temperature=temperature)
        return out.text

    def generate_per_item_with_latency(
        self,
        topic: TopicKey,
        model_key: str,
        struktur: PromptStructKey = "struktur1",
        count: int = 4,
    ):
        svc = self._svc(model_key)
        avoid_set: set[str] = set()
        items: list[dict] = []
        started = time.time()

        for i in range(count):
            messages = build_messages_single(struktur, topic, list(avoid_set))

            # Patch khusus Gemini agar patuh JSON plain text
            if model_key.lower().startswith("gemini"):
                messages[0] = {
                    **messages[0],
                    "content": messages[0]["content"] + """
STRICT FOR GEMINI:
- Output plain text JSON; jangan gunakan LaTeX ($ atau backslash).
- "solution" berupa langkah ringkas 3–6 baris, plain text."""
                }

            # === SIMPAN PROMPT GENERATOR (PER ITEM) ===
            prompt_generator = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in messages])

            temperature_used = 0.4 if struktur == "struktur1" else 0.75
            out = svc.chat(messages, temperature=temperature_used)

            # parse hasil model generator
            try:
                quiz_arr = extract_json_array(out.text) or []
            except Exception:
                quiz_arr = []
            if isinstance(quiz_arr, list) and len(quiz_arr) > 1:
                quiz_arr = [quiz_arr[0]]
            if quiz_arr:
                quiz_arr = [normalize_quiz(quiz_arr[0])]

            # perbarui avoid terms
            stem = quiz_arr[0]["question"] if quiz_arr else None
            if stem:
                for t in extract_avoid_terms(stem):
                    avoid_set.add(t)

            # Verifier: nilai soal & solusi generator
            verifier_block = None
            if quiz_arr:
                q = quiz_arr[0]
                v = verify_with_gemini(
                    q["question"],
                    options=q.get("options"),
                    answer_key=q.get("answer"),
                    model_solution=q.get("solution"),
                )
                verifier_block = {
                    "model": v["model"],
                    "question": q["question"],
                    "solution_model": q.get("solution",""),
                    "solution_verifier": v["solution_verifier"],
                    "latencyMs": v["latencyMs"],
                    "usage": v["usage"],
                    "scores": v["scores"],
                    "notes": v["notes"],
                    "rawText": v["rawText"],
                }

            items.append({
                "index": i + 1,
                "latencyMs": out.latency_ms,
                "usage": out.usage or None,
                "rawText": out.text,
                "quiz": quiz_arr,
                "verifier": verifier_block,
                "prompt_generator": prompt_generator,   # ⬅️ disimpan per item
            })

            # jeda antar iter khusus Gemini untuk menurunkan risiko 429
            if model_key.lower().startswith("gemini"):
                gap = float(os.getenv("GEMINI_DELAY_BETWEEN_ITEMS", os.getenv("GEMINI_DELAY_BETWEEN_CALLS","1.0")))
                time.sleep(max(0.0, gap))

        total_elapsed_ms = int((time.time() - started) * 1000)
        last_prompt = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in build_messages_single(struktur, topic, list(avoid_set))])

        return {
            "topic": topic,
            "model": model_key,
            "struktur": struktur,
            "prompt": last_prompt,
            "totalElapsedMs": total_elapsed_ms,
            "items": items,
        }
