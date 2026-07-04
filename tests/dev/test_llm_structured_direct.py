"""
Direct test of LLM structured output
"""
import json
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.config.models import Scenario
from src.llm.llm_client import LLMClient

# Initialize LLM client
llm_client = LLMClient()

# Get schema
schema = Scenario.model_json_schema()

# Create messages
messages = [
    {"role": "user", "content": "Create a scenario about a data breach at a bank with 3 incidents."}
]

print("Calling LLM with structured output...\n")

# Call LLM directly
json_response = llm_client._call_llm_structured(messages, schema)

print("RAW LLM RESPONSE:")
print("=" * 70)
print(json_response)
print("=" * 70)

# Parse and validate
try:
    response_data = json.loads(json_response)
    scenario = Scenario.model_validate(response_data)

    print(f"\n✓ Valid! Scenario: {scenario.scenario_title}")
    print(f"✓ Incidents: {len(scenario.incidents)}")
except Exception as e:
    print(f"\n✗ Error: {e}")
