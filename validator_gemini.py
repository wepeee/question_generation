# QUESTION_GENERATION/validator_gemini.py
# Verifier: Gemini 2.5 Pro — delay otomatis khusus "pro" agar tidak kena limit.
# - Skala skor: 0–5 (desimal boleh), FAA: "Benar"/"Salah"
# - Role messages (user/model) dipertahankan
# - Retry + backoff + parsing "Please retry in Xs"
# - Delay per-model: default 30s untuk *-pro (atur via GEMINI_PRO_DELAY_SEC)

import os, time, json, re, random
import google.generativeai as genai
from utils.load_env import run_load_env

run_load_env()

print("validator_gemini (with per-model delay for pro)")

SCHEMA = r"""
KELUARAN WAJIB: satu objek JSON persis seperti ini (tanpa teks lain):
{
  "solution_verifier": "solusi ringkas 3–8 baris hasil kerjamu sendiri, plain text; tanpa LaTeX/backslash/markdown",
  "scores": {
    "clarity": 0.0,
    "context_accuracy": 0.0,
    "quality_of_working": 0.0,
    "final_answer_accuracy": "Benar"  // atau "Salah"
  },
  "notes": "alasan singkat 3–6 baris untuk setiap skor (plain text)"
}
Ketentuan:
- Skor numerik berada pada rentang 0.0 sampai 5.0 (boleh desimal, mis. 1.35).
- Final Answer Accuracy hanya salah satu dari: "Benar" atau "Salah".
"""

SYSTEM_INSTRUCTION = (
    "Anda adalah verifikator/evaluator kualitas soal pilihan ganda.\n"
    "Ikuti prosedur ketat:\n"
    "  1) Selesaikan soal SECARA MANDIRI terlebih dahulu (abaikan solusi generator sampai selesai).\n"
    "  2) Setelah itu, evaluasi SOAL dan SOLUSI_GENERATOR secara independen pada 4 metrik.\n"
    "  3) Keluarkan hanya satu objek JSON persis sesuai skema; jangan tambahkan teks lain.\n"
)

# ===== utils =====
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

def _extract_json_object(text: str) -> dict | None:
    s = (text or "").strip()
    s = re.sub(r"```json|```", "", s, flags=re.I).strip()
    start = s.find("{")
    if start == -1:
        return None
    depth, end = 0, -1
    for i, ch in enumerate(s[start:], start=start):
        if ch == "{": depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i; break
    if end == -1:
        return None
    chunk = s[start:end+1]
    chunk = chunk.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    chunk = re.sub(r",\s*}", "}", chunk)
    try:
        return json.loads(chunk)
    except Exception:
        return None

def _build_messages_with_roles(
    question: str,
    options: list[str] | None,
    answer_key: str | None,
    model_solution: str | None
):
    opts_block = ""
    if options:
        opts_block = "Opsi:\n" + "\n".join(f"- {o}" for o in options) + "\n"
    key_block = f"Kunci (A/B/C/D jika ada): {answer_key or '-'}\n"

    user_1 = (
        "Soal berikut untuk dievaluasi. Selesaikan dulu secara mandiri, "
        "jangan gunakan solusi yang akan diberikan setelah ini.\n\n"
        f"Soal:\n{question}\n\n{opts_block}{key_block}"
    )
    model_msg = (
        "SOLUSI_GENERATOR (INI BUKAN jawabanmu; gunakan HANYA setelah kamu selesai mengerjakan mandiri):\n"
        f"{(model_solution or '').strip()}"
    )
    user_2 = (
        "Tugasmu:\n"
        "1) Selesaikan soalnya SECARA MANDIRI terlebih dahulu tanpa membaca SOLUSI_GENERATOR di atas.\n"
        "2) Setelah punya jawaban sendiri, nilai SOAL & SOLUSI_GENERATOR pada metrik berikut:\n"
        "   - Clarity (0–5, boleh desimal): kejelasan stem/notation/data.\n"
        "   - Context Accuracy (0–5): kesesuaian konteks & konsep; tanpa kontradiksi.\n"
        "   - Quality of Working (0–5): kualitas langkah/penalaran pada SOLUSI_GENERATOR (rumus, aritmetika, pembulatan, konsistensi).\n"
        "   - Final Answer Accuracy: \"Benar\" atau \"Salah\" — jawaban akhir pada SOLUSI_GENERATOR terhadap soalnya.\n"
        "3) Keluarkan HASIL dalam format JSON berikut, tanpa teks lain:\n\n"
        f"{SCHEMA}"
    )
    messages = [
        {"role": "user", "parts": [user_1]},
        {"role": "model", "parts": [model_msg]},
        {"role": "user", "parts": [user_2]},
    ]
    return messages

# ====== DELAY khusus model "pro" ======
_LAST_CALL_TS: dict[str, float] = {}

