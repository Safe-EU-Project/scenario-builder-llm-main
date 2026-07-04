"""
Simple script to query the Scenario Builder API
"""
import json

import requests

# API configuration
BASE_URL = "http://10.240.138.254:8002"
QUERY_ENDPOINT = f"{BASE_URL}/api/v1/query_structured"

# Query request
query_data = {"query": "data bank"}

# Make request
response = requests.post(QUERY_ENDPOINT, json=query_data)

# Check response
if response.status_code == 200:
    result = response.json()
    scenario = result.get("scenario")
    print(json.dumps(scenario, indent=4))

else:
    print(f"Error: {response.status_code} - {response.text}")
