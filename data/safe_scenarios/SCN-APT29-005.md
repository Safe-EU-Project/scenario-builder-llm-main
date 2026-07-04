# SCN-APT29-005: Outbound Connection to APT29 C2 Infrastructure

## Description

Firewall logs show outbound HTTPS connections from an internal host to `13.59.205.66` and `54.193.127.66` — confirmed APT29/NOBELIUM command and control IP addresses published by CISA in Alert AA20-352A. APT29 specifically used VPS providers with IP addresses matching the victim's country geolocation to evade detection. These IPs were used as second-stage C2 infrastructure after SUNBURST's initial DNS DGA check-in via `avsvmcloud.com`. Connection to these IPs indicates Cobalt Strike BEACON is active and communicating with the threat actor. Attribution: APT29 / NOBELIUM / SVR Russia, confidence 90%.

---

## Phase 1 — Detection | T+0

### Inject

| Field | Value |
|-------|-------|
| Alert Source | Firewall / Proxy Log |
| Alert Type | Outbound connection to known malicious IP |
| Destination IP | `13.59.205.66` |
| Destination Port | `443` (HTTPS) |
| Source Host | `10.10.5.22` (SRV-ORION-01) |
| Protocol | HTTPS — encrypted traffic |
| Bytes Sent | 4.2 MB over 3 days |
| First Connection | 2024-04-23 01:12:44 UTC |
| Threat Intel Match | APT29 / NOBELIUM C2 infrastructure (CISA AA20-352A) |
| Severity | CRITICAL |

### Expected Actions — System

- [x] Firewall generates alert: outbound connection to IP matching APT29 threat feed
- [x] SIEM ingests the firewall log event and correlates against threat intel feeds
- [x] SIEM fires alert: outbound connection to known APT29 C2 IP
- [x] Firewall applies automatic block rule for `13.59.205.66` — drops new connections
- [x] Automatic P1 incident ticket created in ITSM
- [x] SIEM sends high-priority notification to SOC team

### Expected Actions — Human

- [x] SOC analyst acknowledges P1 alert and opens the firewall log for the source host
- [x] Analyst identifies the source host: `10.10.5.22` — resolves to `SRV-ORION-01`
- [x] Analyst confirms the destination IP `13.59.205.66` against CISA AA20-352A IOC list — confirmed APT29 C2 IP
- [x] Analyst checks the total traffic volume: 4.2 MB outbound over 3 days — assesses potential data exfiltration
- [x] Analyst checks the first connection timestamp: 2024-04-23 01:12:44 UTC — determines how long the connection has been active
- [x] Analyst checks the connection pattern: periodic (beaconing) or continuous — identifies BEACON sleep/jitter behavior
- [x] Analyst checks for a second APT29 C2 IP: `54.193.127.66` — reviews firewall logs for connections to this IP from any host
- [x] Analyst notifies SOC Lead and escalates to P1 war room

---

## Phase 2 — Alert | T+2min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | SIEM Correlation |
| Rule Name | `APT29_C2_IP_EGRESS_CONNECTION` |
| Second IP Found | `54.193.127.66` — also connecting from same host |
| Connection Pattern | Periodic beaconing — every ~4 hours |
| Traffic Volume | 4.2 MB outbound, 1.1 MB inbound |
| Encryption | TLS 1.2 — Cobalt Strike BEACON default profile |
| DNS Correlation | Same host previously queried `avsvmcloud.com` (14 days ago) |
| Attribution | APT29 / NOBELIUM (confidence: 90%) |

### Expected Actions — System

- [x] SIEM correlates C2 IP connection with prior `avsvmcloud.com` DNS queries from the same host
- [x] SIEM enriches with attribution: APT29 / NOBELIUM, campaign C0024, MITRE T1071.001
- [x] SIEM identifies second C2 IP `54.193.127.66` — applies block rule for this IP as well
- [x] SIEM performs fleet-wide hunt: any other host connecting to `13.59.205.66` or `54.193.127.66`
- [x] SIEM opens incident case with all correlated events: firewall log, DNS correlation, threat intel match

