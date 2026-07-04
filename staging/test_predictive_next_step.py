"""
TASK 2 smoke-test: verify predicted_threat_vector and predicted_impact
are returned by POST /api/v1/next_step.
"""
import json
import urllib.request

BASE = "http://127.0.0.1:6002"
SCENARIO_FILE = "/tmp/sb_10incidents.json"

d = json.load(open(SCENARIO_FILE))
scenario = d.get("scenario", d)

body = {
    "scenario": scenario,
    "current_incident_index": 0,
    "visited_incident_indices": [0],
    "user_action": "I noticed the alert but did nothing — I assumed it was a false positive.",
    "use_llm": True,
    "adapt_inject": False,
}

req = urllib.request.Request(
    f"{BASE}/api/v1/next_step",
    data=json.dumps(body).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)

print("[test] Calling next_step... (may take 10-15s)")
with urllib.request.urlopen(req, timeout=120) as r:
    resp = json.loads(r.read())

print(f"\n{'='*65}")
print("  NEXT STEP — PREDICTIVE ANALYSIS TEST")
print(f"{'='*65}")
print(f"  Next incident    : [{resp['next_incident_index']}] {resp['next_incident']['title']}")
print(f"  Rationale        : {resp['rationale']}")
print(f"\n  [PREDICTIVE]")
print(f"  Threat vector    : {resp.get('predicted_threat_vector', '(null)')}")
print(f"  Impact           : {resp.get('predicted_impact', '(null)')}")
print(f"\n  used_fallback    : {resp['used_fallback']}")
print(f"{'='*65}")

ptv = resp.get("predicted_threat_vector")
pi_ = resp.get("predicted_impact")
if ptv and pi_:
    print("\n  PASS — both predictive fields populated")
elif ptv or pi_:
    print("\n  PARTIAL — only one predictive field populated")
else:
    print("\n  FAIL — no predictive fields")
