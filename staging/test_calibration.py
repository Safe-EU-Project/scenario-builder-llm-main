"""TASK 3 smoke-test: verify calibration_score and calibration_sources_count in query_structured response."""
import json, urllib.request

BASE = "http://127.0.0.1:6002"
body = {"query": "A phishing attack on a bank with 3 incidents"}
req = urllib.request.Request(
    f"{BASE}/api/v1/query_structured",
    data=json.dumps(body).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
print("[test] Calling query_structured... (may take 20-30s)")
with urllib.request.urlopen(req, timeout=180) as r:
    d = json.loads(r.read())

print(f"\nScenario    : {d['scenario']['scenario_title']}")
print(f"Incidents   : {len(d['scenario']['incidents'])}")
print(f"\n[CALIBRATION]")
print(f"  score          : {d.get('calibration_score')}")
print(f"  sources_count  : {d.get('calibration_sources_count')}")
print(f"  sources (top3) :")
for s in d.get("sources", [])[:3]:
    print(f"    {s.get('document_name','?')[:50]} — score: {s.get('score')}")

cs = d.get("calibration_score", 0)
sc = d.get("calibration_sources_count", 0)
if cs > 0 and sc > 0:
    print(f"\n  PASS — calibration_score={cs}, sources={sc}")
else:
    print(f"\n  FAIL — calibration_score={cs}, sources={sc}")
