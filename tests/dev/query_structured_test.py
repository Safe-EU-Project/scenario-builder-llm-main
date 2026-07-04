"""
Simple script to query the Scenario Builder structured API
"""

import requests

# API configuration
BASE_URL = "http://10.240.138.254:8002"
QUERY_ENDPOINT = f"{BASE_URL}/api/v1/query_structured"

# Query request
query_data = {
    "query": "data bank",
}

# Make request
response = requests.post(QUERY_ENDPOINT, json=query_data)

# Check response
if response.status_code == 200:
    result = response.json()
    scenario = result.get("scenario", {})

    print(f"Scenario Title: {scenario.get('scenario_title')}")
    print(f"\nTotal Incidents: {len(scenario.get('incidents', []))}\n")

    for idx, incident in enumerate(scenario.get("incidents", []), 1):
        print(f"--- Incident {idx} ---")
        print(f"Title: {incident.get('title')}")
        print(f"Timestamp: {incident.get('message_timestamp')}")
        print(f"Description: {incident.get('description')}")
        print(f"Inject: {incident.get('inject')}")
        print(f"Expected Actions: {incident.get('expected_actions')}\n")
else:
    print(f"Error: {response.status_code} - {response.text}")
