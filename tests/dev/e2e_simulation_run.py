"""
End-to-end simulation runner for the dynamic next_step + grade_step endpoints.

Usage (from repo root):
    python tests/dev/e2e_simulation_run.py [--scenario PATH] [--actions PATH] [--url URL] [--no-adapt] [--no-llm] [--no-grade]

Defaults:
    --url      http://127.0.0.1:6002
    --scenario  (required: path to scenario JSON produced by query_structured)
    --actions   (optional: path to a JSON file with a list of user_action strings)
                If omitted, built-in demo actions are used.

The scenario JSON can be either:
  - the full /api/v1/query_structured response  (uses .scenario key)
  - just the scenario object                    (uses it directly)

Output is written to stdout; redirect to a file to save.

Example:
    curl -s -X POST http://127.0.0.1:6002/api/v1/query_structured \\
        -H 'Content-Type: application/json' \\
        -d '{"query":"Create a short data breach scenario with 5 incidents"}' \\
        > /tmp/sb_structured.json

    python tests/dev/e2e_simulation_run.py \\
        --scenario /tmp/sb_structured.json \\
        --url http://127.0.0.1:6002
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Demo actions used when no --actions file is provided.
# These are intentionally varied (good, off-script, over-ambitious) to show
# different LLM branching behaviours.
# ---------------------------------------------------------------------------
DEMO_ACTIONS: List[str] = [
    "I isolated the affected workstation and opened a SOC ticket with initial triage notes.",
    "I immediately called the CEO and issued a public press statement before doing any technical investigation.",
    "I blocked the suspicious outbound IP, but I also accidentally blocked the entire /24 subnet.",
    "I notified legal and compliance and preserved forensic images of all affected hosts.",
    "I drafted the regulatory notification, scheduled the post-incident review, and updated the playbook.",
]

SEP = "=" * 72


def _wrap(text: str, width: int = 66, indent: str = "    ") -> str:
    return textwrap.fill(text, width, subsequent_indent=indent)


def _trunc(text: str, n: int = 350) -> str:
    if not text:
        return "(none)"
    t = text.replace("\n", " | ")
    return t[:n] + "…" if len(t) > n else t


def load_scenario(path: str) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    # Accept both full query_structured response and bare scenario object
    if "scenario" in data and "incidents" in data["scenario"]:
        return data["scenario"]
    if "incidents" in data:
        return data
    raise ValueError(
        f"Cannot find a valid scenario in '{path}'. "
        "Expected either a /query_structured response or a bare scenario object."
    )


def load_actions(path: Optional[str]) -> List[str]:
    if not path:
        print("[e2e] No --actions file provided; using built-in demo actions.\n")
        return DEMO_ACTIONS
    with open(path, encoding="utf-8") as f:
        actions = json.load(f)
    if not isinstance(actions, list) or not all(isinstance(a, str) for a in actions):
        raise ValueError(f"'{path}' must contain a JSON array of strings.")
    return actions


LEVEL_EMOJI = {
    "excellent": "🟢",
    "good":      "🟡",
    "partial":   "🟠",
    "missing":   "🔴",
}


def call_grade_step(
    base_url: str,
    scenario_title: str,
    incident_title: str,
    expected_actions: List[str],
    user_action: str,
    timeout: int = 120,
) -> Optional[Dict[str, Any]]:
    """Call /api/v1/grade_step. Returns None on error (non-fatal)."""
    if not expected_actions:
        return None
    body = {
        "scenario_title": scenario_title,
        "incident_title": incident_title,
        "expected_actions": expected_actions,
        "user_action": user_action,
    }
    url = f"{base_url.rstrip('/')}/api/v1/grade_step"
    req = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as exc:
        print(f"  [GRADE WARNING] grade_step failed: {exc}")
        return None


def print_grade(grade: Dict[str, Any]) -> None:
    level = grade.get("level", "?")
    emoji = LEVEL_EMOJI.get(level, "⚪")
    score_pct = int(round(grade.get("score", 0) * 100))
    print(f"\n  {emoji} Grade: {level.upper()}  ({score_pct}/100)")
    print(f"  Feedback : {_wrap(grade.get('feedback',''), 66, '             ')}")
    matched = grade.get("matched_actions", [])
    missed  = grade.get("missed_actions", [])
    if matched:
        print(f"  Matched  : {matched}")
    if missed:
        print(f"  Missed   : {missed}")


def call_next_step(
    base_url: str,
    scenario: Dict[str, Any],
    current: int,
    visited: List[int],
    user_action: str,
    use_llm: bool,
    adapt_inject: bool,
    timeout: int = 180,
) -> Dict[str, Any]:
    body = {
        "scenario": scenario,
        "current_incident_index": current,
        "user_action": user_action,
        "visited_incident_indices": visited,
        "use_llm": use_llm,
        "adapt_inject": adapt_inject,
    }
    url = f"{base_url.rstrip('/')}/api/v1/next_step"
    req = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_bytes = e.read()
        raise RuntimeError(f"HTTP {e.code} from {url}: {body_bytes.decode('utf-8', errors='replace')}") from e


def print_incident(label: str, inc: Dict[str, Any]) -> None:
    print(f"  {'Title':<12}: {inc.get('title','?')}")
    print(f"  {'Timestamp':<12}: {inc.get('message_timestamp','?')}")
    desc = inc.get("description", "")
    print(f"  {'Description':<12}:\n    {_wrap(desc)}")
    inject = inc.get("inject")
    if inject:
        print(f"  {'Inject':<12}: {_trunc(inject)}")


def run(
    scenario: Dict[str, Any],
    actions: List[str],
    base_url: str,
    use_llm: bool,
    adapt_inject: bool,
    grade: bool = True,
) -> None:
    n = len(scenario["incidents"])
    started = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    scenario_title: str = scenario.get("scenario_title", "?")

    print(SEP)
    print(f"  E2E SIMULATION RUN — {started}")
    print(f"  Scenario : {scenario_title}")
    print(f"  Incidents: {n}  |  Actions provided: {len(actions)}")
    print(f"  use_llm  : {use_llm}  |  adapt_inject: {adapt_inject}  |  grade: {grade}")
    print(SEP)

    # STEP 0 — show first incident directly (no next_step call needed)
    first = scenario["incidents"][0]
    print(f"\n{'─'*72}")
    print("  STEP 0 — First incident shown to trainee")
    print(f"{'─'*72}")
    print_incident("", first)

    visited: List[int] = [0]
    current: int = 0
    history: List[Dict[str, Any]] = []

    for step_num, action in enumerate(actions, start=1):
        print(f"\n{'─'*72}")
        print(f"  STEP {step_num} — Trainee action")
        print(f"{'─'*72}")
        print(f"  >> {_wrap(action, 66, '     ')}")

        # Grade the action against the current incident's expected_actions
        grade_result: Optional[Dict[str, Any]] = None
        if grade and use_llm:
            current_inc = scenario["incidents"][current]
            expected = current_inc.get("expected_actions") or []
            grade_result = call_grade_step(
                base_url,
                scenario_title=scenario_title,
                incident_title=current_inc.get("title", ""),
                expected_actions=expected,
                user_action=action,
            )
            if grade_result:
                print_grade(grade_result)

        try:
            resp = call_next_step(
                base_url, scenario, current, visited, action, use_llm, adapt_inject
            )
        except RuntimeError as exc:
            print(f"\n  [ERROR] {exc}")
            break

        # Record history for final summary
        history.append(
            {
                "step": step_num,
                "user_action": action,
                "chosen": resp.get("next_incident_index"),
                "default": resp.get("default_next_incident_index"),
                "matches_default": resp.get("chosen_matches_default"),
                "adapted": resp.get("inject_adapted"),
                "fallback": resp.get("used_fallback"),
                "grade_score": grade_result.get("score") if grade_result else None,
                "grade_level": grade_result.get("level") if grade_result else None,
            }
        )

        if resp.get("is_scenario_complete"):
            print("\n  *** SCENARIO COMPLETE ***")
            break

        idx: int = resp["next_incident_index"]
        dflt: int = resp.get("default_next_incident_index", idx)
        matches: bool = resp.get("chosen_matches_default", True)
        adapted: bool = resp.get("inject_adapted", False)
        fallback: bool = resp.get("used_fallback", False)
        rat: str = resp.get("rationale") or ""
        ni: Dict[str, Any] = resp["next_incident"]

        diverge_tag = "" if matches else "  ← DIVERGED from default"
        adapt_tag = "  [adapted]" if adapted else ""
        fb_tag = "  [FALLBACK]" if fallback else ""

        print(f"\n  Chosen: {idx}  |  Default: {dflt}{diverge_tag}{adapt_tag}{fb_tag}")
        if rat:
            print(f"  Rationale: {_wrap(rat, 66, '             ')}")
        print()
        print_incident("Next incident", ni)

        # advance state
        visited = visited + [idx]
        current = idx

    # Final summary
    print(f"\n{SEP}")
    print("  SIMULATION SUMMARY")
    print(SEP)
    print(f"  Visited indices : {visited}")
    unseen = [i for i in range(n) if i not in visited]
    print(f"  Unseen indices  : {unseen if unseen else '(none — full coverage)'}")
    diverged = [h for h in history if not h.get("matches_default")]
    print(f"  Steps diverged from default : {len(diverged)} / {len(history)}")
    if diverged:
        for h in diverged:
            print(f"    Step {h['step']}: chosen={h['chosen']} default={h['default']}")
    adapted_steps = [h for h in history if h.get("adapted")]
    print(f"  Steps with adapted inject   : {len(adapted_steps)} / {len(history)}")
    fallback_steps = [h for h in history if h.get("fallback")]
    print(f"  LLM fallbacks               : {len(fallback_steps)} / {len(history)}")

    # Grading summary
    graded = [h for h in history if h.get("grade_score") is not None]
    if graded:
        print(f"\n  {'─'*40}")
        print("  GRADING SUMMARY")
        print(f"  {'─'*40}")
        for h in graded:
            emoji = LEVEL_EMOJI.get(h["grade_level"], "⚪")
            score_pct = int(round(h["grade_score"] * 100))
            print(f"  Step {h['step']}: {emoji} {h['grade_level']:<10} {score_pct:>3}/100")
        avg = sum(h["grade_score"] for h in graded) / len(graded)
        avg_pct = int(round(avg * 100))
        avg_level = (
            "excellent" if avg >= 0.9 else
            "good"      if avg >= 0.6 else
            "partial"   if avg >= 0.2 else
            "missing"
        )
        print(f"  {'─'*40}")
        print(f"  Average : {LEVEL_EMOJI[avg_level]} {avg_level:<10} {avg_pct:>3}/100")

    print(SEP)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a full end-to-end simulation via /api/v1/next_step.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--scenario",
        required=True,
        metavar="PATH",
        help="Path to scenario JSON (full query_structured response or bare scenario object).",
    )
    parser.add_argument(
        "--actions",
        metavar="PATH",
        default=None,
        help="Path to JSON file containing a list of user_action strings (one per step). "
        "If omitted, built-in demo actions are used.",
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:6002",
        help="Base URL of the LLM service (default: http://127.0.0.1:6002).",
    )
    parser.add_argument(
        "--no-llm",
        dest="use_llm",
        action="store_false",
        default=True,
        help="Disable LLM selection (always use linear default).",
    )
    parser.add_argument(
        "--no-adapt",
        dest="adapt_inject",
        action="store_false",
        default=True,
        help="Disable inject adaptation (return verbatim incident text).",
    )
    parser.add_argument(
        "--no-grade",
        dest="grade",
        action="store_false",
        default=True,
        help="Disable per-step grading via /api/v1/grade_step.",
    )
    args = parser.parse_args()

    scenario = load_scenario(args.scenario)
    actions = load_actions(args.actions)
    run(scenario, actions, args.url, args.use_llm, args.adapt_inject, args.grade)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
