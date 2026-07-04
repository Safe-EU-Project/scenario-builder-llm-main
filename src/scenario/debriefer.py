"""Generate an end-of-simulation debrief report using an LLM."""

from __future__ import annotations

from typing import List

from ..config.models import DebriefHistoryEntry, DebriefLLMResult, Scenario


DEBRIEF_SYSTEM_PROMPT = """You are an expert crisis-training evaluator writing a post-simulation debrief report.

⚠ HARD CONSTRAINT — READ FIRST:
Do NOT reference any external documents, manuals, SOPs, checklists, frameworks, standards, guides, or named resources in your output.
This means: never say things like "review the SOP", "consult NIST SP 800-61", "follow the 11-step guide", "refer to the incident response checklist", "according to ISO 27035", etc.
Every recommendation must be a concrete, self-contained action the trainee can perform on their own — based solely on what was observed in this simulation session.

SCORING RULES:
1. overall_score: float 0.0-1.0. Use the per-step scores if provided; otherwise infer from the action quality.
2. overall_level must be exactly one of:
   - "missing"   → overall_score < 0.2
   - "partial"   → 0.2 ≤ overall_score < 0.6
   - "good"      → 0.6 ≤ overall_score < 0.9
   - "excellent" → overall_score ≥ 0.9

CONTENT RULES:
3. summary: 2-4 sentences. Holistic narrative of the trainee's performance across the full simulation. Reference specific moments.
4. strengths: 2-4 bullet points of what the trainee did consistently well. Be specific and cite incident titles or actions.
5. gaps: 2-4 bullet points of recurring weaknesses or critical misses. Be specific.
6. recommendations: 2-4 concrete, actionable improvement steps. Each must be a specific skill or behaviour to practise — NOT a reference to any external document, framework, or guide.
7. Tone: professional, constructive, encouraging — like a senior instructor giving feedback.

⚠ REMINDER: Do NOT mention SOPs, manuals, frameworks, standards, or any named external resource anywhere in your response."""


def build_debrief_user_message(
    scenario: Scenario,
    history: List[DebriefHistoryEntry],
) -> str:
    lines = []
    for entry in history:
        score_str = f"{int(entry.grade_score * 100)}/100 ({entry.grade_level})" if entry.grade_score is not None else "not graded"
        lines.append(
            f"  Step {entry.incident_index} — {entry.incident_title}\n"
            f"    Action : {entry.user_action}\n"
            f"    Grade  : {score_str}"
        )
    history_block = "\n\n".join(lines)

    graded = [e for e in history if e.grade_score is not None]
    avg_str = ""
    if graded:
        avg = sum(e.grade_score for e in graded) / len(graded)
        avg_str = f"\nAverage score across {len(graded)} graded steps: {int(avg * 100)}/100\n"

    return f"""Scenario: {scenario.scenario_title}
Total incidents in scenario: {len(scenario.incidents)}
Steps completed by trainee: {len(history)}
{avg_str}
Simulation history (ordered):
{history_block}

Write a comprehensive debrief report with: overall_score, overall_level, summary, strengths, gaps, recommendations."""


def score_fallback(history: List[DebriefHistoryEntry]) -> DebriefLLMResult:
    """Simple average-based fallback when LLM is unavailable."""
    graded = [e for e in history if e.grade_score is not None]
    if graded:
        avg = sum(e.grade_score for e in graded) / len(graded)
    else:
        avg = 0.0

    if avg < 0.2:
        level = "missing"
    elif avg < 0.6:
        level = "partial"
    elif avg < 0.9:
        level = "good"
    else:
        level = "excellent"

    return DebriefLLMResult(
        overall_score=round(avg, 2),
        overall_level=level,
        summary=f"Average score: {int(avg * 100)}/100 across {len(graded)} graded steps.",
        strengths=["Completed the simulation"],
        gaps=["Detailed analysis unavailable — LLM service offline"],
        recommendations=["Re-run the simulation when the LLM service is available for full feedback"],
    )
