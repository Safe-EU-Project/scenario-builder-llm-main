# SCN-ENERGY-001: SCADA/ICS Attack on European Power Grid Substation

## Sector
energy

## Description

A regional electricity distribution operator in Eastern Europe detected anomalous commands being issued to substation SCADA systems via a compromised engineering workstation. The attack mirrors INDUSTROYER/CrashOverride (2016, Ukraine) and INDUSTROYER2 (2022, Ukraine) — malware designed to directly communicate with IEC 60870-5-104 and IEC 61850 protocols to open circuit breakers and disrupt power supply. Approximately 180,000 customers experienced an outage lasting 3.5 hours before manual switching restored service.

Attack Type: ICS/SCADA destructive attack targeting power grid  
MITRE ATT&CK ICS: T0855 (Unauthorized Command Message), T0816 (Device Restart/Shutdown), T0831 (Manipulation of Control), T0826 (Loss of Availability)  
Impact: 180,000 customers without power, 3.5 hours  
Attribution: Sandworm / APT44 (GRU Unit 74455, Russia), confidence HIGH

---

## Phase 1 — Detection | T+0

### Inject

| Field | Value |
|-------|-------|
| Alert Source | ICS/SCADA Anomaly Detection (Claroty / Dragos sensor) |
| Alert Type | Unauthorized IEC 60870-5-104 ASDU commands to RTUs |
| Source Host | `ENG-WS-14` (Engineering workstation — OT network segment) |
| Target Devices | 9 Remote Terminal Units (RTUs) across 3 substations |
| Commands Issued | Circuit breaker OPEN commands (IEC 104 Type ID 46) |
| Substation IDs | `SUB-EAST-07`, `SUB-EAST-09`, `SUB-NORTH-02` |
| Operator Present | No — engineering workstation is unattended |
| Severity | CRITICAL |

### Expected Actions — System

- Claroty/Dragos ICS sensor detects anomalous IEC 104 command traffic — fires alert
- SIEM correlation rule fires: `ICS_UNAUTHORIZED_COMMAND_ENGINEERING_WS`
- OT Security Operations Center (OT-SOC) receives P1 alert
- Automatic network ACL applied — blocks `ENG-WS-14` from further communication with SCADA server (if automated response is configured)
- SCADA historian records all commands with timestamps for forensic use

### Expected Actions — Human

- OT-SOC analyst acknowledges P1 alert immediately
- Analyst verifies with the Control Room: are operators expecting any maintenance commands at this time? — Answer: NO
- Analyst calls the substation site manager for `SUB-EAST-07` — confirms circuit breakers tripped unexpectedly
- Analyst immediately requests network isolation of `ENG-WS-14` from the OT network
- Analyst notifies CISO and OT Security Lead — activates ICS Incident Response Plan
- Analyst contacts field engineers to prepare for manual restoration of circuit breakers

---

## Phase 2 — OT Forensics — Engineering Workstation | T+15min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | Endpoint Forensics — ENG-WS-14 |
| Malware Found | `enel.exe` — INDUSTROYER2 variant (IEC 104 attack module) |
| File Hash | `d69665f56ddef7ad4e71971f06432d2a` |
| Persistence | Scheduled Task `\Microsoft\Windows\WDI\ResolutionHost` |
| Wiper Component | `caddywiper.exe` — data wiper for post-attack cleanup |
| Initial Access Vector | Spear-phishing attachment → VBA macro → stager |
| Attacker Dwell Time | 6 weeks (initial compromise to attack day) |
| Lateral Movement | Via domain admin credentials stolen from IT network |

### Expected Actions — Human

- OT forensics analyst acquires a forensic image of `ENG-WS-14` before any cleanup
- Analyst identifies `enel.exe` — cross-checks hash against CERT-UA and CISA advisories — confirms INDUSTROYER2 variant
- Analyst identifies `caddywiper.exe` — notes the wiper was not yet triggered (attack interrupted before cleanup phase)
- Analyst disables the malicious scheduled task to prevent re-execution after reboot
- Analyst checks which other hosts `ENG-WS-14` communicated with over the past 6 weeks — identifies lateral movement paths
- Analyst checks for stolen credentials — identifies domain admin account `svc_scada_maint` used for lateral movement from IT to OT
- Analyst resets `svc_scada_maint` password and revokes all active sessions
- Analyst scans all other OT engineering workstations (`ENG-WS-01` through `ENG-WS-20`) for `enel.exe` and related IOCs
- Analyst identifies initial access vector — spear-phishing email sent 6 weeks ago to engineering team

---

