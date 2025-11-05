# QUESTION_GENERATION/main.py
# Tambahkan kolom CSV baru DI AKHIR untuk menyimpan prompt generator per item.
# Kolom-kolom yang sebelumnya TIDAK diubah urutannya.
from utils.load_env import run_load_env
run_load_env()

import os, pathlib, datetime, csv
from typing import Dict, List

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

def _ensure_dir(p: pathlib.Path): p.mkdir(parents=True, exist_ok=True)

def _rows_from_result(res: dict) -> List[dict]:
    topic = res.get("topic","")
    model = res.get("model","")
    struktur = res.get("struktur","")
    rows: List[dict] = []

    for item in res.get("items", []):
        quiz_list = item.get("quiz") or []
        qobj = quiz_list[0] if quiz_list else {}
        opts = qobj.get("options") or ["", "", "", ""]
        A = opts[0] if len(opts) > 0 else ""
        B = opts[1] if len(opts) > 1 else ""
        C = opts[2] if len(opts) > 2 else ""
        D = opts[3] if len(opts) > 3 else ""

        v = item.get("verifier") or {}
        s = v.get("scores") or {}
        row = {
            "topic": topic,
            "model": model,
            "struktur": struktur,
            "index": item.get("index",""),
            "latency_model_ms": item.get("latencyMs",""),
            "question": qobj.get("question",""),
            "optionA": A,
            "optionB": B,
            "optionC": C,
            "optionD": D,
            "answer": qobj.get("answer",""),
            "solution_model": qobj.get("solution",""),
            "solution_verifier": v.get("solution_verifier",""),
            "verifier_model": v.get("model",""),
            "latency_verifier_ms": v.get("latencyMs",""),
            "clarity": s.get("clarity",""),
            "context_accuracy": s.get("context_accuracy",""),
            "final_answer_accuracy": s.get("final_answer_accuracy",""),
            "quality_of_working": s.get("quality_of_working",""),
            "judge_notes": v.get("notes",""),
            # Kolom baru di akhir:
            "prompt_generator": item.get("prompt_generator",""),
        }
        rows.append(row)
    return rows

def _write_csv(path: pathlib.Path, rows: List[dict]):
    # Header lama dipertahankan urutannya; kolom baru ditambahkan PALING AKHIR.
    header = [
        "topic","model","struktur","index","latency_model_ms",
        "question","optionA","optionB","optionC","optionD",
        "answer","solution_model","solution_verifier",
        "verifier_model","latency_verifier_ms",
        "clarity","context_accuracy","final_answer_accuracy","quality_of_working","judge_notes",
        "prompt_generator",  # ⬅️ kolom baru di akhir
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)

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

    res = svc.generate_per_item_with_latency(
        topic=materi, model_key=model, struktur=struktur, count=count
    )

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = pathlib.Path(outdir) / materi / struktur
    _ensure_dir(out_path)
    csv_path = out_path / f"{model}_{ts}.csv"

    rows = _rows_from_result(res)
    _write_csv(csv_path, rows)
    print(f"[saved csv] {csv_path.as_posix()}")

    return res

if __name__ == "__main__":
    main("struktur3", "matematika", "qwen", count=2)
