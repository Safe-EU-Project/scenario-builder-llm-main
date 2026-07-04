"""Generate a scenario via query_structured and save to file."""
import json, urllib.request, sys

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:6002"
OUT  = sys.argv[2] if len(sys.argv) > 2 else "/tmp/sb_10incidents.json"
QUERY = (
    "Create a detailed cybersecurity incident response scenario with exactly 10 incidents, "
    "covering detection, containment, eradication, recovery, and lessons learned phases. "
    "Each incident must have at least 3 expected_actions."
)

body = {"query": QUERY}
req = urllib.request.Request(
    f"{BASE}/api/v1/query_structured",
    data=json.dumps(body).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
print(f"[gen] Calling query_structured... (may take 30-60s)")
with urllib.request.urlopen(req, timeout=300) as r:
    resp = json.loads(r.read())

sc = resp.get("scenario", resp)
n = len(sc.get("incidents", []))
print(f"[gen] Got {n} incidents: {sc.get('scenario_title','?')}")

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(resp, f, ensure_ascii=False, indent=2)
print(f"[gen] Saved to {OUT}")
