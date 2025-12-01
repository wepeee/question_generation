from __future__ import annotations
from typing import Dict, List, Any
import time, os, csv, pathlib
import json

from models.base import LlmModelService
from prompting import build_messages_single, TopicKey, PromptStructKey
from json_utils import extract_json_array
from normalize import normalize_quiz, extract_avoid_terms
from validator_gemini import verify_with_gemini

CSV_HEADER = [
    "topic","model","struktur","index","latency_model_ms",
    "question","optionA","optionB","optionC","optionD",
    "answer","solution_model","solution_verifier",
    "verifier_model","latency_verifier_ms",
    "clarity","context_accuracy","final_answer_accuracy","quality_of_working","judge_notes",
    "prompt_generator",
]

def _now() -> str:
    import time as _t
    return _t.strftime("%H:%M:%S")


def _extract_json_array_loose(text: str) -> List[Any]:
    """
    Fallback extractor yang lebih toleran:
    - hapus ```json / ``` kalau ada
    - cari substring [ ... ] pertama dengan bracket matching
    - coba json.loads
    - kalau hasilnya string, coba json.loads lagi
    """
    s = (text or "").strip()
    # buang code fences sederhana
    s = s.replace("```json", "").replace("```", "").strip()

    # coba dulu pake extractor bawaan
    try:
        arr = extract_json_array(s)
        if isinstance(arr, list) and arr:
            return arr
    except Exception:
        pass

    # manual cari [ ... ]
    start = s.find("[")
    if start == -1:
        return []

    depth = 0
    end = -1
    for i, ch in enumerate(s[start:], start=start):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                end = i
                break

    if end == -1:
        return []

    chunk = s[start:end+1].strip()
    try:
        arr = json.loads(chunk)
    except Exception:
        # mungkin double-encoded, mis. "[{\"question\":...}]"
        try:
            tmp = json.loads(chunk)
            if isinstance(tmp, str):
                arr = json.loads(tmp)
            else:
                return []
        except Exception:
            return []

    if isinstance(arr, list):
        return arr
    return []


