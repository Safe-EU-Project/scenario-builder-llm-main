# SCN-APT29-008: Security Tool Disable via Registry — APT29 Defense Evasion

## Description

SUNBURST contains an internal blocklist-check routine that queries Windows processes and services. When it detects security tools (AV, EDR, forensic tools), it disables them by modifying the registry `Start` value under `HKLM\SYSTEM\CurrentControlSet\services\`. This allows the backdoor and the following stages (TEARDROP, BEACON) to operate without interference. Security tool services set to `4` (disabled) will not restart at next boot. APT29 used this technique (T1562.001 — Impair Defenses: Disable or Modify Tools) to ensure persistence without AV/EDR blocking BEACON's C2 activity. The disabling is silent — no user prompt, no event log entry from AV itself. Attribution: APT29 / NOBELIUM / SVR Russia, confidence 90%.

---

## Phase 1 — Detection | T+0

### Inject

| Field | Value |
|-------|-------|
| Alert Source | EDR — Registry Modification Monitor |
| Alert Type | Service startup value modified to disabled |
| Registry Key | `HKLM\SYSTEM\CurrentControlSet\services\WinDefend\Start` |
| Old Value | `2` (Automatic) |
| New Value | `4` (Disabled) |
| Modified By | `SolarWinds.BusinessLayerHost.exe` |
| Timestamp | 2024-04-25 04:02:17 UTC |
| Host | `SRV-ORION-01` (10.10.5.22) |
| Severity | HIGH |

### Expected Actions — System

- [ ] EDR alert — security service startup type changed to disabled
- [ ] Check Windows Defender status — confirm if protection is currently active
- [ ] Correlate with SolarWinds process activity

---

## Phase 2 — Alert | T+5min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | SIEM Correlation |
| Rule Name | `APT29_DISABLE_SECURITY_SERVICES` |
| MITRE Technique | T1562.001 — Impair Defenses: Disable or Modify Tools |
| Services Disabled | `WinDefend` (Windows Defender), `Sense` (Windows Defender ATP), `msmpeng` |
| Modification Pattern | All disabled in 38-second window — automated, not manual |
| Source Process | `SolarWinds.BusinessLayerHost.exe` — SUNBURST infected binary |
| Correlated IOC | SUNBURST mutex `583da945-...` confirmed on same host |

### Expected Actions — System

- [ ] SIEM fires alert — multiple security services disabled in short window
- [ ] Flag modification pattern as automated (SUNBURST behavioral signature)
- [ ] Alert SOC: CRITICAL — host security tools disabled

---

## Phase 3 — Triage | T+15min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | Analyst Review |
| Services Status | WinDefend: STOPPED, Sense: STOPPED, msmpeng: STOPPED |
| Registry Check | `Start = 4` confirmed for all three services |
| Duration | Services have been disabled for 12 days |
| Correlation | TEARDROP (`gracious_truth.jpg`) found in same timeframe — BEACON ran undetected for 12 days |
| AV Logs | No AV detections for 12 days — confirms AV was disabled before TEARDROP deployed |

### Expected Actions — Human

- [ ] Confirm all security services are stopped
- [ ] Understand timeline: AV disabled first → then TEARDROP + BEACON deployed safely
- [ ] Re-enable services via registry (`Start = 2`) and restart
- [ ] After re-enabling — run full AV scan immediately
- [ ] Collect registry change logs for forensic evidence

---

## Phase 4 — Scope Expansion | T+35min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | EDR Fleet Scan |
| Additional Host | `SRV-ORION-02` — same registry modifications found |
| Pattern | Both Orion servers disabled security tools — supply chain compromise affected both |
| GPO Check | Group Policy NOT used for disabling — confirms unauthorized local modification |
| Other Hosts | DC-01 and EXCH-01 — security services still active (not yet modified) |

### Expected Actions — Human

- [ ] Re-enable security services on SRV-ORION-02 as well
- [ ] Verify Group Policy is NOT the source — if GPO, check if GPO itself was tampered
- [ ] Check DC-01 and EXCH-01 proactively — BEACON may modify these later
- [ ] Consider deploying additional monitoring for registry `Start` value changes

---

## Phase 5 — Hardening | T+60min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | SOC Lead — Prevention |
| Recommendation | Protect security service registry keys from modification by non-SYSTEM accounts |
| Detection Gap | 12 days without AV detection — SIEM rules must cover registry changes |
| Patch Status | SolarWinds update released — patch or isolate |

### Expected Actions — Human

- [ ] Add SACL (auditing) on security service registry keys
- [ ] Configure SIEM rule for immediate alert on `services\*\Start` modification to `4`
- [ ] Enforce tamper protection on Windows Defender via Intune/GPO
- [ ] Patch or replace SolarWinds Orion — `2020.2.0` is in compromised build range
- [ ] Incident report: document 12-day AV blind spot and root cause

---

## References

- [MITRE T1562.001 — Impair Defenses: Disable or Modify Tools](https://attack.mitre.org/techniques/T1562/001/)
- [MITRE S0559 — SUNBURST](https://attack.mitre.org/software/S0559/)
- [MITRE ATT&CK Campaign C0024](https://attack.mitre.org/campaigns/C0024/)
- [SolarWinds Orion security advisory](https://www.solarwinds.com/securityadvisory/faq)
- Source Bundle: `apt29-solarwinds-stix-bundle.json` — attack-pattern T1562.001, relationship r012

> **Provenance:** Security tool disable technique, SUNBURST process linkage, actor attribution, TTPs → ✅ APT29 STIX Bundle | Specific registry keys, service names, timeline, scope expansion details → 🤖 LLM (based on bundle data)

---

## Threat Scoring

| Metric | Value |
|--------|-------|
| **Threat Score** | 87 / 100 |
| **Severity** | HIGH |
| **Incident Priority** | P1 — Critical |
| **Response SLA** | Within 1 hour |
| **Confidence** | 90% — HIGH (hard-linked STIX) |
| **Threat Actor Attribution** | APT29 / NOBELIUM / SVR Russia |
| **Score Factors** | 12-day AV blind spot: +35 · Nation-state: +20 · Automated disable: +20 · BEACON running undetected: +12 |
