# QUESTION_GENERATION/prompting.py
# English prompting & English outputs (keeps your existing keys: struktur1..3, matematika/biologi/fisika/kimia)

from __future__ import annotations
from typing import List, Literal, TypedDict, Optional

# Reuse the same keys you already pass around
PromptStructKey = Literal["struktur1", "struktur2", "struktur3"]
TopicKey = Literal["matematika", "biologi", "fisika", "kimia"]

# Your LLM service expects {"role": "...", "content": "..."}
class ChatMessage(TypedDict):
    role: Literal["system", "user"]
    content: str

def topic_label(t: TopicKey) -> str:
    return {
        "matematika": "Mathematics",
        "biologi": "Biology",
        "fisika": "Physics",
        "kimia": "Chemistry",
    }[t]

def build_messages_single(
    struct_key: PromptStructKey,
    topic: TopicKey,
    avoid_terms: Optional[List[str]] = None,
) -> List[ChatMessage]:
    """Builds English prompts with strict single-item JSON contract (English output)."""

    t = topic_label(topic)

    # ===== SP / CoT / QC blocks in English =====
    blocks = {
        "matematika": {
            "sp": (
                "SP (Standard Prompting):\n"
                "• Write 1 medium-difficulty computational MCQ from ONE of: algebra (functions/inverse/systems), "
                "trigonometry (identities/evaluation), basic calculus (limits/derivatives/simple integrals), or short statistics.\n"
                "• Use realistic numbers; round to 2 decimals when needed; avoid formal proofs.\n"
                "• Distractors must reflect typical mistakes (sign errors, wrong identities, derivative/limit rules, rounding)."
            ),
            "cot": (
                "CoT (few-shot style; hidden reasoning 2–3 steps):\n"
                "• Perform multi-step reasoning INTERNALLY; do NOT reveal the steps.\n\n"
                "Style example (analogous): system of linear equations → plan elimination/substitution → compute → choose option.\n"
                "• Create a NEW problem of the same family (SLE, trig identity then evaluate angle, derivative then plug-in value, small-data statistics).\n"
                "• Distractors should map to step errors (bad elimination, wrong identity, wrong derivative rule, wrong rounding)."
            ),
            "qc": (
                "Quality Constraints (paper-aligned):\n"
                "• Clarity & notation: consistent symbols; specific stem; sufficient data.\n"
                "• Difficulty target: medium (≤ 3 steps).\n"
                "• Distractor effectiveness: three plausible distractors representing DIFFERENT misconceptions/step errors.\n"
                "• Numerical hygiene: realistic result; 2-decimal rounding; consistent units/notation if any."
            ),
        },
        "biologi": {
            "sp": (
                "SP (Standard Prompting):\n"
                "• Write 1 concise concept/application MCQ from: basic genetics (incl. Hardy–Weinberg), "
                "cell/tissue structure–function, or short ecology.\n"
                "• Use standard terminology; if arithmetic appears (e.g., allele frequency), keep numbers small and round to 2 decimals.\n"
                "• Distractors reflect common misconceptions (dominance ≠ frequency, misreading ratios/diagrams, confusion about DNA→RNA→Protein)."
            ),
            "cot": (
                "CoT (few-shot analogue; hidden 1–2 steps):\n"
                "• Identify concept/ratio/mini-table relations INTERNALLY; do NOT show steps.\n\n"
                "Style example (Hardy–Weinberg): compute 2pq internally → choose option.\n"
                "• Create a NEW item of the same family (small table/genotype ratio/energy flow).\n"
                "• Distractors must be plausible and map to real misconceptions."
            ),
            "qc": (
                "Quality Constraints (paper-aligned):\n"
                "• Clarity: standard terms; no ambiguous processes/structures; enough data for a single best answer.\n"
                "• Difficulty target: medium (1–2 simple inferences/ratios).\n"
                "• Distractor effectiveness: three plausible misconceptions.\n"
                "• Consistency check: verify genotype–phenotype/energy–matter relations before finalizing the key."
            ),
        },
        "fisika": {
            "sp": (
                "SP (Standard Prompting):\n"
                "• Write 1 medium-level quantitative MCQ from: kinematics (uniform/accelerated/projectile), dynamics (Newton/incline), "
                "energy–impulse, or basic circuits (V–I–R).\n"
                "• Use SI units (use g = 9.8 m s^-2 if relevant); realistic numbers; round to 2 decimals.\n"
                "• Distractors: typical vector-component/sign mistakes, unit conversion errors, wrong effective forces."
            ),
            "cot": (
                "CoT (few-shot; hidden 2–3 steps):\n"
                "• Decompose quantities/equations INTERNALLY; do NOT show steps.\n\n"
                "Style example (projectile): compute components; apply kinematic relation; recombine speed → choose option.\n"
                "• Create a NEW item (projectile/incline/energy–impulse/circuit).\n"
                "• Distractors = sin/cos swap, sign errors, wrong units."
            ),
            "qc": (
                "Quality Constraints (paper-aligned):\n"
                "• Clarity & SI: explicit quantities and SI units; consistent symbols.\n"
                "• Difficulty target: medium (2–3 steps).\n"
                "• Physical plausibility: order-of-magnitude check; conserve energy/impulse when relevant.\n"
                "• Distractor effectiveness: three plausible typical mistakes (sin–cos component, work/energy sign, wrong unit)."
            ),
        },
        "kimia": {
            "sp": (
                "SP (Standard Prompting):\n"
                "• Write 1 medium-level quantitative MCQ from: stoichiometry (incl. limiting reagent), concentration (molarity/mass percent), "
                "strong acid–base (pH), or simple equilibria.\n"
                "• Use common atomic masses (H=1, C=12, N=14, O=16, Na=23, Cl=35.5); round to 2 decimals; correct units.\n"
                "• Distractors: wrong coefficients, wrong mol–gram–volume conversions, log/pH errors."
            ),
            "cot": (
                "CoT (few-shot; hidden multi-step):\n"
                "• Perform calculations and coefficient checks INTERNALLY; do NOT show steps.\n\n"
                "Style example (electrolysis): compute Q, moles of e−, stoichiometric relation, mass.\n"
                "• Create a NEW item (stoichiometry/pH/light equilibrium).\n"
                "• Distractors mirror common missteps (coefficients, conversions, log/pH)."
            ),
            "qc": (
                "Quality Constraints (paper-aligned):\n"
                "• Clarity & units: reaction/coefficients/units clear; sufficient data.\n"
                "• Difficulty target: medium; realistic numbers; 2-decimal rounding.\n"
                "• Distractor effectiveness: three plausible common errors (coefficients, conversion, log/pH).\n"
                "• Numerical hygiene: significant figures & units consistent; realistic results."
            ),
        },
    }

    # ===== Strict single-item output contract (English, plain text) =====
    output_contract = (
        "STRICT OUTPUT CONTRACT (SINGLE ITEM):\n"
        "- Return ONLY a JSON array containing EXACTLY 1 object:\n"
        '  [{"question":"...","options":["A. ...","B. ...","C. ...","D. ..."],'
        '"answer":"A","solution":"3–6 short lines, plain text; no LaTeX/markdown."}]\n'
        '- The "solution" field is MANDATORY with 3–6 short lines (plain text; no LaTeX/markdown).\n'
        "- No extra text outside JSON; no code fences.\n"
        '- Options MUST be prefixed "A. "/"B. "/"C. "/"D. " and "answer" ∈ {A,B,C,D}.\n'
        "- NO LaTeX: do not use $ or backslashes; write plain text (sin, cos, pi, (a)/(b))."
    )

    # ===== Assemble system content (English teacher role + selected blocks) =====
    parts: List[str] = []
    parts.append(blocks[topic]["sp"])
    if struct_key in ("struktur2", "struktur3"):
        parts.append(blocks[topic]["cot"])
    if struct_key == "struktur3":
        parts.append(blocks[topic]["qc"])

    system_content = (
        f"You are a Grade 12 {t} teacher.\n"
        "Write EXACTLY 1 high-quality multiple-choice question (MCQ) and INCLUDE a brief solution (3–6 lines, plain text).\n"
        + "\n\n".join(parts)
        + "\n\n"
        + output_contract
    ).strip()

    # Optional: avoid-terms block
    avoid_block = ""
    if avoid_terms:
        avoid_terms = [str(x) for x in avoid_terms if str(x).strip()]
        if avoid_terms:
            avoid_block = (
                "\n\nAdditional constraint:\n"
                f"- Avoid reusing the following words/numbers: {', '.join(avoid_terms)}.\n"
                "- Do NOT print this list in the output."
            )

    user_content = (
        f"Topic: {t}. Create 1 MCQ following the instructions and return a single-item JSON with the \"solution\" field."
        + avoid_block
    )

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]
