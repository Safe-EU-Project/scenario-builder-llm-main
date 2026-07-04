# Development scope (SB improvements)

## Current phase

For the first iteration of Scenario Builder improvements, work focuses on:

- **This repo** (`scenario-builder-llm-main`) — RAG pipeline, API (`/query`, `/query_structured`, `/ingest_scenario`), LLM client, prompts.
- **Backend** (`BackEnd-SB-master`) — FastAPI, Mongo, calls into this service.

## Out of scope (for now)

- **Frontend** (gaandalf / Scenario-Builder-FrontEnd-SB) — unchanged unless the team explicitly extends scope.

## Rationale

Evolve LLM and API behaviour without requiring frontend releases for the same iteration.

## Docker image (staging vs prod)

Compose files set **`image: scenario-builder-llm:staging`** next to `build:` so `docker compose build` tags a **named image** that is easy to tell apart from anonymous or production images on the GPU server (e.g. prod may keep using another tag or compose project). Push that tag to your registry when deploying staging; use a different tag (e.g. `:prod` or `:release`) for production if you adopt the same pattern there.
