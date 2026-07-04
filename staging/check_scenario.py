import json, sys
path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/sb_10incidents.json"
d = json.load(open(path))
sc = d.get("scenario", d)
print(f"Title    : {sc.get('scenario_title','?')}")
print(f"Incidents: {len(sc['incidents'])}")
for i, inc in enumerate(sc["incidents"]):
    ea = len(inc.get("expected_actions") or [])
    print(f"  [{i}] {inc['title']}  ({ea} expected_actions)")
