# English-only prompting & outputs.
from __future__ import annotations
from typing import List, TypedDict, Literal, Optional

PromptStructKey = Literal["struktur1", "struktur2", "struktur3"]
TopicKey = Literal["mathematics", "biology", "physics", "chemistry"]

class ChatMessage(TypedDict):
    role: Literal["system", "user"]
    content: str

def _require_topic(t: str) -> TopicKey:
    key = (t or "").strip().lower()
    allowed: tuple[str, ...] = ("mathematics", "biology", "physics", "chemistry")
    if key not in allowed:
        raise ValueError(f"Unknown topic '{t}'. Use one of: {', '.join(allowed)}.")
    return key  # type: ignore[return-value]

def _topic_label(t: TopicKey) -> str:
    return {
        "mathematics": "Mathematics",
        "biology": "Biology",
        "physics": "Physics",
        "chemistry": "Chemistry",
    }[t]

def build_messages_single(
    struct_key: PromptStructKey,
    topic: str,
    avoid_terms: Optional[List[str]] = None,
) -> List[ChatMessage]:
    """English prompts + strict single-item JSON (English output)."""
    tkey = _require_topic(topic)
    tlabel = _topic_label(tkey)

    blocks = {
        "mathematics": {
            "sp": (
                "SP (Standard Prompting):\n"
                "• Write 1 medium-difficulty computational MCQ from ONE of: algebra (functions/inverse/systems), "
                "trigonometry (identities/evaluation), basic calculus (limits/derivatives/simple integrals), or short statistics.\n"
                "• Use realistic numbers; round to 2 decimals when needed; avoid formal proofs.\n"
                "• Distractors must reflect typical mistakes (sign errors, wrong identities, derivative/limit rules, rounding)."
            ),
            "cot": (
                "CoT (few-shot style; hidden 2–3 steps):\n"
                "• Perform multi-step reasoning INTERNALLY; do NOT reveal the steps.\n\n"
                "Style example: plan elimination/substitution for a linear system → compute → choose option.\n"
                "• Create a NEW problem of the same family (SLE, trig identity+evaluation, derivative+substitution, small-data stats).\n"
                "• Distractors map to step errors (bad elimination, wrong identity, wrong derivative rule, wrong rounding)."
            ),
            "qc": (
                "Quality Constraints:\n"
                "• Clarity & notation: consistent symbols; specific stem; sufficient data.\n"
                "• Difficulty target: medium (≤ 3 steps).\n"
                "• Distractor effectiveness: three plausible distractors representing different misconceptions/step errors.\n"
                "• Numerical hygiene: realistic result; 2-decimal rounding; consistent units/notation if any."
            ),
        },
        "biology": {
            "sp": (
                "SP (Standard Prompting):\n"
                "• Write 1 concise concept/application MCQ from: basic genetics (incl. Hardy–Weinberg), "
                "cell/tissue structure–function, or short ecology.\n"
                "• Use standard terminology; if arithmetic appears (e.g., allele frequency), keep numbers small and round to 2 decimals.\n"
                "• Distractors reflect common misconceptions (dominance ≠ frequency, misreading ratios/diagrams, DNA→RNA→Protein confusion)."
            ),
            "cot": (
                "CoT (few-shot analogue; hidden 1–2 steps):\n"
                "• Identify concept/ratio/mini-table relations INTERNALLY; do NOT show steps.\n\n"
                "Style example (Hardy–Weinberg): compute 2pq internally → choose option.\n"
                "• Create a NEW item of the same family (small table/genotype ratio/energy flow).\n"
                "• Distractors must be plausible and map to real misconceptions."
            ),
            "qc": (
                "Quality Constraints:\n"
                "• Clarity: standard terms; no ambiguous processes/structures; enough data for a single best answer.\n"
                "• Difficulty target: medium (1–2 simple inferences/ratios).\n"
                "• Distractor effectiveness: three plausible misconceptions.\n"
                "• Consistency check: verify genotype–phenotype or energy–matter relations before finalizing the key."
            ),
        },
        "physics": {
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
                "Style example (projectile): compute components; apply kinematic relations; recombine speed → choose option.\n"
                "• Create a NEW item (projectile/incline/energy–impulse/circuit).\n"
                "• Distractors = sin/cos swap, sign errors, wrong units."
            ),
            "qc": (
                "Quality Constraints:\n"
                "• Clarity & SI: explicit quantities and SI units; consistent symbols.\n"
                "• Difficulty target: medium (2–3 steps).\n"
                "• Physical plausibility: order-of-magnitude check; conserve energy/impulse when relevant.\n"
                "• Distractor effectiveness: three plausible typical mistakes (sin–cos component, work/energy sign, wrong unit)."
            ),
        },
        "chemistry": {
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
                "Quality Constraints:\n"
                "• Clarity & units: reaction/coefficients/units clear; sufficient data.\n"
                "• Difficulty target: medium; realistic numbers; 2-decimal rounding.\n"
                "• Distractor effectiveness: three plausible common errors (coefficients, conversion, log/pH).\n"
                "• Numerical hygiene: significant figures & units consistent; realistic results."
            ),
        },
    }

    output_contract = (
        "STRICT OUTPUT CONTRACT (SINGLE ITEM):\n"
        "- Return ONLY a JSON array containing EXACTLY 1 object.\n"
        '- Format:\n'
        '  [{"question": "...", "options": ["...","...","...","..."], "answer": "A", "solution": "..."}]\n'
        "- Fields:\n"
        '  * \"question\": one string.\n'
        '  * \"options\": array of 4 answer-choice strings.\n'
        '  * \"answer\": one of \"A\",\"B\",\"C\",\"D\" (just the letter).\n'
        '  * \"solution\": short plain-text explanation (a few lines is fine).\n'
        "- No extra text before or after the JSON.\n"
        "- Do NOT use markdown, code fences, or LaTeX ($ or backslashes)."
    )


    parts: List[str] = [blocks[tkey]["sp"]]
    if struct_key == "struktur2":
        parts.append(blocks[tkey]["cot"])

    if struct_key == "struktur3":
        parts.append(blocks[tkey]["qc"])

    system_content = (
        f"You are a Grade 12 {tlabel} teacher.\n"
        "Write EXACTLY 1 high-quality multiple-choice question (MCQ) and INCLUDE a brief solution (3–6 lines, plain text).\n"
        + "\n\n".join(parts)
        + "\n\n"
        + output_contract
    ).strip()

    avoid_block = ""
    if avoid_terms:
        avoid_terms = [str(x).strip() for x in avoid_terms if str(x).strip()]
        if avoid_terms:
            avoid_block = (
                "\n\nAdditional constraint:\n"
                f"- Avoid reusing the following words/numbers: {', '.join(avoid_terms)}.\n"
                "- Do NOT print this list in the output."
            )

    user_content = (
        f"Topic: {tlabel}. Create 1 MCQ following the instructions and return a single-item JSON with the \"solution\" field."
        + avoid_block
    )

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]
