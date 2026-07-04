"""
Simple test to verify structured output works with ChatGPT
"""
from openai import OpenAI
from pydantic import BaseModel

# Configure OpenAI client — set OPENAI_API_KEY env var before running
import os
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY", "")
)


# Define models
class Incident(BaseModel):
    title: str
    message_timestamp: str
    description: str
    inject: str = ""
    expected_actions: list[str] = []


class Scenario(BaseModel):
    scenario_title: str
    incidents: list[Incident]


# Test the structured output
print("Testing ChatGPT structured output...")
print("=" * 70)

try:
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": "Create a scenario about a data breach at a bank with 2 incidents.",
            },
        ],
        response_format=Scenario,
    )

    scenario = completion.choices[0].message.parsed
    print(scenario)

    print("\n✓ SUCCESS!")
    print(f"\nScenario Title: {scenario.scenario_title}")
    print(f"Number of Incidents: {len(scenario.incidents)}")

    for idx, incident in enumerate(scenario.incidents, 1):
        print(f"\n--- Incident {idx} ---")
        print(f"Title: {incident.title}")
        print(f"Timestamp: {incident.message_timestamp}")
        print(f"Description: {incident.description[:100]}...")

except Exception as e:
    print(f"\n✗ Error: {e}")

print("\n" + "=" * 70)
