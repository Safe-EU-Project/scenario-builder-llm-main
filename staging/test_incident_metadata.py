"""
TASK 1 smoke-test: verify that new Incident metadata fields
(attack_technique, target_asset, vulnerability_class, estimated_impact)
are populated by the LLM when generating a scenario via query_structured.
"""
import json
import urllib.request

BASE = "http://127.0.0.1:6002"

body = {"query": "Create a ransomware attack on a hospital with 4 incidents"}
req = urllib.request.Request(
    f"{BASE}/api/v1/query_structured",
    data=json.dumps(body).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)

print("[test] Generating scenario... (may take 20-30s)")
with urllib.request.urlopen(req, timeout=180) as r:
    resp = json.loads(r.read())

scenario = resp["scenario"]
print(f"\nScenario: {scenario['scenario_title']}")
print(f"Incidents: {len(scenario['incidents'])}\n")
print("=" * 65)

new_fields = ["attack_technique", "target_asset", "vulnerability_class", "estimated_impact"]
populated = 0

for i, inc in enumerate(scenario["incidents"]):
    print(f"\n[{i}] {inc['title']}")
    for field in new_fields:
        val = inc.get(field)
        if val:
            populated += 1
            print(f"  {field:25s}: {val}")
        else:
            print(f"  {field:25s}: (null)")

total = len(scenario["incidents"]) * len(new_fields)
print(f"\n{'='*65}")
print(f"  Populated fields: {populated}/{total} ({int(populated/total*100)}%)")
if populated == total:
    print("  PASS — all metadata fields populated")
elif populated > 0:
    print("  PARTIAL — some fields populated (LLM may not always fill all)")
else:
    print("  FAIL — no metadata fields populated")
print("=" * 65)
