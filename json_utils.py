# QUESTION_GENERATION/json_utils.py
import json, re
from typing import Any, List

def _balanced_chunk(s: str, open_ch: str, close_ch: str) -> str | None:
    start = s.find(open_ch)
    if start == -1: return None
    depth = 0
    for i, ch in enumerate(s[start:], start=start):
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return s[start:i+1]
    return None

def _sanitize(s: str) -> str:
    s = re.sub(r",\s*([}\]])", r"\1", s)
    s = re.sub(r'\\(?!["\\\/bfnrtu])', r"\\\\", s)
    return s

def _to_strict_json(s: str) -> str:
    t = s
    t = re.sub(r'([{,]\s*)([A-Za-z_]\w*)\s*:', r'\1"\2":', t)
    t = re.sub(r"'([^'\\]*(?:\\.[^'\\]*)*)'", lambda m: '"' + m.group(1).replace('"','\\"') + '"', t)
    return t

def extract_json_array(text: str) -> List[Any]:
    if not text: return []
    clean = str(text).strip()
    clean = re.sub(r'```json|```', '', clean, flags=re.I).strip()
    clean = clean.replace('“','"').replace('”','"').replace('’',"'").replace('‘',"'")

    chunk = _balanced_chunk(clean, '[', ']')
    if chunk is None:
        chunk = _balanced_chunk(clean, '{', '}')
    if chunk is None:
        chunk = clean

    jsonish = _sanitize(chunk)
    try:
        parsed = json.loads(jsonish)
        return parsed if isinstance(parsed, list) else [parsed]
    except Exception:
        jsonish = _sanitize(_to_strict_json(jsonish))
        parsed = json.loads(jsonish)
        return parsed if isinstance(parsed, list) else [parsed]
