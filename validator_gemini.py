# English-only verifier (Gemini 2.5 Pro). No Indonesian mapping.
import os, time, json, re, random
import google.generativeai as genai
from utils.load_env import run_load_env

run_load_env()
print("validator_gemini (per-model delay for pro, EN-only)")

SCHEMA = r"""
REQUIRED OUTPUT: exactly one JSON object (no extra text):
{
  "solution_verifier": "your own concise worked solution in 3–8 lines, plain text; no LaTeX/backslashes/markdown",
  "scores": {
    "clarity": 0.0,
    "context_accuracy": 0.0,
    "quality_of_working": 0.0,
    "final_answer_accuracy": "Correct"  // or "Incorrect"
  },
  "notes": "3–6 brief lines justifying each score (plain text)"
}
Constraints:
- Numeric scores must be within 0.0 to 5.0 (decimals allowed).
- Final Answer Accuracy must be exactly one of: "Correct" or "Incorrect".
"""

SYSTEM_INSTRUCTION = (
    "You are a verifier/evaluator of multiple-choice question (MCQ) quality.\n"
    "Strict procedure:\n"
    "  1) First, solve the question INDEPENDENTLY (ignore the generator's solution until you finish).\n"
    "  2) Then evaluate BOTH the QUESTION and the GENERATOR_SOLUTION on four metrics.\n"
    "  3) Return exactly ONE JSON object that matches the schema; do not add any extra text.\n"
)

def _usage_to_dict(usage) -> dict | None:
    if usage is None:
        return None
    fields = (
        "prompt_token_count","candidates_token_count","total_token_count",
        "input_token_count","output_token_count","cached_input_token_count",
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
        opts_block = "Options:\n" + "\n".join(f"- {o}" for o in options) + "\n"
    key_block = f"Key (A/B/C/D if provided): {answer_key or '-'}\n"
    user_1 = (
        "The following MCQ is to be evaluated. Solve it independently FIRST; "
        "do NOT use the generator's solution until afterwards.\n\n"
        f"Question:\n{question}\n\n{opts_block}{key_block}"
    )
    model_msg = (
        "GENERATOR_SOLUTION (THIS IS NOT your answer; use ONLY after you finish your own solution):\n"
        f"{(model_solution or '').strip()}"
    )
    user_2 = (
        "Your tasks:\n"
        "1) Solve the item INDEPENDENTLY without reading the GENERATOR_SOLUTION above.\n"
        "2) After you have your own answer, evaluate the QUESTION and the GENERATOR_SOLUTION using these metrics:\n"
        "   - Clarity (0–5, decimals allowed): wording/notation/data sufficiency.\n"
        "   - Context Accuracy (0–5): realism and conceptual correctness of context/values.\n"
        "   - Quality of Working (0–5): soundness of reasoning/steps, formulas, arithmetic, units, rounding, consistency.\n"
        '   - Final Answer Accuracy: "Correct" or "Incorrect" — judge the generator\'s final answer against the question.\n'
        "3) Output EXACTLY one JSON object using the following schema (no extra text):\n\n"
        f"{SCHEMA}"
    )
    return [
        {"role": "user", "parts": [user_1]},
        {"role": "model", "parts": [model_msg]},
        {"role": "user", "parts": [user_2]},
    ]

_LAST_CALL_TS: dict[str, float] = {}

def _desired_gap_seconds(model_id: str) -> float:
    if "pro" in model_id.lower():
        return float(os.getenv("GEMINI_PRO_DELAY_SEC", "30"))
    return float(os.getenv("GEMINI_DELAY_BETWEEN_CALLS", "1.0"))

def _delay_for_model(model_id: str):
    gap = max(0.0, _desired_gap_seconds(model_id))
    last = _LAST_CALL_TS.get(model_id, 0.0)
    now = time.time()
    if last > 0 and now - last < gap:
        time.sleep(gap - (now - last))
    _LAST_CALL_TS[model_id] = time.time()

def _parse_retry_seconds(msg: str) -> float | None:
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
            _delay_for_model(model_id)
            return model.generate_content(
                messages,
                generation_config={"temperature": float(temperature)},
                request_options={"timeout": timeout},
            )
        except Exception as e:
            msg = str(e)
            hinted = _parse_retry_seconds(msg)
            if hinted is not None:
                time.sleep(hinted + random.uniform(0, 0.5)); continue
            if "429" in msg or "resource exhausted" in msg.lower() or "rate" in msg.lower() or "quota" in msg.lower():
                sleep_s = min(30.0, (backoff_base ** attempt) + random.uniform(0, 0.5))
                time.sleep(sleep_s); continue
            raise
    raise RuntimeError("Gemini verifier rate limited after retries")

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
    faa = "Correct" if faa_raw.startswith(("c","t")) else ("Incorrect" if faa_raw.startswith(("i","f")) else "")

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