class QuizService:
    def __init__(self, model_map: Dict[str, LlmModelService]):
        self.model_map = model_map

    def _svc(self, key: str) -> LlmModelService:
        svc = self.model_map.get(key)
        if not svc:
            raise RuntimeError(f"Layanan '{key}' belum dikonfigurasi / API key kosong")
        return svc

    def ask_once(
        self,
        model_key: str,
        struktur: PromptStructKey,
        topic: TopicKey,
        temperature: float = 0.7,
    ) -> str:
        svc = self._svc(model_key)
        messages = build_messages_single(struktur, topic)
        out = svc.chat(messages, temperature=temperature)
        return out.text

    def generate_items_incremental_to_csv(
        self,
        *,
        topic: TopicKey,
        model_key: str,
        struktur: PromptStructKey = "struktur1",
        count: int = 4,
        csv_path: pathlib.Path,
    ):
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        file_exists = csv_path.exists()
        f = csv_path.open("a", newline="", encoding="utf-8")
        w = csv.DictWriter(f, fieldnames=CSV_HEADER, extrasaction="ignore")
        if not file_exists:
            w.writeheader()
            f.flush()
            print(f"[{_now()}] CSV created: {csv_path.name}")

        svc = self._svc(model_key)
        avoid_set: set[str] = set()

        for i in range(count):
            qidx = i + 1

            messages = build_messages_single(struktur, topic, list(avoid_set))
            if model_key.lower().startswith("gemini"):
                messages[0] = {
                    **messages[0],
                    "content": messages[0]["content"]
                    + """
STRICT FOR GEMINI:
- Output plain-text JSON only; do not use LaTeX ($ or backslashes).
- The "solution" must be 3–6 lines, plain text."""
                }
            prompt_generator = "\n".join(
                [f"{m['role'].upper()}: {m['content']}" for m in messages]
            )

            print(
                f"[{_now()}] Generating question {qidx}/{count}...",
                end="",
                flush=True,
            )
            temperature_used = 0.4 if struktur == "struktur1" else 0.75
            out = svc.chat(messages, temperature=temperature_used)

            # ==== PARSE RESULT (LOOSE) ====
            quiz_arr: List[Any] = _extract_json_array_loose(out.text)
            if isinstance(quiz_arr, list) and len(quiz_arr) > 1:
                quiz_arr = [quiz_arr[0]]

            if not quiz_arr:
                print(" failed (no valid JSON array).", flush=True)
                if model_key.lower().startswith("gemini"):
                    gap = float(
                        os.getenv(
                            "GEMINI_DELAY_BETWEEN_ITEMS",
                            os.getenv("GEMINI_DELAY_BETWEEN_CALLS", "1.0"),
                        )
                    )
                    time.sleep(max(0.0, gap))
                continue

            raw_q = quiz_arr[0]
            if isinstance(raw_q, str):
                try:
                    raw_q = json.loads(raw_q)
                except Exception:
                    print(" failed (inner JSON not parseable).", flush=True)
                    continue

            if not isinstance(raw_q, dict):
                print(" failed (JSON element is not an object).", flush=True)
                continue

            q = normalize_quiz(raw_q)
            print(" done.", flush=True)

            opts = q.get("options") or ["", "", "", ""]
            A = opts[0] if len(opts) > 0 else ""
            B = opts[1] if len(opts) > 1 else ""
            C = opts[2] if len(opts) > 2 else ""
            D = opts[3] if len(opts) > 3 else ""

            row = {
                "topic": topic,
                "model": model_key,
                "struktur": struktur,
                "index": qidx,
                "latency_model_ms": out.latency_ms,
                "question": q.get("question", ""),
                "optionA": A,
                "optionB": B,
                "optionC": C,
                "optionD": D,
                "answer": q.get("answer", ""),
                "solution_model": q.get("solution", ""),
                "solution_verifier": "",
                "verifier_model": "",
                "latency_verifier_ms": "",
                "clarity": "",
                "context_accuracy": "",
                "final_answer_accuracy": "",
                "quality_of_working": "",
                "judge_notes": "",
                "prompt_generator": prompt_generator,
            }

            try:
                print(
                    f"[{_now()}] Verifying question {qidx} with Gemini Pro...",
                    end="",
                    flush=True,
                )
                v = verify_with_gemini(
                    q["question"],
                    options=q.get("options"),
                    answer_key=q.get("answer"),
                    model_solution=q.get("solution"),
                )
                s = v.get("scores") or {}
                row.update(
                    {
                        "solution_verifier": v.get("solution_verifier", ""),
                        "verifier_model": v.get("model", ""),
                        "latency_verifier_ms": v.get("latencyMs", ""),
                        "clarity": s.get("clarity", ""),
                        "context_accuracy": s.get("context_accuracy", ""),
                        "final_answer_accuracy": s.get(
                            "final_answer_accuracy", ""
                        ),
                        "quality_of_working": s.get("quality_of_working", ""),
                        "judge_notes": v.get("notes", ""),
                    }
                )
                print(" done.", flush=True)
            except Exception as e:
                print(
                    f" FAILED ({e}). Writing partial row and stopping.",
                    flush=True,
                )
                w.writerow(row)
                f.flush()
                f.close()
                print(
                    f"[{_now()}] Wrote partial row for question {qidx} to {csv_path.name}"
                )
                return

            w.writerow(row)
            f.flush()
            print(
                f"[{_now()}] Wrote question {qidx} to {csv_path.name}",
                flush=True,
            )

            stem = q.get("question")
            if stem:
                for t in extract_avoid_terms(stem):
                    avoid_set.add(t)

            if model_key.lower().startswith("gemini"):
                gap = float(
                    os.getenv(
                        "GEMINI_DELAY_BETWEEN_ITEMS",
                        os.getenv("GEMINI_DELAY_BETWEEN_CALLS", "1.0"),
                    )
                )
                time.sleep(max(0.0, gap))

        f.close()
        print(
            f"[{_now()}] Completed {count} questions. CSV saved: {csv_path.name}",
            flush=True,
        )

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
            if model_key.lower().startswith("gemini"):
                messages[0] = {
                    **messages[0],
                    "content": messages[0]["content"]
                    + """
STRICT FOR GEMINI:
- Output plain text JSON; jangan gunakan LaTeX ($ atau backslash).
- "solution" berupa langkah ringkas 3–6 baris, plain text."""
                }
            prompt_generator = "\n".join(
                [f"{m['role'].upper()}: {m['content']}" for m in messages]
            )
            temperature_used = 0.4 if struktur == "struktur1" else 0.75
            out = svc.chat(messages, temperature=temperature_used)

            quiz_arr = _extract_json_array_loose(out.text)
            if isinstance(quiz_arr, list) and len(quiz_arr) > 1:
                quiz_arr = [quiz_arr[0]]

            normalized_list: list[dict] = []
            if quiz_arr:
                raw_q = quiz_arr[0]
                if isinstance(raw_q, str):
                    try:
                        raw_q = json.loads(raw_q)
                    except Exception:
                        raw_q = None
                if isinstance(raw_q, dict):
                    normalized_list = [normalize_quiz(raw_q)]

            quiz_arr = normalized_list

            stem = quiz_arr[0]["question"] if quiz_arr else None
            if stem:
                for t in extract_avoid_terms(stem):
                    avoid_set.add(t)

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
                    "solution_model": q.get("solution", ""),
                    "solution_verifier": v["solution_verifier"],
                    "latencyMs": v["latencyMs"],
                    "usage": v["usage"],
                    "scores": v["scores"],
                    "notes": v["notes"],
                    "rawText": v["rawText"],
                }

            items.append(
                {
                    "index": i + 1,
                    "latencyMs": out.latency_ms,
                    "usage": out.usage or None,
                    "rawText": out.text,
                    "quiz": quiz_arr,
                    "verifier": verifier_block,
                    "prompt_generator": prompt_generator,
                }
            )

            if model_key.lower().startswith("gemini"):
                gap = float(
                    os.getenv(
                        "GEMINI_DELAY_BETWEEN_ITEMS",
                        os.getenv("GEMINI_DELAY_BETWEEN_CALLS", "1.0"),
                    )
                )
                time.sleep(max(0.0, gap))

        total_elapsed_ms = int((time.time() - started) * 1000)
        last_prompt = "\n".join(
            [
                f"{m['role'].upper()}: {m['content']}"
                for m in build_messages_single(
                    struktur, topic, list(avoid_set)
                )
            ]
        )

        return {
            "topic": topic,
            "model": model_key,
            "struktur": struktur,
            "prompt": last_prompt,
            "totalElapsedMs": total_elapsed_ms,
            "items": items,
        }
