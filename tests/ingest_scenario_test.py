"""
Simple script to test the Scenario Ingestion API endpoint
"""
import requests

# API configuration
BASE_URL = "http://10.240.138.254"
INGEST_ENDPOINT = f"{BASE_URL}/api/v1/ingest_scenario"

# Sample scenario content (human-reviewed LLM-generated scenario)
scenario_content = """  """

# Prepare request
ingest_data = {"content": scenario_content}

print("Sending scenario to ingestion endpoint...")
print("-" * 60)

# Make request
response = requests.post(INGEST_ENDPOINT, json=ingest_data)

# Check response
if response.status_code == 200:
    result = response.json()
    print("SUCCESS!")
    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")
else:
    print(f"ERROR: {response.status_code}")
    print(f"Details: {response.text}")