### Expected Actions — Human

- [x] Analyst reviews the correlated SIEM alert — confirms same host that queried `avsvmcloud.com` is now connecting to second-stage C2 IPs
- [x] Analyst confirms: SUNBURST dormancy completed → DNS beaconing → C2 IP activation — full SUNBURST kill chain
- [x] Analyst checks the connection pattern: every ~4 hours — consistent with Cobalt Strike BEACON default sleep configuration
- [x] Analyst measures the traffic ratio: 4.2 MB out vs 1.1 MB in — outbound exceeds inbound, suggests data exfiltration possible
- [x] Analyst checks TLS certificate presented by `13.59.205.66` — notes self-signed cert typical of Cobalt Strike BEACON C2
- [x] Analyst verifies block rule is applied for both `13.59.205.66` and `54.193.127.66` on ALL egress firewall rules
- [x] Analyst reviews fleet-wide hunt results: identifies any other hosts connecting to either C2 IP
- [x] Analyst checks geolocation of both IPs: `13.59.205.66` → US-East region (AWS) — APT29 deliberately used US-based infrastructure to blend in

---

## Phase 3 — Triage | T+10min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | Analyst Review — Host Investigation |
| Source Host | `SRV-ORION-01` — SolarWinds Orion server |
| SUNBURST DLL | `b91ce2fa41029f6955bff20079468448` — CONFIRMED present |
| TEARDROP File | `gracious_truth.jpg` — CONFIRMED in SysWOW64 |
| Process Making Connection | `SolarWinds.BusinessLayerHost.exe` |
| Connection Start | 2024-04-23 — 1 day after SUNBURST beaconed via DNS |
| Geolocation of IPs | `13.59.205.66` → US-East (matches victim region — deliberate OpSec) |

### Expected Actions — Human

