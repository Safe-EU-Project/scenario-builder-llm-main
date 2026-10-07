"""Choose the next training incident from an authored scenario (allowlist + optional LLM)."""

from __future__ import annotations

from typing import List, Optional, Set, Tuple

from ..config.models import AdaptLLMResult, Incident, Scenario, TraineeIncidentView  # noqa: F401 (AdaptLLMResult used in api.py)


def incident_to_trainee_view(incident: Incident) -> TraineeIncidentView:
    return TraineeIncidentView(
        title=incident.title,
        message_timestamp=incident.message_timestamp,
        description=incident.description,
        inject=incident.inject,
    )


def _visited_set(visited: List[int]) -> Set[int]:
    return set(visited)


def eligible_indices(n_incidents: int, visited: List[int]) -> List[int]:
    v = _visited_set(visited)
    return [i for i in range(n_incidents) if i not in v]


def default_next_index(n_incidents: int, visited: List[int], current: int) -> Optional[int]:
    """
    Prefer the next unseen index after `current`, then wrap forward from 0.
    Matches a typical linear script when the LLM agrees with the default.
    """
    v = _visited_set(visited)
    for j in range(current + 1, n_incidents):
        if j not in v:
            return j
    for j in range(0, n_incidents):
        if j not in v:
            return j
    return None


def validate_next_step_request(
    scenario: Scenario, current: int, visited: List[int]
) -> Tuple[bool, Optional[str]]:
    n = len(scenario.incidents)
    if n == 0:
        return False, "scenario has no incidents"
    if current < 0 or current >= n:
        return False, f"current_incident_index out of range (0..{n - 1})"
    vset = _visited_set(visited)
    for i in visited:
        if i < 0 or i >= n:
            return False, f"visited_incident_indices contains invalid index: {i}"
    if current not in vset:
        return False, "visited_incident_indices must include current_incident_index"
    if len(vset) != len(visited):
        return False, "visited_incident_indices must not contain duplicates"
    return True, None


def summarize_incidents_for_prompt(scenario: Scenario, indices: List[int], max_chars: int = 1200) -> str:
    """Compact per-incident lines for LLM context (allowlist narrative)."""
    lines: List[str] = []
    for i in indices:
        inc = scenario.incidents[i]
        title = inc.title.replace("\n", " ")[:200]
        desc = inc.description.replace("\n", " ")[:400]
        lines.append(f"[{i}] {title}\n    {desc}")
    text = "\n\n".join(lines)
    if len(text) > max_chars:
        return text[:max_chars] + "\n…(truncated)"
    return text


NEXT_STEP_SYSTEM_PROMPT = """You are a crisis-training simulation director choosing the next incident in a live tabletop exercise.

═══ HARD RULES ═══

1. chosen_incident_index MUST be one of the integers in the allowed list — never outside it.

2. rationale is REQUIRED and MUST NOT be empty. Write 1-2 sentences that:
   a. Reference the trainee's specific action (quote or paraphrase it).
   b. Explain the causal link: why does THAT action lead to THIS next incident?
   Example: "Because the trainee wiped the server before imaging it, forensic evidence is gone and the regulator now demands proof of containment."

3. If only one index is allowed, still write a rationale explaining why that incident follows causally.

4. Base your choice on:
   - The trainee's stated action (most important)
   - The simulation history (what has already happened)
   - Causal / consequence logic: late-game actions often trigger closure, review, or escalation beats.

5. Do NOT invent new incidents. Do NOT reference indices outside the allowed list.

6. predicted_threat_vector: predict in 1 sentence what attack technique the adversary will likely use next,
   based on what the trainee did or failed to do. Be specific (e.g. "lateral movement via stolen credentials").
   Set to null only if this is the last step.

7. predicted_impact: predict in 1 sentence the operational impact if the trainee fails to contain this step.
   Be concrete (e.g. "ransomware spreads to backup servers within 30 minutes"). Set to null only if last step."""


NEXT_STEP_EXPLOIT_PATH_PROMPT = """
═══ EXPLOIT PATH — REQUIRED UNLESS SCENARIO IS COMPLETE ═══

8. exploit_path: Populate this structured object to explain HOW the attacker moves from the current
   incident to the chosen next incident. This is the vulnerability exploitation chain — the specific
   path the adversary takes between steps. All sub-fields are required:

   current_foothold
     — The access or position the attacker holds RIGHT NOW (end of current incident).
     — Example: "Compromised credentials for local admin on WORKSTATION-14"
     — Example: "Read/write access to SWIFT message broker via hijacked operator session"

   vulnerability_exploited
     — The specific CVE, protocol weakness, or human/process failure the attacker exploits
       to advance. Be precise — name the CVE if known, or the exact misconfiguration.
     — Example: "CVE-2021-34527 (PrintNightmare) — unpatched Windows Print Spooler"
     — Example: "Absence of MFA on Domain Admin account; password reuse from phished credentials"

   lateral_movement_technique
     — MITRE ATT&CK technique ID + name for this specific pivot step.
     — Example: "T1550.002 — Pass the Hash"
     — Example: "T1021.001 — Remote Desktop Protocol"
     — For ICS scenarios use MITRE ATT&CK ICS: "T0886 — Remote Services"

   pivot_target
     — The specific system, account, service, or asset being targeted in this step.
     — Example: "Domain Controller DC-CORP-01 (Windows Server 2019)"
     — Example: "SWIFT Alliance Access Terminal (SAA 7.3.x)"

   new_capability_gained
     — What the attacker achieves by successfully exploiting this path.
     — Example: "Domain Administrator privileges across all production OUs"
     — Example: "Ability to inject and approve fraudulent MT103 SWIFT payment messages"

   containment_window
     — Realistic estimate of time available to defenders to interrupt this path.
       Base it on the attack technique (fast techniques = short windows).
     — Example: "~8-12 minutes from first beacon — Pass-the-Hash is near-instant once credentials are in memory"
     — Example: "< 4 minutes — SWIFT session tokens expire after 5 minutes; attacker must act fast"

   detection_indicators
     — List of 2-4 concrete, observable IOCs or behavioral signals that defenders could
       use to detect THIS exploitation path. Be specific — not generic "check logs".
     — Example: ["Event ID 4624 (Logon) with LogonType 3 from WORKSTATION-14 to DC-CORP-01",
                 "Kerberos TGS request for CIFS service from non-standard source IP",
                 "SIEM correlation: successful logon 30s after failed MFA attempt"]

   Set exploit_path to null ONLY if is_scenario_complete would be true (no next step exists)."""


