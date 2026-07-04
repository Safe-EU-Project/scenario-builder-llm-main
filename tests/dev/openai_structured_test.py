"""
Simple test to verify structured output works with ChatGPT
"""
import json

from openai import OpenAI
from pydantic import BaseModel

# Configure OpenAI client
client = OpenAI(base_url="http://10.240.138.254:11434/v1", api_key="ollama")


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
        model="chat:gpt-oss",
        messages=[
            {
                "role": "user",
                "content": "Create a scenario about a data breach at a bank with 9-12 incidents.return as JSON",
            },
        ],
        response_format=Scenario,
        temperature=0.0,
    )

    scenario = completion.choices[0].message

    if scenario.parsed:
        print("\n✓ Structured Output Successfully Generated\n")

        # Pretty print the scenario
        scenario_dict = scenario.parsed.model_dump()

        print(f"📋 Scenario Title: {scenario_dict['scenario_title']}")
        print(f"\n📊 Total Incidents: {len(scenario_dict['incidents'])}")
        print("\n" + "─" * 70 + "\n")

        for i, incident in enumerate(scenario_dict["incidents"], 1):
            print(f"Incident #{i}")
            print(f"  Title: {incident['title']}")
            print(f"  Timestamp: {incident['message_timestamp']}")
            print(
                f"  Description: {incident['description'][:100]}{'...' if len(incident['description']) > 100 else ''}"
            )
            if incident.get("inject"):
                print(
                    f"  Inject: {incident['inject'][:80]}{'...' if len(incident['inject']) > 80 else ''}"
                )
            if incident.get("expected_actions"):
                print(f"  Expected Actions: {len(incident['expected_actions'])} action(s)")
            print()

        print("─" * 70)
        print("\n📄 Full JSON Output:\n")
        print(json.dumps(scenario_dict, indent=2))

    elif scenario.refusal:
        print(f"\n✗ Request Refused: {scenario.refusal}")

except Exception as e:
    print(f"\n✗ Error occurred: {type(e).__name__}")
    print(f"   {str(e)}")

print("\n" + "=" * 70)
