"""
Simple script to query the Scenario Builder API
"""
import requests

# API configuration
BASE_URL = "http://10.240.138.254:8002"
QUERY_ENDPOINT = f"{BASE_URL}/api/v1/query"

# Query request
query_data = {
    "query": "data bank",
}

# Make request
response = requests.post(QUERY_ENDPOINT, json=query_data)

# Check response
if response.status_code == 200:
    result = response.json()
    print(result["answer"])
else:
    print(f"Error: {response.status_code} - {response.text}")
