# SCN-APT29-004: TEARDROP Dropper File Detected — gracious_truth.jpg in SysWOW64

## Description

A file named `gracious_truth.jpg` was detected in `C:\Windows\SysWOW64\` by FIM. Despite its JPG extension, the file has a fake image header and contains a XOR-encoded Cobalt Strike BEACON payload. This is the TEARDROP dropper — a memory-only second-stage component deployed by APT29 in targeted victim environments after SUNBURST initial access. TEARDROP reads this file, decodes the payload using a custom rolling XOR algorithm, and manually loads Cobalt Strike BEACON into memory without writing any additional files to disk. Presence of this file confirms second-stage activity — the victim was selected for follow-on exploitation. Attribution: APT29 / NOBELIUM / SVR Russia, confidence 95%.

---

## Phase 1 — Detection | T+0

### Inject

| Field | Value |
|-------|-------|
| Alert Source | FIM (File Integrity Monitoring) |
| Alert Type | New file created in protected system directory |
| File Name | `gracious_truth.jpg` |
| File Path | `C:\Windows\SysWOW64\gracious_truth.jpg` |
| File Size | 218 KB |
| File Header | `FF D8 FF` overwritten — fake JPG header |
| Created By | `SolarWinds.BusinessLayerHost.exe` |
| Timestamp | 2024-05-01 02:47:33 UTC |
| Severity | CRITICAL |

### Expected Actions — System

- [x] FIM generates alert: new file created in `C:\Windows\SysWOW64\` by a non-OS process
- [x] EDR detects `SolarWinds.BusinessLayerHost.exe` creating a file in a protected system directory — flags as suspicious
- [x] EDR hashes the new file: MD5, SHA-1, SHA-256 — submits hashes to threat intel feed
- [x] SIEM ingests the FIM alert and correlates with the process name
- [x] Automatic P1 incident ticket created in ITSM
- [x] SIEM notifies SOC dashboard: file creation in system directory by application process

### Expected Actions — Human

- [x] SOC analyst acknowledges P1 alert and opens the FIM event details
- [x] Analyst confirms the file path: `C:\Windows\SysWOW64\gracious_truth.jpg` — a JPG file in a system DLL directory is inherently suspicious
- [x] Analyst checks the process that created the file: `SolarWinds.BusinessLayerHost.exe` — notes this is a SolarWinds process that should never create JPG files
- [x] Analyst hashes the file and searches the hash against APT29/SUNBURST IOC feeds — confirms TEARDROP indicator
- [x] Analyst checks the file creation timestamp against the SUNBURST DNS beaconing timeline — determines relationship
- [x] Analyst checks file size (218 KB) — notes it matches known TEARDROP dropper size range
- [x] Analyst notifies SOC Lead — escalates to P1 nation-state incident protocol
- [x] Analyst documents file details in the incident case: path, size, hash, creation timestamp, creating process

---

## Phase 2 — Alert | T+3min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | SIEM Correlation Rule |
| Rule Name | `APT29_TEARDROP_FILE_INDICATOR` |
| Matched IOC | `gracious_truth.jpg` in `C:\Windows\SysWOW64\` |
| Threat Actor | APT29 / NOBELIUM / SVR Russia |
| Malware | TEARDROP — second-stage dropper |
| Linked Malware | Cobalt Strike BEACON (payload inside file) |
| MITRE Technique | T1036.005 — Masquerading |
| Attribution Confidence | 95% — Hard-linked STIX |
| Parent Process | `SolarWinds.BusinessLayerHost.exe` |

### Expected Actions — System

- [x] SIEM correlation fires alert: `gracious_truth.jpg` in SysWOW64 matches APT29/TEARDROP IOC feed
- [x] SIEM enriches with threat actor: APT29 / NOBELIUM / SVR Russia, malware: TEARDROP
- [x] SIEM enriches with MITRE technique: T1036.005 — Masquerading (fake JPG extension)
- [x] SIEM checks for correlated events: any SUNBURST hash or DNS C2 matches on same host
- [x] SIEM sends critical alert to SOC team and opens incident case
- [x] EDR attempts to block the parent process hash `b91ce2fa41029f6955bff20079468448` on all agents — confirms block applied

### Expected Actions — Human

- [x] Analyst reviews the enriched SIEM alert — confirms TEARDROP attribution and APT29 linkage
- [x] Analyst searches for correlated SUNBURST activity on the same host: checks for DLL hash match and DNS queries to `*.avsvmcloud.com`
- [x] Analyst confirms: SUNBURST DLL `b91ce2fa41029f6955bff20079468448` also present on the same host — full infection chain confirmed
- [x] Analyst checks whether this host was previously flagged for SUNBURST — if so, links the incidents
- [x] Analyst checks the file's true MIME type using a hex editor: first bytes `FF D8 FF` appear to be JPG but remaining content is not valid JPEG structure
- [x] Analyst checks the registry key `HKU\SOFTWARE\Microsoft\CTF` — TEARDROP checks this key before executing; confirms presence
- [x] Analyst reviews what other files `SolarWinds.BusinessLayerHost.exe` has written to disk in the past 14 days
- [x] Analyst documents the infection chain: SUNBURST (supply chain) → TEARDROP (dropper) → BEACON (in-memory)

---

## Phase 3 — Triage | T+10min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | Analyst Review — File Analysis |
| File Header Check | First 3 bytes: `FF D8 FF` (JPG) — content after offset 8 is NOT valid JPEG |
| True Content | XOR-encoded binary — custom rolling XOR (TEARDROP decode routine) |
| Registry Check | `HKU\SOFTWARE\Microsoft\CTF` — EXISTS on this host |
| SUNBURST DLL | `b91ce2fa41029f6955bff20079468448` — CONFIRMED on same host |
| Named Pipe | `583da945-62af-10e8-4902-a8f205c72b2e` — SUNBURST mutex found |

### Expected Actions — Human

- [x] Analyst opens `gracious_truth.jpg` in a hex editor — confirms fake JPG header: first bytes match JPG signature but remaining content is binary data
- [x] Analyst counts file structure: after the first 8 bytes, the content switches to what appears to be compressed binary — confirms XOR encoding
- [x] Analyst checks registry key `HKU\SOFTWARE\Microsoft\CTF` — confirms the key exists (TEARDROP pre-condition is met)
- [x] Analyst confirms SUNBURST DLL hash on same host: `b91ce2fa41029f6955bff20079468448` — infection chain: SUNBURST deployed TEARDROP
- [x] Analyst checks for named pipe `583da945-62af-10e8-4902-a8f205c72b2e` — confirms SUNBURST mutex is active
- [x] Analyst checks if TEARDROP has already executed — reviews process memory for any DLL loaded from a JPG-origin memory region
- [x] Analyst checks EDR memory scan results — determines if Cobalt Strike BEACON is already loaded in-memory
- [x] Analyst verifies that `gracious_truth.jpg` file is not currently open by any process (indicating TEARDROP may not have executed yet)
- [x] Analyst records all findings for forensic chain of custody
- [x] Analyst confirms with SOC Lead: TEARDROP present, BEACON deployment likely imminent or already active

---

## Phase 4 — Memory Investigation | T+25min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | EDR Memory Scan |
| Finding | Cobalt Strike BEACON loaded in-memory in `SolarWinds.BusinessLayerHost.exe` |
| C2 Connection | Outbound HTTPS to `13.59.205.66:443` detected |
| Pipe | SMB named pipe — custom variant for lateral movement |
| Dwell Time | TEARDROP file created 5 days ago — BEACON active since then |

### Expected Actions — Human

- [x] Analyst runs a memory scan on `SolarWinds.BusinessLayerHost.exe` using pe-sieve or BeaconHunter — confirms Cobalt Strike BEACON loaded in memory
- [x] Analyst takes a full memory dump of `SolarWinds.BusinessLayerHost.exe` using ProcDump before any remediation
- [x] Analyst extracts the Cobalt Strike BEACON configuration from the memory dump: C2 server, sleep interval, jitter, user-agent string
- [x] Analyst confirms BEACON C2 IP from extracted config: `13.59.205.66` — cross-checks against APT29 IOC feed
- [x] Analyst checks firewall logs for all outbound connections to `13.59.205.66:443` — confirms HTTPS beaconing
- [x] Analyst calculates BEACON dwell time: TEARDROP file created 5 days ago — determines what the actor could have done in 5 days
- [x] Analyst checks EDR process logs for any commands executed via BEACON in the past 5 days: AdFind, net.exe, whoami, etc.
- [x] Analyst checks for SMB named pipe connections from `SolarWinds.BusinessLayerHost.exe` to other internal hosts — lateral movement indicators
- [x] Analyst checks for AdFind (`AdFind.exe`) execution in the past 5 days — AD enumeration (T1087.002)
- [x] Analyst checks Domain Controller security event logs for authentication events from SRV-ORION-01 in the past 5 days
- [x] Analyst checks if BEACON has moved to DC-01 or EXCH-01 — reviews EDR telemetry on those hosts
- [x] Analyst documents BEACON configuration details: C2 IP, sleep/jitter values, staging paths — for threat intel sharing

---

## Phase 5 — Containment | T+45min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | SOC Lead — Scope Assessment |
| Lateral Movement | AdFind logs found — DC enumerated 3 days ago |
| Credential Risk | DCSync likely attempted — check Domain Controller event logs |
| Cloud Risk | Azure AD Service Principals — check for unauthorized entries |
| Other Hosts | Check all hosts for BEACON C2 connection to `13.59.205.66` |

### Expected Actions — Human

- [x] Analyst isolates SRV-ORION-01 immediately — disconnects from network via EDR remote isolation or firewall rule
- [x] Analyst checks all hosts for BEACON C2 connections to `13.59.205.66` and `54.193.127.66` — EDR fleet-wide hunt
- [x] Analyst blocks `13.59.205.66` and `54.193.127.66` at all perimeter firewalls
- [x] Analyst checks Domain Controller security event log for Event ID 4662 — DCSync activity (T1003.006) from SRV-ORION-01
- [x] Analyst checks Azure AD audit logs for unauthorized Service Principals created in the past 5 days (T1098.001)
- [x] Analyst reviews AD FS token-signing certificate access logs — checks if it was exported (Golden SAML risk, T1606.002)
- [x] Analyst checks Exchange audit logs for any mailbox export requests from SRV-ORION-01 or any BEACON-compromised host
- [x] Analyst verifies whether AdFind was used to enumerate the domain — checks for AdFind.exe in EDR process logs
- [x] Analyst preserves all forensic artifacts: memory dump, TEARDROP file, BEACON config, EDR telemetry
- [x] SOC Lead escalates to CISO — nation-state actor active in environment for 5+ days
- [x] CISO activates external IR retainer — APT29 nation-state incident requires specialized response
- [x] Legal team notified — potential data exposure during 5-day BEACON dwell period

---

## References

- [MITRE T1036.005 — Match Legitimate Name or Location](https://attack.mitre.org/techniques/T1036/005/)
- [MITRE S0560 — TEARDROP](https://attack.mitre.org/software/S0560/)
- [MITRE S0154 — Cobalt Strike](https://attack.mitre.org/software/S0154/)
- [MITRE ATT&CK Campaign C0024](https://attack.mitre.org/campaigns/C0024/)
- [FireEye SUNBURST Analysis](https://cloud.google.com/blog/topics/threat-intelligence/evasive-attacker-leverages-solarwinds-supply-chain-compromises-with-sunburst-backdoor)
- Source Bundle: `apt29-solarwinds-stix-bundle.json` — indicator b9a8c7d6, malware efed2e55, relationship r029

> **Provenance:** Filename, path, fake JPG header, XOR decode, registry check, actor attribution, TTPs → ✅ APT29 STIX Bundle | Phase structure, simulated timestamps/sizes, BEACON memory details, timeline → 🤖 LLM (based on bundle data)

---

## Threat Scoring

| Metric | Value |
|--------|-------|
| **Threat Score** | 96 / 100 |
| **Severity** | CRITICAL |
| **Incident Priority** | P1 — Critical |
| **Response SLA** | Immediate |
| **Confidence** | 95% — HIGH (hard-linked STIX) |
| **Threat Actor Attribution** | APT29 / NOBELIUM / SVR Russia |
| **Score Factors** | Second-stage active payload: +35 · BEACON in memory: +30 · Nation-state: +20 · 5-day dwell time: +11 |
