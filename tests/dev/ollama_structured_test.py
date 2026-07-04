"""
Simple test to verify structured output works with ChatGPT
"""
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
        print(scenario.parsed)
    elif scenario.refusal:
        print(scenario.refusal)


except Exception as e:
    if type(e) == openai.LengthFinishReasonError:
        print("Too many tokens: ", e)
        pass
    else:
        print(e)
        pass

print("\n" + "=" * 70)
