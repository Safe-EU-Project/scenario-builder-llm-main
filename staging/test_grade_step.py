"""Quick smoke-test for POST /api/v1/grade_step."""
import json, urllib.request

BASE = "http://127.0.0.1:6002/api/v1/grade_step"

CASES = [
    {
        "label": "EXCELLENT — all actions covered",
        "body": {
            "scenario_title": "Unauthorized Access to Customer Data",
            "incident_title": "SIEM Alert: Suspicious Admin Login",
            "expected_actions": [
                "isolate the affected workstation",
                "open a SOC ticket with initial triage notes",
                "preserve forensic images of the system",
                "notify legal and compliance team",
            ],
            "user_action": (
                "I isolated the workstation, opened a SOC ticket with triage notes, "
                "took forensic images of the disk, and notified legal and compliance."
            ),
        },
    },
    {
        "label": "PARTIAL — 2 of 4 actions",
        "body": {
            "scenario_title": "Unauthorized Access to Customer Data",
            "incident_title": "SIEM Alert: Suspicious Admin Login",
            "expected_actions": [
                "isolate the affected workstation",
                "open a SOC ticket with initial triage notes",
                "preserve forensic images of the system",
                "notify legal and compliance team",
            ],
            "user_action": "I isolated the affected workstation and opened a SOC ticket.",
        },
    },
    {
        "label": "MISSING — wrong action entirely",
        "body": {
            "scenario_title": "Unauthorized Access to Customer Data",
            "incident_title": "SIEM Alert: Suspicious Admin Login",
            "expected_actions": [
                "isolate the affected workstation",
                "open a SOC ticket with initial triage notes",
                "preserve forensic images of the system",
                "notify legal and compliance team",
            ],
            "user_action": "I called the CEO and issued a public press statement.",
        },
    },
]


def call(body):
    req = urllib.request.Request(
        BASE,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


for case in CASES:
    print(f"\n{'='*60}")
    print(f"  {case['label']}")
    print(f"{'='*60}")
    resp = call(case["body"])
    print(f"  score        : {resp['score']}")
    print(f"  level        : {resp['level']}")
    print(f"  feedback     : {resp['feedback']}")
    print(f"  matched      : {resp['matched_actions']}")
    print(f"  missed       : {resp['missed_actions']}")
    print(f"  used_fallback: {resp['used_fallback']}")