## Phase 3 — Operational Impact Assessment | T+30min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | Control Room — Manual Assessment |
| Substations Affected | `SUB-EAST-07`: 12/18 circuit breakers tripped — 47,000 customers offline |
| | `SUB-EAST-09`: 8/12 circuit breakers tripped — 89,000 customers offline |
| | `SUB-NORTH-02`: 3/6 circuit breakers tripped — 44,000 customers offline |
| Total Customers Offline | 180,000 |
| Critical Infrastructure | 2 hospitals, 1 water treatment plant on affected circuits |
| Backup Generator Status | Both hospitals on emergency backup — 72h fuel reserve |
| Manual Switching | Possible — field engineers dispatched |
| Estimated Restoration | 2-4 hours via manual switching |

### Expected Actions — Human

- Control Room Director activates the Grid Emergency Response Plan
- Field engineers dispatched to all 3 substations for manual circuit breaker restoration
- Operations team notifies the national grid operator (TSO) of the abnormal grid state
- OT-SOC analyst ensures all RTUs are in MANUAL mode — prevents further remote commands
- Communications officer notifies the national emergency response authority (Civil Protection)
- Hospital liaison officer confirms both hospitals are on backup generators — arranges priority power restoration
- Water utility informed — assesses pump station backup power status
- OT-SOC analyst flags all remaining SCADA commands as requiring dual-operator authorization until the incident is resolved

---

## Phase 4 — Containment & Network Segmentation | T+60min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | Network Analysis — OT/IT Boundary |
| Pivot Path Found | IT network → `ENG-WS-14` (OT) via IT-OT jump server `JUMP-OT-01` |
| Jump Server Compromise | `JUMP-OT-01` fully compromised — attacker had domain admin |
| C2 Channel | HTTPS beacon to `update.microsoft-telemetry.net` (DGA) |
| C2 Active Since | 6 weeks |
| Data Exfiltrated | SCADA network diagrams, RTU configuration files, grid topology maps |

### Expected Actions — Human

- Analyst completely segments the OT network from the IT network — disables all IT-OT firewall rules
- Analyst isolates and forensically images `JUMP-OT-01`
- Analyst blocks C2 domain `update.microsoft-telemetry.net` at all DNS resolvers and perimeter firewalls
- Analyst conducts threat hunt across the entire IT domain for the same C2 beacon
- Analyst assesses the exfiltrated data: SCADA network diagrams and RTU configurations are classified — notifies national CSIRT
- Analyst reviews all user accounts that authenticated to `JUMP-OT-01` over the past 6 weeks — identifies compromised accounts
- Analyst resets all domain admin credentials across the IT domain
- CISO notifies the national energy regulator and national CSIRT per mandatory critical infrastructure incident reporting obligations
- Analyst contacts CERT-EU and ENISA given cross-border potential impact (interconnected European grid)

---

## Phase 5 — Recovery & Regulatory Reporting | T+4h

### Inject

| Field | Value |
|-------|-------|
| Power Restoration | 3.5 hours — all 180,000 customers restored via manual switching |
| RTU Status | All 27 affected RTUs verified — no firmware modification detected |
| SCADA Server | Checked — no malicious payload found on SCADA server itself |
| Regulatory Deadline | NIS2 Article 23: significant incident report to national authority within 24h |
| Law Enforcement | National cybercrime unit and military cyber command notified |

### Expected Actions — Human

- OT-SOC verifies all RTUs are functioning correctly before returning to REMOTE mode
- SCADA administrator performs integrity check on all RTU firmware — hashes compared against vendor-signed baselines
- Legal and Compliance team prepares NIS2 Article 23 significant incident notification — submits within 24 hours
- CISO prepares a formal incident report for the national energy regulator
- Communications team issues a public statement acknowledging the outage — attributes to "malicious cyberattack" without technical details
- Security team begins long-term remediation: network redesign, one-way data diodes for IT-OT transfer, hardware MFA for OT access
- IT Security team engages ICS security vendor for a full OT security assessment
- Company coordinates with national CSIRT to share IOC package with other European energy operators

---

## References

- INDUSTROYER/CrashOverride analysis — ESET (2017)
- INDUSTROYER2 analysis — ESET / CERT-UA (2022)
- Sandworm / APT44 attribution — Mandiant (2022)
- CISA Advisory AA22-110A — Sandworm ICS attack tools
- IEC 60870-5-104 protocol specification
- NIS2 Directive 2022/2555 — Article 23 incident reporting
- ENISA Guidelines for ICS/SCADA Security

## Threat Scoring

| Metric | Value |
|--------|-------|
| **Threat Score** | 98 / 100 |
| **Severity** | CRITICAL |
| **Incident Priority** | P1 — Critical |
| **Operational Impact** | 180,000 customers, 3.5h outage |
| **Response SLA** | Immediate |
| **Confidence** | HIGH — confirmed ICS attack pattern |
| **Sector** | Energy / Critical Infrastructure |
| **Threat Actor** | Sandworm / APT44 (GRU Unit 74455) |
