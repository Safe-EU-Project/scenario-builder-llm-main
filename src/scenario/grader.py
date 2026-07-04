"""Grade a single trainee action against a list of expected actions using an LLM."""

from __future__ import annotations

from typing import List

from ..config.models import GradeLLMResult


GRADE_SYSTEM_PROMPT = """You are an expert crisis-training evaluator assessing a trainee's incident response action.

RULES:
1. Compare the trainee's action against each expected action SEMANTICALLY — different wording, order, or phrasing that conveys the same intent counts as a match.
2. score: a float 0.0–1.0 based on how many expected actions were covered (0.0 = none, 1.0 = all).
3. level must be exactly one of:
   - "missing"   → score < 0.2  (almost nothing correct)
   - "partial"   → 0.2 ≤ score < 0.6  (some correct, significant gaps)
   - "good"      → 0.6 ≤ score < 0.9  (mostly correct, minor gaps)
   - "excellent" → score ≥ 0.9  (all or nearly all correct)
4. feedback: 1–3 sentences. Acknowledge what was done well, then explain what was missed. Be constructive and specific.
5. matched_actions: list only the expected actions the trainee DID cover (use the original wording from the expected list).
6. missed_actions: list only the expected actions the trainee did NOT cover (use the original wording).
7. Do NOT penalise for extra actions the trainee took beyond the expected list."""


def build_grade_user_message(
    scenario_title: str,
    incident_title: str,
    expected_actions: List[str],
    user_action: str,
) -> str:
    expected_block = "\n".join(f"  - {a}" for a in expected_actions)
    return f"""Scenario: {scenario_title}
Incident: {incident_title}

Expected actions (ground truth — do NOT reveal to trainee):
{expected_block}

Trainee's submitted action:
{user_action}

Evaluate and return JSON with: score, level, feedback, matched_actions, missed_actions."""


def cosine_fallback(
    expected_actions: List[str],
    user_action: str,
) -> GradeLLMResult:
    """Lightweight cosine-similarity fallback when LLM is unavailable."""
    try:
        from sentence_transformers import SentenceTransformer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np

        model = SentenceTransformer("all-MiniLM-L6-v2")
        user_emb = model.encode([user_action])
        matched: List[str] = []
        missed: List[str] = []
        for action in expected_actions:
            exp_emb = model.encode([action])
            sim = float(cosine_similarity(user_emb, exp_emb)[0][0])
            if sim >= 0.55:
                matched.append(action)
            else:
                missed.append(action)

        score = len(matched) / len(expected_actions) if expected_actions else 0.0
        if score < 0.2:
            level = "missing"
        elif score < 0.6:
            level = "partial"
        elif score < 0.9:
            level = "good"
        else:
            level = "excellent"

        feedback = (
            f"You covered {len(matched)} of {len(expected_actions)} expected actions."
            + (f" Missed: {', '.join(missed[:3])}." if missed else " Well done!")
        )
        return GradeLLMResult(
            score=round(score, 2),
            level=level,
            feedback=feedback,
            matched_actions=matched,
            missed_actions=missed,
        )
    except Exception:
        return GradeLLMResult(
            score=0.0,
            level="missing",
            feedback="Grading unavailable — please try again.",
            matched_actions=[],
            missed_actions=list(expected_actions),
        )
