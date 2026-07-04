"""Smoke-test for POST /api/v1/debrief using the 10-incident scenario."""
import json, urllib.request

BASE = "http://127.0.0.1:6002"
SCENARIO_FILE = "/tmp/sb_10incidents.json"

d = json.load(open(SCENARIO_FILE))
scenario = d.get("scenario", d)

# Simulated history — mirrors what the frontend would accumulate
HISTORY = [
    {"incident_index": 0, "incident_title": "SOC Alert: Unusual Outbound Traffic to External IP",
     "user_action": "I verified the alert, cross-checked the destination IP against threat intel, and notified the Network Security team.",
     "grade_score": 0.75, "grade_level": "good"},
    {"incident_index": 1, "incident_title": "SIEM Correlation: Potential Data Exfiltration",
     "user_action": "I isolated the workstation, took a forensic image, ran an AV scan, and notified the affected user.",
     "grade_score": 0.25, "grade_level": "partial"},
    {"incident_index": 2, "incident_title": "Endpoint Detection: Ransomware on Employee Workstation",
     "user_action": "I identified the compromised subnet, ran Nmap to map lateral movement, and updated the SOC ticket.",
     "grade_score": 0.0, "grade_level": "missing"},
    {"incident_index": 5, "incident_title": "Containment: Isolate Affected Subnet",
     "user_action": "I sent an incident briefing to all stakeholders, defined the scope, assigned roles, and scheduled the response meeting.",
     "grade_score": 0.25, "grade_level": "partial"},
    {"incident_index": 4, "incident_title": "Incident Commander Convenes Response Team",
     "user_action": "I executed the firewall rule to block the affected subnet, verified the cut-off, and notified the affected business units.",
     "grade_score": 0.25, "grade_level": "partial"},
    {"incident_index": 3, "incident_title": "Network Segmentation Breach: Compromised Subnet",
     "user_action": "I removed malicious binaries, whitelisted legitimate ones, reset compromised passwords, and ran a full system scan.",
     "grade_score": 0.0, "grade_level": "missing"},
    {"incident_index": 6, "incident_title": "Eradication: Remove Malicious Binaries",
     "user_action": "I restored the database from the last clean backup and validated data integrity before bringing it online.",
     "grade_score": 0.0, "grade_level": "missing"},
    {"incident_index": 8, "incident_title": "Stakeholder Communication: Public Statement",
     "user_action": "I drafted the public statement, coordinated with PR, and published it to customers and media.",
     "grade_score": 0.5, "grade_level": "partial"},
    {"incident_index": 7, "incident_title": "Recovery: Restore Database from Backup",
     "user_action": "I drafted the regulatory notification and submitted it within 72 hours.",
     "grade_score": 0.0, "grade_level": "missing"},
    {"incident_index": 9, "incident_title": "Lessons Learned & Incident Closure",
     "user_action": "I conducted the lessons learned meeting, updated the incident playbook, and archived all evidence.",
     "grade_score": 0.5, "grade_level": "partial"},
]

body = {"scenario": scenario, "history": HISTORY}
req = urllib.request.Request(
    f"{BASE}/api/v1/debrief",
    data=json.dumps(body).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
print("[debrief] Calling... (may take 15-30s)")
with urllib.request.urlopen(req, timeout=180) as r:
    resp = json.loads(r.read())

print(f"\n{'='*65}")
print(f"  DEBRIEF REPORT")
print(f"{'='*65}")
print(f"  Overall score : {resp['overall_score']} ({int(resp['overall_score']*100)}/100)")
print(f"  Overall level : {resp['overall_level'].upper()}")
print(f"  Used fallback : {resp['used_fallback']}")
print(f"\n  Summary:\n    {resp['summary']}")
print(f"\n  Strengths:")
for s in resp["strengths"]:
    print(f"    ✓ {s}")
print(f"\n  Gaps:")
for g in resp["gaps"]:
    print(f"    ✗ {g}")
print(f"\n  Recommendations:")
for r_ in resp["recommendations"]:
    print(f"    → {r_}")
print(f"{'='*65}")
