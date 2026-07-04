# SCN-APT29-001: SUNBURST Backdoor DLL Detected in SolarWinds Orion Server

## Description

EDR detected the hash of `SolarWinds.Orion.Core.BusinessLayer.dll` matching a known SUNBURST backdoor IOC — a trojanized DLL injected into the SolarWinds Orion update package by APT29/NOBELIUM (SVR Russia). The file carries a valid SolarWinds digital signature, which allowed bypass of all application whitelisting controls. The presence of this hash is hard evidence of compromise by a nation-state actor. Attribution: APT29 / NOBELIUM / SVR Russia, confidence 100%.

---

## Phase 1 — Detection | T+0

### Inject

| Field | Value |
|-------|-------|
| Alert Source | EDR — Hash Match |
| IOC Type | file_hash (MD5) |
| IOC Value | `b91ce2fa41029f6955bff20079468448` |
| Filename | `SolarWinds.Orion.Core.BusinessLayer.dll` |
| File Path | `C:\Program Files (x86)\SolarWinds\Orion\` |
| File Type | DLL — .NET Assembly (C#) |
| Digital Signature | SolarWinds (valid — abused) |
| Detection | IOC Feed match — APT29/SUNBURST |
| Severity | CRITICAL |

### Expected Actions — System

- [x] EDR generates alert — hash match against known APT29 IOC feed
- [x] EDR blocks the hash on the local endpoint protection platform
- [x] Automatic P1 incident ticket created in ITSM (e.g., ServiceNow)
- [x] EDR agent attempts to quarantine the file — quarantine blocked because file is in active use by SolarWinds process
- [x] EDR sends alert to SIEM via syslog/API integration
- [x] SIEM receives raw event and queues it for correlation rules

### Expected Actions — Human

- [x] SOC analyst acknowledges the P1 alert within defined SLA (≤5 minutes for CRITICAL)
- [x] Analyst opens the EDR console and reviews the full alert details: file path, hash, process name, user context
- [x] Analyst confirms the file path is the expected SolarWinds Orion installation directory
- [x] Analyst cross-checks the MD5 hash against a second independent threat intel source (e.g., VirusTotal, CISA AA20-352A IOC list)
- [x] Analyst confirms the SHA-256 hash also matches: `ce77d116a074dab7a22a0fd4f2c1ab475f16eec42e1ded3c0b0aa8211fe858d6`
- [x] Analyst checks when the file was first written to disk — confirms installation date
- [x] Analyst checks if the DLL is currently loaded in memory by the SolarWinds process
- [x] Analyst notifies SOC Lead — escalation to P1 war room protocol

---

## Phase 2 — Alert | T+5min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | SIEM Correlation Rule |
| Rule Name | `APT29_NOBELIUM_SUNBURST_IOC_MATCH` |
| Correlated IOCs | MD5 `b91ce2fa...` + SHA-256 `ce77d116...` |
| Threat Actor | APT29 / NOBELIUM / SVR Russia |
| Campaign | SolarWinds Compromise (MITRE C0024) |
| Malware | SUNBURST (Solorigate) |
| Attribution Confidence | 100% — Hard-linked STIX |
| MITRE Techniques | T1195.002 · T1553.002 · T1562.001 · T1027 |

### Expected Actions — System

- [x] SIEM correlation rule fires — both MD5 and SHA-256 match APT29/NOBELIUM threat feed
- [x] SIEM enriches the alert with threat actor context (APT29, NOBELIUM, SVR Russia)
- [x] SIEM enriches with MITRE ATT&CK technique tags: T1195.002, T1553.002
- [x] SIEM sends high-priority notification to SOC dashboard and email distribution list
- [x] SIEM triggers automated DNS blocking for `*.avsvmcloud.com` via firewall API integration
- [x] SIEM creates a case with all correlated events attached

### Expected Actions — Human

- [x] SOC analyst reviews the enriched SIEM alert and confirms threat actor attribution: APT29 / NOBELIUM / SVR Russia
- [x] Analyst reads the MITRE ATT&CK campaign C0024 page to understand the full attack chain
- [x] Analyst confirms the DNS block for `*.avsvmcloud.com` was applied — checks firewall policy
- [x] Analyst opens CISA Emergency Directive 21-01 to verify mandatory response requirements
- [x] Analyst identifies the affected host: `SRV-ORION-01` and documents hostname, IP, OS version in the incident case
- [x] Analyst checks asset management system — confirms SRV-ORION-01 is a production SolarWinds Orion server
- [x] Analyst assigns the incident to Tier 2 / Threat Response team
- [x] SOC Lead is briefed — activates IR plan for nation-state incident

---

## Phase 3 — Triage | T+10min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | Analyst Review |
| Host | `SRV-ORION-01` (SolarWinds Orion server) |
| Orion Version | `2020.2.0` — AFFECTED range: 2019.4–2020.2.1 |
| DLL Present | `SolarWinds.Orion.Core.BusinessLayer.dll` ✅ |
| DLL Signed | Yes — SolarWinds certificate (serial: `0f:e9:73:75:20:22:a6:06:ad:f2:a3:6e:34:5d:c0:ed`) |
| Process | `SolarWinds.BusinessLayerHost.exe` — running |
| First Seen | 2024-04-22 (14 days ago — dormancy period) |

### Expected Actions — Human

- [x] Analyst logs into SRV-ORION-01 (read-only / forensic mode) and navigates to the SolarWinds Orion installation directory
- [x] Analyst verifies the Orion version: `2020.2.0` — confirms it falls in the affected range (2019.4 through 2020.2.1 HF 1)
- [x] Analyst checks the file creation timestamp of the DLL — records the exact date and time for timeline documentation
- [x] Analyst runs `Get-AuthenticodeSignature` on the DLL — confirms the certificate is issued to SolarWinds Corporation and is currently valid (not yet revoked)
- [x] Analyst checks if `SolarWinds.BusinessLayerHost.exe` is currently running — confirms process is active
- [x] Analyst records the PID of `SolarWinds.BusinessLayerHost.exe` for memory dump preparation
- [x] Analyst checks Task Manager / Process Explorer for child processes spawned by `SolarWinds.BusinessLayerHost.exe`
- [x] Analyst checks the Windows Services list — identifies `SolarWinds Orion Module Loader` service and its start type
- [x] Analyst checks Event Viewer for any errors or warnings logged by the SolarWinds service in the past 14 days
- [x] Analyst checks whether any other hosts in the environment also have Orion version 2020.2.0 installed — queries asset database
- [x] Analyst documents all findings in the incident case log with timestamps
- [x] Analyst confirms with SOC Lead: triage complete, proceeding to C2 investigation

---

## Phase 4 — C2 Investigation | T+30min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | DNS Logs |
| Queried Domain | `r8swhqn7yz0a8.appsync-api.us-east-2.avsvmcloud.com` |
| Parent Domain | `avsvmcloud.com` — SUNBURST DGA C2 (sinkholed) |
| Source Host | `SRV-ORION-01` (10.10.5.22) |
| First Query | 2024-04-22 03:14:22 UTC |
| Last Query | 2024-05-06 03:14:22 UTC |
| Total Queries | 847 (approximately every 12 hours) |
| CNAME Response | `sinkhole.microsoft.com` — sinkholed December 2020 |
| Follow-on Domains | `freescanonline.com`, `deftsecurity.com` |

### Expected Actions — Human

- [x] Analyst queries DNS logs for all queries from `SRV-ORION-01` to `*.avsvmcloud.com` — confirms 847 queries over 14 days
- [x] Analyst identifies the first query timestamp: 2024-04-22 03:14:22 UTC — this marks the start of SUNBURST C2 beaconing
- [x] Analyst verifies the query interval: approximately every 12 hours — consistent with SUNBURST's known beaconing schedule
- [x] Analyst decodes the DGA subdomain `r8swhqn7yz0a8` — notes it encodes victim environment information (hostname, domain) as per SUNBURST's known DGA algorithm
- [x] Analyst checks the DNS CNAME response — confirms `sinkhole.microsoft.com` — C2 was sinkholed and actor did not receive active callbacks
- [x] Analyst checks DNS logs for queries to `freescanonline.com` and `deftsecurity.com` — second-stage C2 domains used when DGA succeeds
- [x] Analyst checks firewall egress logs for any outbound connections to `13.59.205.66` or `54.193.127.66` — known APT29 second-stage C2 IPs
- [x] Analyst blocks all C2 domains and IPs on the DNS resolver and perimeter firewall: `avsvmcloud.com`, `freescanonline.com`, `deftsecurity.com`, `13.59.205.66`, `54.193.127.66`
- [x] Analyst checks if any other internal host made DNS queries to `*.avsvmcloud.com` — fleet-wide DNS log review
- [x] Analyst documents the full C2 timeline: first beacon, last beacon, total count, domain structure
- [x] Analyst checks whether the sinkhole response prevented second-stage activation — reviews if CNAME responses were always to sinkhole
- [x] Analyst prepares C2 IOC list for sharing with IT Security team for broader blocking

---

## Phase 5 — Second-Stage Hunt | T+45min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | Filesystem Scan |
| File Found | `gracious_truth.jpg` — TEARDROP indicator |
| File Path | `C:\Windows\SysWOW64\gracious_truth.jpg` |
| File Header | Fake JPG (actual: XOR-encoded Cobalt Strike BEACON) |
| Named Pipe | `583da945-62af-10e8-4902-a8f205c72b2e` — SUNBURST mutex detected |
| Service | `SolarWinds Orion Module Loader` — suspicious start type |

### Expected Actions — Human

- [x] Analyst searches `C:\Windows\SysWOW64\` for `gracious_truth.jpg` — confirms file exists
- [x] Analyst checks the file header of `gracious_truth.jpg` — uses hex editor to inspect first bytes — confirms fake JPG header (starts with `FF D8 FF` but content is not valid JPEG)
- [x] Analyst hashes `gracious_truth.jpg` and cross-checks hash against APT29 IOC feed — confirms TEARDROP indicator
- [x] Analyst checks creation timestamp of `gracious_truth.jpg` — records date for timeline (should be close to first SUNBURST DNS beacon)
- [x] Analyst lists all named pipes on `SRV-ORION-01` using Sysinternals Handle or `[System.IO.Directory]::GetFiles("\\.\pipe\")` — finds `583da945-62af-10e8-4902-a8f205c72b2e`
- [x] Analyst confirms the named pipe `583da945-62af-10e8-4902-a8f205c72b2e` is open and held by `SolarWinds.BusinessLayerHost.exe` — this is the SUNBURST single-instance guard mutex
- [x] Analyst takes a full memory dump of `SolarWinds.BusinessLayerHost.exe` using ProcDump or WinPmem before any remediation
- [x] Analyst checks registry key `HKU\SOFTWARE\Microsoft\CTF` — TEARDROP checks this key before executing; confirms key exists
- [x] Analyst checks for Cobalt Strike BEACON in memory using a BEACON scanner (e.g., BeaconHunter, pe-sieve) against the memory dump
- [x] Analyst checks for any active outbound connections from `SolarWinds.BusinessLayerHost.exe` to external IPs
- [x] Analyst checks Windows Event Log for any suspicious PowerShell or cmd.exe execution originating from the SolarWinds process lineage
- [x] Analyst confirms to SOC Lead: second-stage TEARDROP confirmed — BEACON likely loaded in memory — escalation required

---

## Phase 6 — Containment & Escalation | T+60min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | SOC Lead Review |
| Confirmed | SUNBURST + TEARDROP + Cobalt Strike BEACON |
| Attribution | APT29 / NOBELIUM / SVR Russia (100%) |
| Scope | SolarWinds Orion server — rest of network TBD |
| Cloud Risk | Azure AD / Office 365 — Golden SAML risk (T1606.002) |
| Evidence | DNS logs, DLL hash, gracious_truth.jpg, mutex, memory dump |

### Expected Actions — Human

- [x] Analyst isolates `SRV-ORION-01` from the network — disconnects NIC or applies firewall block rule to all traffic from/to the host
- [x] Analyst confirms isolation — verifies no active network connections remain from the host
- [x] Analyst blocks C2 IPs at the perimeter firewall: `13.59.205.66`, `54.193.127.66`
- [x] Analyst blocks C2 domains at the DNS resolver: `avsvmcloud.com`, `freescanonline.com`, `deftsecurity.com`
- [x] Analyst preserves all forensic evidence before any reimaging: memory dump, disk image, DNS logs, firewall logs, EDR telemetry
- [x] Analyst checks Azure AD audit logs for unauthorized Service Principals created in the past 14 days — potential cloud backdoor (T1098.001)
- [x] Analyst reviews AD FS token-signing certificate — checks if it has been exported or accessed recently — Golden SAML risk (T1606.002)
- [x] Analyst checks Domain Controller security event logs for Event ID 4662 — potential DCSync activity (T1003.006)
- [x] Analyst checks Exchange audit logs for any unauthorized mailbox export requests (T1114.002)
- [x] Analyst enumerates all other hosts with SolarWinds Orion 2020.2.0 installed — each is a potential SUNBURST host
- [x] SOC Lead escalates to CISO — nation-state breach by APT29/SVR confirmed
- [x] CISO initiates external Incident Response retainer — engage forensic IR firm
- [x] Legal and Privacy team notified — assess GDPR / regulatory notification obligations
- [x] If US Federal agency: CISA notified per Emergency Directive 21-01 within required timeframe

---

## References

- [MITRE T1195.002 — Supply Chain Compromise](https://attack.mitre.org/techniques/T1195/002/)
- [MITRE ATT&CK Campaign C0024 — SolarWinds Compromise](https://attack.mitre.org/campaigns/C0024/)
- [FireEye/Mandiant SUNBURST Disclosure](https://cloud.google.com/blog/topics/threat-intelligence/evasive-attacker-leverages-solarwinds-supply-chain-compromises-with-sunburst-backdoor)
- [CISA Emergency Directive 21-01](https://www.cisa.gov/emergency-directive-21-01)
- [FireEye Public IOCs — sunburst_countermeasures](https://github.com/mandiant/sunburst_countermeasures)
- Source Bundle: `apt29-solarwinds-stix-bundle.json` — indicators aa116f76, 31b9b682, b9a8c7d6, a1b2c3d4

> **Provenance:** Hash IOCs, malware names, TTPs, C2 domains/IPs, mutex, gracious_truth.jpg, DGA pattern, actor attribution → ✅ APT29 STIX Bundle | Phase structure, inject table format, simulated host/IP values, timeline narrative → 🤖 LLM (based on bundle data)

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
| **Score Factors** | Nation-state actor: +30 · Supply chain vector: +25 · Confirmed IOC 100%: +20 · Active C2 + second-stage: +20 |