def next_step_system_prompt(include_exploit_path: bool) -> str:
    """Full prompt only when the caller asked for exploit_path. Otherwise the model fills a short schema."""
    if not include_exploit_path:
        return NEXT_STEP_SYSTEM_PROMPT
    return f"{NEXT_STEP_SYSTEM_PROMPT}\n{NEXT_STEP_EXPLOIT_PATH_PROMPT}"


def build_visited_summary(scenario: "Scenario", visited: List[int], current: int) -> str:
    """One-line per already-shown incident for history context in the prompt."""
    lines = []
    for i in visited:
        if i == current:
            continue
        inc = scenario.incidents[i]
        lines.append(f"  [shown] #{i} {inc.title} ({inc.message_timestamp})")
    return "\n".join(lines) if lines else "  (none — this is the first step)"


def build_next_step_user_message(
    scenario_title: str,
    current_index: int,
    current_summary: str,
    user_action: str,
    eligible: List[int],
    eligible_summaries: str,
    visited_summary: str = "",
) -> str:
    history_block = f"\nSimulation history (already shown to trainee):\n{visited_summary}\n" if visited_summary else ""
    return f"""Scenario title: {scenario_title}
{history_block}
Current incident (index {current_index}) — the trainee just responded to this:
{current_summary}

Trainee action (verbatim):
{user_action}

Allowed next indices — you MUST pick exactly one of: {eligible}

Summaries of allowed next incidents:
{eligible_summaries}

Return JSON with chosen_incident_index (must be in {eligible}) and a non-empty rationale that references the trainee's action."""


def current_incident_summary(incident: Incident, max_len: int = 800) -> str:
    parts = [f"Title: {incident.title}", f"When: {incident.message_timestamp}", incident.description]
    if incident.inject:
        parts.append(f"Inject: {incident.inject}")
    text = "\n".join(parts)
    if len(text) > max_len:
        return text[:max_len] + "…"
    return text


# ---------------------------------------------------------------------------
# Inject adaptation helpers
# ---------------------------------------------------------------------------

ADAPT_INJECT_SYSTEM_PROMPT = """You are a crisis-training simulation director adapting a pre-authored incident card.

Rules (MUST follow):
1. The trainee has already taken the action described below — do NOT present it as something still to be done.
2. Keep the incident's CORE learning objective intact (do not change what the incident is fundamentally about).
3. Rewrite `adapted_description` (2-4 sentences) to:
   a. Briefly acknowledge what the trainee did.
   b. Surface what is STILL unresolved or what new information has emerged as a consequence.
4. Rewrite `adapted_inject` (the artefact: email, log, alert, ticket) so it reflects the trainee's prior action.
   If the original inject is None, you may return null for adapted_inject.
5. Do NOT reveal expected actions. Do NOT add new incidents outside the authored scenario.
6. Keep the same timestamp and title — only description and inject change."""


def build_adapt_user_message(
    scenario_title: str,
    user_action: str,
    chosen_incident: Incident,
    history_summary: str = "",
) -> str:
    orig_inject = chosen_incident.inject or "(no inject)"
    history_block = f"\nPrevious steps summary:\n{history_summary}\n" if history_summary else ""
    return f"""Scenario title: {scenario_title}
{history_block}
Trainee's most recent action (verbatim):
{user_action}

Pre-authored incident card to adapt:
Title: {chosen_incident.title}
Timestamp: {chosen_incident.message_timestamp}
Description: {chosen_incident.description}
Inject: {orig_inject}

Rewrite description and inject so they acknowledge what the trainee already did and focus on what still needs to be addressed."""


def apply_adapt_result(
    original: Incident,
    adapt: AdaptLLMResult,
) -> TraineeIncidentView:
    """Merge adapt LLM output into a TraineeIncidentView (no expected_actions)."""
    return TraineeIncidentView(
        title=original.title,
        message_timestamp=original.message_timestamp,
        description=adapt.adapted_description,
        inject=adapt.adapted_inject if adapt.adapted_inject is not None else original.inject,
    )
