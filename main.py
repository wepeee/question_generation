from utils.load_env import run_load_env
run_load_env()

import os, pathlib, datetime
from typing import Dict

from models.base import LlmModelService
from models.gemini import GeminiService
from models.openrouter import OpenRouterService
from models.groq import GroqService

from quiz_service import QuizService

def _build_models() -> Dict[str, LlmModelService]:
    models: Dict[str, LlmModelService] = {}
    try:
        models["gemini"] = GeminiService(model=os.getenv("GEMINI_MODEL","gemini-2.0-flash"))
    except Exception as e:
        print("[warn] Gemini disabled:", e)
    for alias in ["QWEN", "DEEPSEEK", "GEMMA"]:
        try:
            models[alias.lower()] = OpenRouterService(alias)
        except Exception as e:
            print(f"[warn] {alias} disabled:", e)
    try:
        models["groq"] = GroqService()
    except Exception as e:
        print("[info] Groq disabled:", e)
    return models

def main(
    struktur: str,
    materi: str,
    model: str,
    *,
    count: int = 4,
    outdir: str = "outputs",
):
    models = _build_models()
    if model not in models:
        raise RuntimeError(f"Model '{model}' belum tersedia. Aktifkan env yang diperlukan.")

    svc = QuizService(models)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = pathlib.Path(outdir) / materi / struktur
    out_path.mkdir(parents=True, exist_ok=True)
    csv_path = out_path / f"{model}_{ts}.csv"

    # === INCREMENTAL MODE ===
    # Tulis CSV per row; jika kena rate limit validator, proses berhenti otomatis
    svc.generate_items_incremental_to_csv(
        topic=materi,
        model_key=model,
        struktur=struktur,
        count=count,
        csv_path=csv_path,
    )

    print(f"[csv incremental] {csv_path.as_posix()}")

if __name__ == "__main__":
    # contoh eksekusi
    main("struktur1", "matematika", "deepseek", count=15)
