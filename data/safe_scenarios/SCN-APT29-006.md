# SCN-APT29-006: SUNBURST Single-Instance Mutex — Named Pipe Detected

## Description

EDR detected the creation of a named pipe `583da945-62af-10e8-4902-a8f205c72b2e` on a SolarWinds Orion server. This is the SUNBURST single-instance guard mutex — created to prevent multiple copies of the backdoor from running simultaneously. Its presence is a strong indicator of an active SUNBURST infection even when the DLL hash bypasses AV detection. Unlike file hashes that may be missed due to code-signing bypass, this named pipe is a behavioral indicator that cannot be falsified. Attribution: APT29 / NOBELIUM / SVR Russia, confidence 100%.

---

## Phase 1 — Detection | T+0

### Inject

| Field | Value |
|-------|-------|
| Alert Source | EDR — Named Pipe Creation |
| Alert Type | Suspicious named pipe created by monitored process |
| Named Pipe | `583da945-62af-10e8-4902-a8f205c72b2e` |
| Created By | `SolarWinds.BusinessLayerHost.exe` |
| Host | `SRV-ORION-01` (10.10.5.22) |
| Timestamp | 2024-05-06 03:13:55 UTC |
| Threat Intel Match | SUNBURST mutex — APT29 (confidence: 100%) |
| Severity | CRITICAL |

### Expected Actions — System

- [ ] EDR alert — named pipe matches SUNBURST IOC feed
- [ ] Flag `SolarWinds.BusinessLayerHost.exe` as suspicious process
- [ ] Automatic P1 incident ticket created

---

## Phase 2 — Alert | T+2min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | SIEM Correlation |
| Rule Name | `APT29_SUNBURST_MUTEX_NAMED_PIPE` |
| Purpose | Single-instance guard — prevents duplicate SUNBURST execution |
| Significance | Behavioral IOC — present even if DLL hash evades AV |
| Correlated Event | DNS query to `avsvmcloud.com` from same host — 26 seconds later |
| Threat Actor | APT29 / NOBELIUM / SVR Russia |
| Attribution Confidence | 100% — Hard-linked STIX |

### Expected Actions — System

- [ ] SIEM correlates named pipe with DNS DGA query — confirms SUNBURST active
- [ ] Alert SOC with priority: CRITICAL
- [ ] Block DNS queries to `*.avsvmcloud.com` immediately

---

## Phase 3 — Triage | T+10min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | Analyst Review |
| Named Pipe Still Active | YES — pipe is open, SUNBURST running |
| DLL Check | `SolarWinds.Orion.Core.BusinessLayer.dll` hash = `b91ce2fa...` — CONFIRMED SUNBURST |
| AV Status | No AV detection on DLL (code-signing bypass — T1553.002) |
| Process Age | Started 14 days ago (dormancy period completed) |
| Orion Version | 2020.2.0 — affected range |

### Expected Actions — Human

- [ ] Confirm named pipe is still open — SUNBURST actively running
- [ ] Verify DLL hash even though AV did not flag it
- [ ] Understand: code-signing bypass is why AV missed it — named pipe reveals it
- [ ] Check Orion version — confirm in affected range

---

## Phase 4 — Behavioral Investigation | T+20min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | Memory + Process Analysis |
| SUNBURST Status | Active — dormancy period ended, now in C2 phase |
| DNS Queries | 847 queries to `*.avsvmcloud.com` over 14 days |
| Blocklist Check | SUNBURST scanned for security tools — disabled `WinDefend` via registry |
| Registry Modified | `HKLM\SYSTEM\CurrentControlSet\services\WinDefend\Start` → set to `4` (disabled) |
| Second-Stage | `gracious_truth.jpg` found in SysWOW64 — TEARDROP present |

### Expected Actions — Human

- [ ] Check Windows Defender status — was it disabled via registry? (T1562.001)
- [ ] Re-enable security services disabled by SUNBURST
- [ ] Confirm TEARDROP / BEACON also present — full infection chain
- [ ] Collect memory dump before isolating host

---

## Phase 5 — Containment | T+40min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | SOC Lead |
| Full Chain Confirmed | SUNBURST (mutex) → TEARDROP (gracious_truth.jpg) → BEACON (C2 IPs) |
| Security Disabled | WinDefend disabled for 14 days |
| Scope | SRV-ORION-01 confirmed; check SRV-ORION-02 |

### Expected Actions — Human

- [ ] Terminate named pipe — kill `SolarWinds.BusinessLayerHost.exe`
- [ ] Restore disabled security services via registry (`Start = 2`)
- [ ] Isolate host and block all C2 domains/IPs
- [ ] Scan SRV-ORION-02 for same named pipe
- [ ] Document: named pipe = behavioral detection bypass for signed DLL

---

## References

- [MITRE S0559 - SUNBURST](https://attack.mitre.org/software/S0559/)
- [FireEye SUNBURST named pipe analysis](https://cloud.google.com/blog/topics/threat-intelligence/evasive-attacker-leverages-solarwinds-supply-chain-compromises-with-sunburst-backdoor)
- [MITRE ATT&CK Campaign C0024](https://attack.mitre.org/campaigns/C0024/)
- Source Bundle: `apt29-solarwinds-stix-bundle.json` — indicator a1b2c3d4

> **Provenance:** Named pipe value, single-instance guard purpose, actor attribution, AV bypass via code signing → ✅ APT29 STIX Bundle | Phase structure, process age, registry details, timeline → 🤖 LLM (based on bundle data)

---

## Threat Scoring

| Metric | Value |
|--------|-------|
| **Threat Score** | 95 / 100 |
| **Severity** | CRITICAL |
| **Incident Priority** | P1 — Critical |
| **Response SLA** | Immediate |
| **Confidence** | 100% — CONFIRMED (hard-linked STIX) |
| **Threat Actor Attribution** | APT29 / NOBELIUM / SVR Russia |
| **Score Factors** | Behavioral IOC bypassed AV: +30 · Active C2 + TEARDROP: +30 · Security tools disabled: +20 · Nation-state: +15 |
