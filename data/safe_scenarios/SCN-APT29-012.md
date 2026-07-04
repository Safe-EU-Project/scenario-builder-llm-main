# SCN-APT29-012: Evidence Removal via SDelete — APT29 Anti-Forensics

## Description

A volume of forensic activity was observed when SDelete (`sdelete64.exe`) was executed on the compromised SolarWinds Orion server, systematically overwriting and deleting files related to the SUNBURST compromise. APT29 / NOBELIUM used this technique (T1070.004 — Indicator Removal: File Deletion) during the cleanup phase of their operation to destroy forensic artifacts — logs, staging files, TEARDROP dropper, and tooling. SDelete performs multiple-pass overwrites so files cannot be recovered with disk forensics. Fortunately, most artifacts were already copied to SIEM and EDR before deletion. Attribution: APT29 / NOBELIUM / SVR Russia, confidence 85%.

---

## Phase 1 — Detection | T+0

### Inject

| Field | Value |
|-------|-------|
| Alert Source | EDR — Process Monitoring |
| Alert Type | SDelete executing recursive deletion of sensitive paths |
| Binary | `sdelete64.exe` (Sysinternals — legitimate but misused) |
| Command | `sdelete64.exe -p 7 -s -q C:\Windows\Temp\cab_*.tmp` |
| Parent Process | `cmd.exe` → `SolarWinds.BusinessLayerHost.exe` |
| Timestamp | 2024-05-10 05:00:45 UTC |
| Passes | 7-pass overwrite — forensically unrecoverable |
| Severity | HIGH |

### Expected Actions — System

- [ ] EDR alert — SDelete (known forensic-evasion tool) executed
- [ ] Capture process command line before execution completes
- [ ] EDR should have preserved file hashes before deletion (if EDR was active)

---

## Phase 2 — Alert | T+3min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | SIEM Correlation |
| Rule Name | `APT29_SDELETE_ANTI_FORENSICS` |
| MITRE Technique | T1070.004 — Indicator Removal: File Deletion |
| Files Targeted | `cab_*.tmp` (staged archives), `gracious_truth.jpg` (TEARDROP), `sdelete64.exe` itself |
| Secondary Command | `sdelete64.exe -p 3 -s -q C:\Users\svc-monitoring\AppData\Local\Temp\` |
| Tool Source | Downloaded by BEACON — not previously installed on server |
| Timing | Executed 10 minutes after C2 connection was blocked — actor is covering tracks |

### Expected Actions — System

- [ ] SIEM alert — SDelete used after C2 block (actor noticed block, initiating cleanup)
- [ ] Alert SOC: attacker is destroying evidence — initiate emergency memory dump
- [ ] Preserve all SIEM logs and EDR telemetry immediately — actor can't delete these

---

## Phase 3 — Forensics Race | T+8min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | Incident Response Team |
| Status | SDelete still running — active deletion |
| Files Deleted | `cab_0035.tmp` through `cab_0041.tmp` — remaining unexfiltrated archives GONE |
| Files Deleted | `gracious_truth.jpg` — TEARDROP dropper deleted |
| Remaining | `SolarWinds.Orion.Core.BusinessLayer.dll` — NOT deleted (still in use by process) |
| SIEM Coverage | EDR telemetry preserved everything — file hashes, process chains, registry changes |

### Expected Actions — Human

- [ ] IMMEDIATE: take memory dump of `SolarWinds.BusinessLayerHost.exe` RIGHT NOW
- [ ] Confirm what was deleted — compare to known file inventory from earlier phases
- [ ] Preserve: SIEM logs, EDR logs, firewall logs before attempting to isolate
- [ ] Note: actor deliberately preserved remaining archives that were NOT yet exfiltrated — unusual

---

## Phase 4 — Forensic Preservation | T+25min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | Forensic Team |
| Memory Dump | Captured successfully — contains BEACON in-memory config |
| BEACON C2 Config | Extracted: C2 IPs, sleep interval, jitter, staging paths |
| Event Logs | Windows Security, System, Application logs — NOT deleted (actor did not target these) |
| File Recovery | SDelete 7-pass = unrecoverable — no file recovery possible |
| Alternative Evidence | Network captures, SIEM aggregated logs, EDR telemetry — comprehensive |

### Expected Actions — Human

- [ ] Preserve memory dump in isolated storage — contains BEACON C2 config
- [ ] Generate forensic image of disk before reimaging
- [ ] Document: actor did NOT wipe event logs — Windows event logs preserved
- [ ] Timeline reconstruction: can be done from SIEM + EDR even without local files
- [ ] Prepare for law enforcement handover if applicable (nation-state incident)

---

## Phase 5 — Post-Incident | T+120min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | SOC Lead — Lessons Learned |
| Gap | SDelete was allowed to execute — should have been blocked by application allowlist |
| Gap 2 | 10-minute delay between C2 block and SDelete detection — monitoring lag |
| Positive | EDR pre-served all file hashes before deletion — forensics possible |

### Expected Actions — Human

- [ ] Block SDelete and similar tools (cipher.exe for overwrite) via application allowlist
- [ ] Add SIEM rule: SDelete execution on any server = immediate critical alert
- [ ] Improve monitoring: changes in C2 connection status should trigger increased logging
- [ ] Training recommendation: analysts should immediately initiate memory dump when C2 blocked

---

## References

- [MITRE T1070.004 — Indicator Removal: File Deletion](https://attack.mitre.org/techniques/T1070/004/)
- [Sysinternals SDelete](https://docs.microsoft.com/en-us/sysinternals/downloads/sdelete)
- [MITRE ATT&CK Campaign C0024](https://attack.mitre.org/campaigns/C0024/)
- Source Bundle: `apt29-solarwinds-stix-bundle.json` — attack-pattern T1070.004, tool s0195 (SDelete), relationship r022

> **Provenance:** SDelete tool use, file deletion technique, actor attribution → ✅ APT29 STIX Bundle | 7-pass command, timing post-C2-block, race condition details, forensics gap analysis → 🤖 LLM (based on bundle data)

---

## Threat Scoring

| Metric | Value |
|--------|-------|
| **Threat Score** | 82 / 100 |
| **Severity** | HIGH — Anti-Forensics |
| **Incident Priority** | P1 — Critical |
| **Response SLA** | Immediate — Forensics Race Condition |
| **Confidence** | 85% — HIGH (hard-linked STIX) |
| **Threat Actor Attribution** | APT29 / NOBELIUM / SVR Russia |
| **Score Factors** | Evidence destruction: +30 · 7-pass overwrite: +20 · Nation-state: +20 · Timing indicates actor awareness: +12 |
