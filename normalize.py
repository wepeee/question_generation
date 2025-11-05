# QUESTION_GENERATION/normalize.py
import re
from typing import List

STOPWORDS = {
  'yang','dan','atau','pada','dari','untuk','dengan','adalah','nilai','berapa',
  'tentukan','sebuah','suatu','jika','ke','di','dalam','itu','ini','the','of','a','an','to','is','are'
}

def normalize_math_text(s: str) -> str:
    if not s: return s
    t = s
    t = t.replace('$','')
    t = t.replace('\\\\','\\')
    repl = [
        (r'\\times','×'), (r'\\cdot','·'), (r'\\pi','π'),
        (r'\\deg|\\degree|\\circ','°'),
        (r'\\sin','sin'), (r'\\cos','cos'), (r'\\tan','tan'),
        (r'\\sqrt','sqrt'), (r'\\ln','ln'), (r'\\log','log'),
        (r'\\cup','∪'), (r'\\cap','∩'), (r'\\leq','≤'), (r'\\geq','≥'),
        (r'\\ne','≠'), (r'\\pm','±'), (r'\\left|\\right',''),
    ]
    for p, r in repl: t = re.sub(p, r, t)
    t = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1)/(\2)', t)
    t = re.sub(r'\^\{(\d+)\}', r'^\1', t)
    t = re.sub(r'[{}]', '', t)
    t = t.replace('\\','')
    t = re.sub(r'\s+',' ', t).strip()
    return t

def normalize_quiz(q: dict) -> dict:
    return {
        "question": normalize_math_text(q.get("question","")),
        "options": [normalize_math_text(o) for o in q.get("options", [])],
        "answer": str(q.get("answer","")).strip().upper(),
        "solution": normalize_math_text(q.get("solution","")),
    }

def extract_avoid_terms(text: str, limit: int = 10) -> List[str]:
    t = normalize_math_text(text or '').lower()
    nums = list(dict.fromkeys(re.findall(r'\b\d+(?:[.,]\d+)?\b', t)))[:6]
    words = [
        w for w in re.sub(r'[^a-z0-9\s\-]', ' ', t).split()
        if len(w) >= 3 and w not in STOPWORDS
    ][: max(0, limit - len(nums))]
    return list(dict.fromkeys([*words, *nums]))