- [x] Analyst connects to SRV-ORION-01 in read-only forensic mode and checks which process is making connections to `13.59.205.66`
- [x] Analyst confirms: `SolarWinds.BusinessLayerHost.exe` is the process — consistent with BEACON loaded by TEARDROP
- [x] Analyst verifies SUNBURST DLL hash on host: `b91ce2fa41029f6955bff20079468448` — confirmed
- [x] Analyst verifies TEARDROP file: `gracious_truth.jpg` in `C:\Windows\SysWOW64\` — confirmed
- [x] Analyst checks the full infection timeline: SUNBURST installed (day 0) → DNS beaconing started (day 14) → C2 IP connection (day 15)
- [x] Analyst notes deliberate OpSec: APT29 used a US-East AWS IP to match victim's geographic region — less likely to trigger geo-based firewall rules
- [x] Analyst checks what data was transferred: 4.2 MB outbound — reviews if any staged archives or files were created before connections started
- [x] Analyst checks for a second BEACON callback channel: `54.193.127.66` — confirms connections to this backup C2 as well
- [x] Analyst documents full infection chain in the incident case: SUNBURST → TEARDROP → BEACON → C2 IPs
- [x] Analyst confirms with SOC Lead: active C2 channel — BEACON has been communicating with APT29 for 3 days

---

## Phase 4 — Lateral Movement Check | T+30min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | EDR + AD Logs |
| Finding | Cobalt Strike BEACON used SMB named pipe for internal movement |
| Hosts Reached | `DC-01` (Domain Controller), `EXCH-01` (Exchange server) |
| Method | Pass-the-Hash via NTLM relay from BEACON |
| Credentials Used | Different from initial remote access credentials (deliberate OpSec) |
| AdFind Execution | Detected on `SRV-ORION-01` — domain enumeration logged |

### Expected Actions — Human

- [x] Analyst checks EDR telemetry on SRV-ORION-01 for SMB connections to other internal hosts from the BEACON process
- [x] Analyst identifies hosts reached by BEACON: DC-01 and EXCH-01 — records timestamps of first lateral movement
- [x] Analyst checks EDR on DC-01 and EXCH-01 for any BEACON-related process activity
- [x] Analyst checks Domain Controller event logs for Pass-the-Hash indicators: Event ID 4624 (logon type 3) with NTLM from SRV-ORION-01
- [x] Analyst checks AdFind execution logs: reviews what AD enumeration was performed — users, groups, OUs, DCs listed
- [x] Analyst checks if different credentials were used for lateral movement versus initial access — reviews authentication logs
- [x] Analyst checks for DCSync activity on DC-01: Event ID 4662 with DS-Replication-Get-Changes-All GUID
- [x] Analyst checks for Exchange PowerShell remoting from SRV-ORION-01 to EXCH-01 — mailbox collection risk
- [x] Analyst checks for any Kerberos ticket requests (Event ID 4768/4769) from SRV-ORION-01 — Golden Ticket risk
- [x] Analyst prepares lateral movement scope map: which hosts were reached from SRV-ORION-01 via BEACON
- [x] Analyst resets the credentials used for lateral movement (different set from initial access)
- [x] Analyst documents all lateral movement findings in the incident case

---

## Phase 5 — Containment | T+60min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | SOC Lead — Full Scope |
| Hosts Affected | SRV-ORION-01, DC-01, EXCH-01 |
| C2 Active | 3 days of confirmed BEACON activity |
| Second IP | `54.193.127.66` — backup C2, now blocked |
| Cloud Risk | Azure AD — Service Principal check required |

### Expected Actions — Human

- [x] Analyst isolates all affected hosts simultaneously: SRV-ORION-01, DC-01, EXCH-01
- [x] Analyst confirms business impact of isolation: domain controller offline means domain authentication disrupted — notifies IT Operations
- [x] Analyst takes memory dumps on all 3 hosts before proceeding with remediation
- [x] Analyst blocks both C2 IPs at perimeter firewall: `13.59.205.66` and `54.193.127.66`
- [x] Analyst resets all credentials used by BEACON for lateral movement — separate set from initial access credentials
- [x] Analyst checks Azure AD for unauthorized Service Principals created in the past 3 days (T1098.001)
- [x] Analyst reviews AD FS signing certificate access — Golden SAML risk (T1606.002)
- [x] Analyst reviews Domain Controller event logs for Event ID 4662 — confirms whether DCSync occurred
- [x] Analyst reviews Exchange audit logs for mailbox export requests
- [x] Analyst prepares scope summary: 3 hosts confirmed, BEACON active 3 days, possible credential dump and cloud backdoor
- [x] SOC Lead escalates to CISO — confirmed nation-state C2 communication for 3 days
- [x] CISO activates external IR retainer and legal notification process
- [x] Analyst coordinates clean rebuilds of all 3 affected hosts after forensics are complete

---

## References

- [CISA Alert AA20-352A — SolarWinds](https://www.cisa.gov/uscert/ncas/alerts/aa20-352a)
- [MITRE T1071.001 — Application Layer Protocol](https://attack.mitre.org/techniques/T1071/001/)
- [MITRE S0154 — Cobalt Strike BEACON](https://attack.mitre.org/software/S0154/)
- [MITRE ATT&CK Campaign C0024](https://attack.mitre.org/campaigns/C0024/)
- Source Bundle: `apt29-solarwinds-stix-bundle.json` — indicators 8e1c9a7f, c3d4e5f6, relationship r030

> **Provenance:** C2 IPs, geolocation OpSec detail, BEACON SMB pipe, AdFind usage, actor attribution → ✅ APT29 STIX Bundle | Phase structure, traffic volumes, timestamps, lateral movement chain → 🤖 LLM (based on bundle data)

---

## Threat Scoring

| Metric | Value |
|--------|-------|
| **Threat Score** | 94 / 100 |
| **Severity** | CRITICAL |
| **Incident Priority** | P1 — Critical |
| **Response SLA** | Immediate |
| **Confidence** | 90% — HIGH (hard-linked STIX) |
| **Threat Actor Attribution** | APT29 / NOBELIUM / SVR Russia |
| **Score Factors** | Active C2 communication: +35 · Lateral movement confirmed: +25 · Nation-state: +20 · 3-day dwell: +14 |
