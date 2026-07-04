# SCN-APT29-011: 7-Zip Archiving + Data Staging for Exfiltration

## Description

EDR process logs and DLP alerts show 7-Zip (`7za.exe`) executing multiple archive creation commands on sensitive directories. APT29 / NOBELIUM used 7-Zip to compress and password-protect collected data before exfiltration via Cobalt Strike BEACON. This technique (T1560.001 — Archive Collected Data: Archive via Utility) allows large data volumes to be staged as small encrypted archives, bypassing file-size DLP rules and making inspection by network security tools impossible. The archive files were staged in `C:\Windows\Temp\cab_*.tmp` — a masqueraded path designed to look like Windows cabinet files. Attribution: APT29 / NOBELIUM / SVR Russia, confidence 88%.

---

## Phase 1 — Detection | T+0

### Inject

| Field | Value |
|-------|-------|
| Alert Source | EDR — Process Monitoring |
| Alert Type | 7-Zip creating password-protected archives in system temp folder |
| Command | `7za.exe a -p[redacted] C:\Windows\Temp\cab_0034.tmp \\SHARE\SensitiveData\ -r` |
| Process | `7za.exe` spawned by `cmd.exe` → parent: `SolarWinds.BusinessLayerHost.exe` |
| Archive Password | Encrypted — not retrievable from logs |
| Destination Path | `C:\Windows\Temp\cab_*.tmp` |
| Timestamp | 2024-05-09 04:02:11 UTC |
| Severity | HIGH |

### Expected Actions — System

- [ ] EDR alert — 7-Zip spawned by monitored suspicious parent process
- [ ] DLP alert — archive creation targeting sensitive share
- [ ] Log command line (masked password) and parent process chain

---

## Phase 2 — Alert | T+5min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | SIEM Correlation |
| Rule Name | `APT29_DATA_STAGING_7ZIP` |
| MITRE Technique | T1560.001 — Archive Collected Data: Archive via Utility |
| Archives Created | 7 archive files, total: 1.4 GB (compressed from ~3.8 GB source) |
| Source Data | Finance shared drive, Legal contracts folder, Security policy documents |
| Password | Set — content unreadable without actor's private password |
| Masquerade | `cab_*.tmp` naming mimics Windows temp cabinet file pattern (T1036.005) |

### Expected Actions — System

- [ ] SIEM alert — multiple password-protected archives of sensitive data
- [ ] Block `7za.exe` execution from SolarWinds process lineage
- [ ] Alert SOC: staging in progress — likely imminent exfiltration

---

## Phase 3 — Triage | T+15min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | Analyst Review — File System + Process |
| Archive Files | 7 files: `cab_0034.tmp` through `cab_0041.tmp` |
| File Sizes | 156 MB – 240 MB each |
| Data Sources | `\\FILESERVER\Finance\`, `\\FILESERVER\Legal\`, `\\FILESERVER\Security\` |
| Already Exfiltrated | Logs show `cab_0034.tmp` already transferred to `13.59.205.66` via BEACON |
| Remaining | `cab_0035.tmp` through `cab_0041.tmp` — staged but not yet exfiltrated |

### Expected Actions — Human

- [ ] Immediately isolate SRV-ORION-01 to prevent remaining 6 archives from exfil
- [ ] Confirm `cab_0034.tmp` already exfiltrated — classify as data breach
- [ ] Preserve remaining archives for forensics — do NOT delete yet
- [ ] Check what specific documents were in `cab_0034.tmp` (first archive = priority)
- [ ] Block C2 IP `13.59.205.66` at all egress points

---

## Phase 4 — Impact Assessment | T+30min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | File Server Access Logs |
| First Archive | `cab_0034.tmp` (~156 MB compressed from ~420 MB) — 1,240 financial files |
| Files Include | Q4 budget, contract values, bank account details for vendor payments |
| Second Archive | `cab_0035.tmp` — 380 legal contracts (NOT yet exfiltrated) |
| Actor Intent | Financial intelligence + leverage for future operations |

### Expected Actions — Human

- [ ] Identify exact files in `cab_0034.tmp` — cross-reference file server access logs
- [ ] Notify Finance Director: Q4 budget and vendor payment data confirmed compromised
- [ ] Legal review: contract data exposure — notify affected vendors if required
- [ ] Begin regulatory notification process — data breach confirmed

---

## Phase 5 — Hardening | T+90min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | SOC Lead — Prevention |
| Gap | 7-Zip was installed on server — should not be present on Orion servers |
| Gap 2 | Sensitive shares accessible from SolarWinds server — unnecessary access |
| Gap 3 | `cab_*.tmp` masquerade — DLP should flag encrypted archives in temp paths |

### Expected Actions — Human

- [ ] Remove 7-Zip and other compression utilities from all servers (except where required)
- [ ] Implement application allowlisting — restrict executable file types per server role
- [ ] Remove SolarWinds server from file share access — least privilege principle
- [ ] Add DLP rule: alert on password-protected archives created in `%TEMP%` paths
- [ ] Add SIEM rule: `7za.exe` or `7z.exe` spawned by non-admin parent process = critical alert

---

## References

- [MITRE T1560.001 — Archive via Utility](https://attack.mitre.org/techniques/T1560/001/)
- [MITRE ATT&CK Campaign C0024](https://attack.mitre.org/campaigns/C0024/)
- [MITRE T1036.005 — Masquerade: Match Legitimate Name](https://attack.mitre.org/techniques/T1036/005/)
- Source Bundle: `apt29-solarwinds-stix-bundle.json` — attack-pattern T1560.001, tool s0038 (7-Zip), relationship r020

> **Provenance:** 7-Zip archiving technique, staging + exfil chain, masquerade path, actor attribution → ✅ APT29 STIX Bundle | Specific paths, archive sizes, data types, share names, DLP gap analysis → 🤖 LLM (based on bundle data)

---

## Threat Scoring

| Metric | Value |
|--------|-------|
| **Threat Score** | 89 / 100 |
| **Severity** | HIGH — Data Exfiltration in Progress |
| **Incident Priority** | P1 — Critical |
| **Response SLA** | Immediate — Block Exfil Before Remaining Archives Transfer |
| **Confidence** | 88% — HIGH (hard-linked STIX) |
| **Threat Actor Attribution** | APT29 / NOBELIUM / SVR Russia |
| **Score Factors** | Active exfiltration: +35 · Financial data exposed: +25 · Nation-state: +20 · Masquerade evades DLP: +9 |
