import json, urllib.request

BASE = "http://127.0.0.1:6002/api/v1/next_step"
STAGING = "/home/intrasoft/Documents/Scenario-builder-llm/scenario-builder-llm/staging"
scenario = json.load(open(STAGING + "/sb_scenario_only.json"))

HISTORY = (
    "Step 0: Called the CEO and issued a public press statement before any technical investigation.\n"
    "Step 1: Tried to isolate the workstation but accidentally wiped the event logs.\n"
    "Step 2: Blocked the entire /24 subnet by mistake, disrupting legitimate services."
)

def call(history_summary=None, label=""):
    body = {
        "scenario": scenario,
        "current_incident_index": 2,
        "user_action": "I blocked the entire /24 subnet by mistake and disrupted legitimate services.",
        "visited_incident_indices": [0, 1, 2],
        "use_llm": True,
        "adapt_inject": True,
    }
    if history_summary:
        body["history_summary"] = history_summary
    req = urllib.request.Request(
        BASE,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        resp = json.loads(r.read())
    inc = resp["next_incident"]
    print(f"\n{'='*65}")
    print(f"  {label}")
    print(f"{'='*65}")
    print(f"  Next: {inc['title']}")
    print(f"  Description:\n    {inc['description'][:400]}")
    print(f"  Inject:\n    {(inc['inject'] or '')[:300]}")

call(label="WITHOUT history_summary")
call(history_summary=HISTORY, label="WITH history_summary")
