from utils.load_env import run_load_env
import os
run_load_env()
# print("[DEBUG] GEMINI_API_KEY prefix:", (os.getenv("GEMINI_API_KEY") or "")[:16])

import os, pathlib, datetime
from typing import Dict, Tuple

from models.base import LlmModelService
from models.gemini import GeminiService
from models.openrouter import OpenRouterService
from models.groq import GroqService

from quiz_service import QuizService

_ALLOWED_TOPICS = ("mathematics", "biology", "physics", "chemistry")

def _canon_topic(user_topic: str) -> Tuple[str, str]:
    key = (user_topic or "").strip().lower()
    if key not in _ALLOWED_TOPICS:
        raise RuntimeError(f"Unknown topic '{user_topic}'. Use one of: {', '.join(_ALLOWED_TOPICS)}.")
    return key, key

def _build_models() -> Dict[str, LlmModelService]:
    models: Dict[str, LlmModelService] = {}
    try:
        models["gemini"] = GeminiService(model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))
    except Exception as e:
        print("[warn] Gemini disabled:", e)

    # local models via Ollama
    for alias in ["QWEN", "GEMMA", "LLAMA", "PHI"]:
        try:
            models[alias.lower()] = OpenRouterService(alias)
        except Exception as e:
            print(f"[warn] {alias} disabled:", e)

    return models


def main(
    struktur: str,
    topic: str,
    model: str,
    *,
    count: int = 4,
    outdir: str = "outputs",
):
    models = _build_models()
    if model not in models:
        raise RuntimeError(f"Model '{model}' is not available. Check your environment variables.")

    internal_topic, topic_dir = _canon_topic(topic)

    svc = QuizService(models)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = pathlib.Path(outdir) / topic_dir / struktur
    out_path.mkdir(parents=True, exist_ok=True)
    csv_path = out_path / f"{model}_{ts}.csv"

    # Incremental mode: write each row; stop on verifier rate-limit (partial CSV preserved).
    svc.generate_items_incremental_to_csv(
        topic=internal_topic,
        model_key=model,
        struktur=struktur,
        count=count,
        csv_path=csv_path,
    )

    print(f"[csv incremental] {csv_path.as_posix()}")

if __name__ == "__main__":
    # example
    main("struktur3", "mathematics", "phi", count=50)
