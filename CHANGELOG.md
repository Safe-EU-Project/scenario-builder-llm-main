# Changelog — LLM Service

## [1.0.0] — 2026-06-23 · First Stable Release

### New Endpoints

- **POST `/api/v1/policy_draft`** — Accepts scenario metadata and aggregated trainee performance data; returns a structured policy document suitable for LEA review. Output covers executive summary, identified risks, recommended procedures, controls, resource requirements, and policy recommendations.
- **POST `/api/v1/debrief`** — Generates an end-of-simulation performance debrief for a trainee.

### Improvements

- `next_step` responses now include **predictive threat analysis** fields: probability distribution over likely follow-on attack vectors, calibration score, and supporting source count.
- `grade_step` uses an LLM evaluator instead of cosine similarity, producing richer qualitative feedback.
- Scenario model extended with optional metadata fields (`scenario_description`, `threat_actor`, `threat_type`, `target_sector`, `attack_vector`) used to enrich policy drafts and threat predictions.
- System prompts hardened to prevent hallucinated references to external standards or documents.

### Internal

- Policy drafting logic isolated in `src/scenario/policy_drafter.py`.
- Pydantic schemas for all new endpoints defined in `src/config/models.py`.
