"""
Simple script to test the GET document endpoint of the Scenario Builder API
"""
import requests

# API configuration
BASE_URL = "http://10.240.138.254:8002"
GET_DOCUMENT_ENDPOINT = f"{BASE_URL}/api/v1/document"

# Replace with your actual document_id
# You get this from the ingest_scenario endpoint response
DOCUMENT_ID = "scenario_20251027_142544_04746b33"

# Make request
response = requests.get(f"{GET_DOCUMENT_ENDPOINT}/{DOCUMENT_ID}")

# Check response
if response.status_code == 200:
    result = response.json()
    print(f"Document ID: {result['document_id']}")
    print("\n" + "=" * 80)
    print("Content:")
    print("=" * 80)
    print(result["content"])
    print("=" * 80)
    print(f"\nTotal length: {len(result['content'])} characters")
elif response.status_code == 404:
    print(f"Document not found: {DOCUMENT_ID}")
    print(response.json())
else:
    print(f"Error: {response.status_code} - {response.text}")
