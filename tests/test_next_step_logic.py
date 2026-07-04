"""Unit tests for next-step allowlist / default index helpers and adapt (no LLM)."""

import unittest

from src.config.models import AdaptLLMResult, Incident, NextStepLLMResult, Scenario
from src.scenario.next_step import (
    apply_adapt_result,
    build_visited_summary,
    default_next_index,
    eligible_indices,
    incident_to_trainee_view,
    validate_next_step_request,
)


def _sample_scenario(n: int = 4) -> Scenario:
    incidents = [
        Incident(
            title=f"Event {i}",
            message_timestamp=f"T+{i}",
            description=f"Description {i}",
            inject=f"Inject {i}",
            expected_actions=[f"act-{i}-a", f"act-{i}-b"],
        )
        for i in range(n)
    ]
    return Scenario(scenario_title="Test breach", incidents=incidents)


class TestNextStepLogic(unittest.TestCase):
    def test_trainee_view_hides_expected_actions(self):
        inc = _sample_scenario().incidents[0]
        view = incident_to_trainee_view(inc)
        self.assertEqual(view.title, inc.title)
        self.assertFalse(hasattr(view, "expected_actions") or getattr(view, "expected_actions", None))

    def test_eligible_after_first_visit(self):
        n = 4
        eligible = eligible_indices(n, [0])
        self.assertEqual(eligible, [1, 2, 3])

    def test_default_prefers_forward(self):
        n = 5
        self.assertEqual(default_next_index(n, [0], 0), 1)
        self.assertEqual(default_next_index(n, [0, 1], 1), 2)

    def test_default_wraps_when_forward_blocked(self):
        n = 4
        # seen 0,2,3 — after answering 2, forward finds 3? 3 is visited. then wrap to 1
        self.assertEqual(default_next_index(n, [0, 2, 3], 2), 1)

    def test_validate_requires_current_in_visited(self):
        sc = _sample_scenario()
        ok, msg = validate_next_step_request(sc, 0, [])
        self.assertFalse(ok)
        self.assertIn("visited", msg or "")

    def test_validate_ok(self):
        sc = _sample_scenario()
        ok, msg = validate_next_step_request(sc, 0, [0])
        self.assertTrue(ok)
        self.assertIsNone(msg)

    def test_validate_rejects_duplicate_visited(self):
        sc = _sample_scenario()
        ok, msg = validate_next_step_request(sc, 0, [0, 0])
        self.assertFalse(ok)
        self.assertIn("duplicate", (msg or "").lower())


class TestAdaptInject(unittest.TestCase):
    def _sample_incident(self) -> Incident:
        return Incident(
            title="Credential Alert",
            message_timestamp="T+0 (09:00)",
            description="Admin login from unknown IP.",
            inject="Log: login success from 1.2.3.4",
            expected_actions=["isolate host", "notify SOC"],
        )

    def test_apply_adapt_result_keeps_title_and_timestamp(self):
        inc = self._sample_incident()
        adapt = AdaptLLMResult(
            adapted_description="The attacker has moved laterally. New alert incoming.",
            adapted_inject="Alert: lateral movement detected on FIN-WS-02",
        )
        view = apply_adapt_result(inc, adapt)
        self.assertEqual(view.title, inc.title)
        self.assertEqual(view.message_timestamp, inc.message_timestamp)

    def test_apply_adapt_result_replaces_description_and_inject(self):
        inc = self._sample_incident()
        new_desc = "The host has been isolated. DLP now shows outbound traffic."
        new_inject = "DLP: 1.1 GB exfiltrated to 5.6.7.8"
        adapt = AdaptLLMResult(adapted_description=new_desc, adapted_inject=new_inject)
        view = apply_adapt_result(inc, adapt)
        self.assertEqual(view.description, new_desc)
        self.assertEqual(view.inject, new_inject)

    def test_apply_adapt_result_falls_back_to_original_inject_when_none(self):
        inc = self._sample_incident()
        adapt = AdaptLLMResult(
            adapted_description="Updated description.",
            adapted_inject=None,
        )
        view = apply_adapt_result(inc, adapt)
        self.assertEqual(view.inject, inc.inject)

    def test_adapt_result_no_expected_actions_in_view(self):
        inc = self._sample_incident()
        adapt = AdaptLLMResult(adapted_description="desc", adapted_inject="inject")
        view = apply_adapt_result(inc, adapt)
        self.assertFalse(hasattr(view, "expected_actions") or getattr(view, "expected_actions", None))


class TestRationaleRequired(unittest.TestCase):
    def test_rationale_required_non_empty(self):
        """NextStepLLMResult must reject empty / missing rationale."""
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            NextStepLLMResult(chosen_incident_index=0, rationale="")

    def test_rationale_required_missing(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            NextStepLLMResult(chosen_incident_index=0)

    def test_rationale_valid(self):
        r = NextStepLLMResult(
            chosen_incident_index=2,
            rationale="Because the trainee wiped the server, forensic evidence is lost.",
        )
        self.assertEqual(r.chosen_incident_index, 2)
        self.assertGreater(len(r.rationale), 10)


class TestVisitedSummary(unittest.TestCase):
    def test_visited_summary_excludes_current(self):
        sc = _sample_scenario(4)
        summary = build_visited_summary(sc, [0, 1, 2], current=2)
        self.assertIn("Event 0", summary)
        self.assertIn("Event 1", summary)
        self.assertNotIn("Event 2", summary)

    def test_visited_summary_empty_when_only_current(self):
        sc = _sample_scenario(4)
        summary = build_visited_summary(sc, [0], current=0)
        self.assertIn("none", summary.lower())


if __name__ == "__main__":
    unittest.main()