def _desired_gap_seconds(model_id: str) -> float:
    # jika nama model mengandung "pro", pakai delay panjang (default 30s)
    if "pro" in model_id.lower():
        return float(os.getenv("GEMINI_PRO_DELAY_SEC", "30"))
    # non-pro: fallback ke delay umum (default 1s)
    return float(os.getenv("GEMINI_DELAY_BETWEEN_CALLS", "1.0"))

def _delay_for_model(model_id: str):
    gap = max(0.0, _desired_gap_seconds(model_id))
    last = _LAST_CALL_TS.get(model_id, 0.0)
    now = time.time()
    if last > 0 and now - last < gap:
        time.sleep(gap - (now - last))
    _LAST_CALL_TS[model_id] = time.time()

def _parse_retry_seconds(msg: str) -> float | None:
    # coba ambil "Please retry in 25.66s" atau "retry_delay { seconds: 25 }"
    m = re.search(r"retry in\s+([0-9]+(?:\.[0-9]+)?)s", msg, re.I)
    if m: 
        try: return float(m.group(1))
        except: pass
    m = re.search(r"retry_delay\s*\{\s*seconds:\s*([0-9]+)\s*\}", msg, re.I)
    if m:
        try: return float(m.group(1))
        except: pass
    return None

def _generate_with_retry(model, model_id: str, messages, temperature: float):
    max_retries = int(os.getenv("GENAI_MAX_RETRIES", "6"))
    backoff_base = float(os.getenv("GENAI_BACKOFF_BASE", "1.8"))
    timeout = float(os.getenv("GENAI_TIMEOUT", "90"))
    for attempt in range(max_retries):
        try:
            _delay_for_model(model_id)  # <-- delay per model (pro dapat 30s default)
            return model.generate_content(
                messages,
                generation_config={"temperature": float(temperature)},
                request_options={"timeout": timeout},
            )
        except Exception as e:
            msg = str(e)
            # hormati hint "retry in Xs" jika ada
            hinted = _parse_retry_seconds(msg)
            if hinted is not None:
                time.sleep(hinted + random.uniform(0, 0.5))
                continue
            # rate/quota: exponential backoff
            if "429" in msg or "Resource exhausted" in msg or "rate" in msg.lower() or "quota" in msg.lower():
                sleep_s = min(30.0, (backoff_base ** attempt) + random.uniform(0, 0.5))
                time.sleep(sleep_s)
                continue
            raise
    raise RuntimeError("Gemini verifier rate limited after retries")

# ====== entry point ======
def verify_with_gemini(
    question: str,
    *,
    options: list[str] | None = None,
    answer_key: str | None = None,
    model_solution: str | None = None,
    model_name: str | None = None,
    temperature: float = 0.15,
):
    genai.configure(api_key=os.getenv("GEMINI_API_KEY") or "")
    model_id = model_name or os.getenv("GEMINI_VERIFIER_MODEL", "gemini-2.5-pro")

    try:
        model = genai.GenerativeModel(model_id, system_instruction=SYSTEM_INSTRUCTION)
        use_sys_in_user = False
    except TypeError:
        model = genai.GenerativeModel(model_id)
        use_sys_in_user = True

    messages = _build_messages_with_roles(question, options, answer_key, model_solution)
    if use_sys_in_user:
        messages[0]["parts"][0] = SYSTEM_INSTRUCTION + "\n\n" + messages[0]["parts"][0]

    t0 = time.time()
    resp = _generate_with_retry(model, model_id, messages, temperature)
    latency_ms = int((time.time() - t0) * 1000)
    usage = _usage_to_dict(getattr(resp, "usage_metadata", None))

    text = (getattr(resp, "text", None) or "").strip()
    if not text and getattr(resp, "candidates", None):
        for c in resp.candidates:
            if getattr(c, "content", None) and getattr(c.content, "parts", None):
                for p in c.content.parts:
                    if getattr(p, "text", None):
                        text = p.text.strip(); break
            if text: break

    obj = _extract_json_object(text) or {}
    solution_verifier = (obj.get("solution_verifier") or "").strip()
    scores = obj.get("scores") or {}
    notes = (obj.get("notes") or "").strip()

    def clamp05(x):
        try: v = float(x)
        except Exception: return 0.0
        return max(0.0, min(5.0, v))

    faa_raw = str(scores.get("final_answer_accuracy", "")).strip().lower()
    faa = "Benar" if faa_raw.startswith("b") else ("Salah" if faa_raw.startswith("s") else "")

    norm_scores = {
        "clarity": clamp05(scores.get("clarity", 0)),
        "context_accuracy": clamp05(scores.get("context_accuracy", 0)),
        "quality_of_working": clamp05(scores.get("quality_of_working", 0)),
        "final_answer_accuracy": faa,
    }

    if not solution_verifier:
        solution_verifier = text

    return {
        "model": f"gemini:{model_id}",
        "latencyMs": latency_ms,
        "usage": usage,
        "rawText": text,
        "solution_verifier": solution_verifier,
        "scores": norm_scores,
        "notes": notes,
    }
