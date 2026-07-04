---
description: Update README documentation to reflect current codebase features and verify everything is up to date
---

Please perform a comprehensive documentation review and update:

## Task: Update and Verify Documentation

### 1. Analyze Current State
- Review recent git commits (last 5-10 commits) to identify new features, changes, or deprecations
- Read the current README.md file
- Scan the main API endpoints in src/api/api.py to identify all available endpoints
- Check configuration models in src/config/models.py for any new request/response models
- Review src/llm/llm_client.py for any new LLM capabilities

### 2. Identify Documentation Gaps
Compare what's in the code vs what's documented in README.md:
- Are all API endpoints documented with correct paths?
- Are there new features that aren't mentioned?
- Are the configuration options complete and accurate?
- Are there new response models or structured outputs that should be documented?
- Are there any deprecated features still mentioned in docs?
- Are example curl commands correct and complete?

### 3. Update README if Necessary
If gaps are found, update the README.md to include:
- New API endpoints with correct paths (e.g., /api/v1/query_structured, /api/v1/ingest_scenario)
- New features like structured scenario generation, JSON schema mode, etc.
- Updated request/response examples with all available fields
- New configuration options in the .env section
- Updated architecture or workflow descriptions if needed
- Any new dependencies or requirements

### 4. Verification
After updates:
- Ensure all endpoint paths match the actual API routes
- Verify that example requests include all important parameters
- Check that response examples match the actual Pydantic models
- Confirm configuration variables match settings.py
- Make sure the documentation is clear, concise, and well-organized

### 5. Summary
Provide a brief summary of:
- What changes were made to the README (if any)
- What features are now properly documented
- Any recommendations for additional documentation needs

**Important**:
- Be thorough in checking endpoint paths (e.g., /api/v1/query vs /query)
- Include all new structured output capabilities
- Document the scenario ingestion feature if not already present
- Ensure examples are accurate and copy-paste ready
