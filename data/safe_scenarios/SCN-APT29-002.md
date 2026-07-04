# SCN-APT29-002: DNS Beaconing to avsvmcloud.com — SUNBURST C2 Channel Detected

## Description

DNS resolver logs show repeated queries from an internal SolarWinds Orion server to subdomains of `avsvmcloud.com` — the SUNBURST backdoor's hardcoded DGA-based C2 domain. APT29 / NOBELIUM used DNS-based C2 (T1071.004) combined with a Domain Generation Algorithm (T1568.002) to exfiltrate system information and receive activation commands. Each subdomain encodes the victim's hostname and domain via a custom XOR algorithm. Queries were happening approximately every 12 hours over a 14-day dormancy period. The domain has been sinkholed by Microsoft since December 2020 — live queries today indicate an unpatched installation of the trojanized SolarWinds update. Attribution: APT29 / NOBELIUM / SVR Russia, confidence 100%.

---

## Phase 1 — Detection | T+0

### Inject

| Field | Value |
|-------|-------|
| Alert Source | DNS Resolver / SIEM |
| Query | `r8swhqn7yz0a8.appsync-api.us-east-2.avsvmcloud.com` |
| Source Host | `SRV-ORION-01` (10.10.5.22) |
| Query Count | 847 over 14 days |
| Interval | ~12 hours per query |
| DNS Response | CNAME → `sinkhole.microsoft.com` |
| IOC Match | `avsvmcloud.com` — APT29/SUNBURST C2 domain |
| Severity | CRITICAL |

### Expected Actions — System

- [x] DNS resolver logs the query and generates a security event
- [x] SIEM ingests the DNS event and matches it against the APT29 threat intel feed
- [x] SIEM fires alert: `APT29_SUNBURST_DNS_C2_QUERY` — threat actor attribution: APT29 / NOBELIUM
- [x] Automated DNS block rule applied: `*.avsvmcloud.com` → NXDOMAIN or sinkhole redirect
- [x] Automatic P1 incident ticket created in ITSM
- [x] SIEM notifies SOC dashboard and on-call analyst

### Expected Actions — Human

- [x] SOC analyst acknowledges P1 alert within 5 minutes
- [x] Analyst identifies source host `SRV-ORION-01` from the alert and opens the DNS log for that host
- [x] Analyst confirms the queried domain: `avsvmcloud.com` — cross-checks against CISA AA20-352A and APT29 IOC feeds
- [x] Analyst checks the total query count (847) and timestamps — confirms beaconing started 14 days ago
- [x] Analyst verifies the DNS response was `sinkhole.microsoft.com` — confirms the sinkhole was active during all queries
- [x] Analyst determines whether any DNS response returned a live IP (non-sinkhole) — reviews all 847 response records
- [x] Analyst notifies SOC Lead and escalates to P1 nation-state incident protocol
- [x] Analyst opens the MITRE ATT&CK C0024 campaign page to review the full SolarWinds attack chain

---

## Phase 2 — Alert | T+5min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | SIEM Correlation |
| Rule Name | `APT29_SUNBURST_DNS_BEACONING` |
| MITRE Technique | T1071.004 — Application Layer Protocol: DNS |
| MITRE Technique | T1568.002 — Domain Generation Algorithms |
| DGA Subdomain | `r8swhqn7yz0a8` — encodes victim hostname and domain |
| Campaign | MITRE C0024 — SolarWinds Compromise |
| Threat Actor | APT29 / NOBELIUM / SVR Russia |
| Attribution Confidence | 100% |

### Expected Actions — System

- [x] SIEM correlation enriches alert with MITRE technique tags: T1071.004, T1568.002
- [x] SIEM enriches with threat actor: APT29 / NOBELIUM / SVR Russia, campaign: C0024
- [x] SIEM checks for correlated events: any IOC hash matches on the same source host
- [x] SIEM checks for additional hosts querying `*.avsvmcloud.com` — fleet-wide correlation
- [x] SIEM sends alert to SOC team and opens a formal incident case with all correlated events

### Expected Actions — Human

- [x] Analyst reviews the enriched alert — confirms MITRE T1071.004 (DNS C2) and T1568.002 (DGA)
- [x] Analyst decodes the DGA subdomain `r8swhqn7yz0a8` — identifies that it encodes victim environment data (hostname, domain name) using SUNBURST's custom XOR-based DGA
- [x] Analyst checks if any other internal host made queries to `*.avsvmcloud.com` — reviews fleet-wide DNS logs for the past 30 days
- [x] Analyst verifies whether `SRV-ORION-01` also queried the follow-on C2 domains: `freescanonline.com`, `deftsecurity.com`
- [x] Analyst confirms: DNS block for `*.avsvmcloud.com` is active on the DNS resolver — tests with a manual nslookup
- [x] Analyst confirms: block for follow-on domains `freescanonline.com`, `deftsecurity.com` also applied
- [x] Analyst checks firewall egress logs — confirms no direct TCP connections to `13.59.205.66` or `54.193.127.66` occurred from SRV-ORION-01
- [x] Analyst documents correlation findings in the incident case: number of hosts affected, query timeline, sinkhole status

---

## Phase 3 — Triage | T+15min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | Analyst Review — Host |
| DLL | `SolarWinds.Orion.Core.BusinessLayer.dll` |
| DLL Hash MD5 | `b91ce2fa41029f6955bff20079468448` — CONFIRMED SUNBURST |
| Orion Version | `2020.2.0` — in affected range |
| Process | `SolarWinds.BusinessLayerHost.exe` — running |
| Security Tools | Windows Defender disabled via registry (T1562.001) |
| Registry Key | `HKLM\SYSTEM\CurrentControlSet\services\WinDefend\Start = 4` |

### Expected Actions — Human

- [x] Analyst connects to `SRV-ORION-01` in read-only forensic mode and navigates to the SolarWinds installation directory
- [x] Analyst hashes `SolarWinds.Orion.Core.BusinessLayer.dll` and confirms MD5: `b91ce2fa41029f6955bff20079468448` — SUNBURST confirmed
- [x] Analyst checks the registry key `HKLM\SYSTEM\CurrentControlSet\services\WinDefend\Start` — confirms value is `4` (disabled)
- [x] Analyst checks which other security services were disabled — queries all services with `Start = 4` that should be `2` (automatic)
- [x] Analyst checks `SolarWinds.BusinessLayerHost.exe` process — confirms it is currently running and records the PID
- [x] Analyst checks whether SUNBURST has completed its 14-day dormancy and entered active C2 mode — reviews DGA query pattern
- [x] Analyst checks process tree for `SolarWinds.BusinessLayerHost.exe` — identifies any child processes (cmd.exe, powershell.exe) that indicate active post-exploitation
- [x] Analyst checks Windows Event Log for security events from the past 14 days on SRV-ORION-01
- [x] Analyst checks if file `gracious_truth.jpg` exists in `C:\Windows\SysWOW64\` — TEARDROP second-stage indicator
- [x] Analyst checks for named pipe `583da945-62af-10e8-4902-a8f205c72b2e` — SUNBURST mutex
- [x] Analyst re-enables Windows Defender temporarily to scan the host — then immediately takes memory dump before any further action
- [x] Analyst documents all triage findings in the incident case with timestamps

---

## Phase 4 — DGA Analysis & Scope | T+35min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | DNS Log Analysis |
| Domains Queried | 14 unique subdomains over 847 total queries |
| Encoding | Victim hostname + domain encoded in subdomain via custom XOR |
| Sinkhole | All responses → `sinkhole.microsoft.com` — no live C2 contact |
| Other Hosts | Fleet scan: 2 additional hosts found querying `*.avsvmcloud.com` |
| Additional Hosts | `SRV-ORION-02` (10.10.5.23), `SRV-MON-01` (10.10.6.11) |

### Expected Actions — Human

- [x] Analyst confirms: 2 additional hosts are also infected — `SRV-ORION-02` and `SRV-MON-01`
- [x] Analyst checks SolarWinds Orion version on `SRV-ORION-02` and `SRV-MON-01` — confirms both also run 2020.2.0
- [x] Analyst checks DLL hashes on `SRV-ORION-02` and `SRV-MON-01` — confirms SUNBURST on both
- [x] Analyst decodes each unique DGA subdomain to confirm victim environment data — compares subdomains across the 3 infected hosts
- [x] Analyst checks whether the sinkhole blocked ALL queries or whether any query received a live response — reviews every DNS response record
- [x] Analyst checks DNS query timestamps for all 3 hosts — determines if infections happened simultaneously (same update batch) or at different times
- [x] Analyst blocks all 3 hosts from external DNS resolution — applies firewall rules per host
- [x] Analyst updates the incident scope: 3 infected hosts confirmed — expands scope check to all remaining Orion servers
- [x] Analyst queries asset database for all servers running SolarWinds Orion — generates full list for fleet-wide hash check
- [x] Analyst submits SUNBURST DLL hash to fleet-wide EDR search — confirms results across all endpoints
- [x] Analyst documents DGA decode methodology and results for the incident report
- [x] Analyst prepares summary of scope for SOC Lead briefing

---

## Phase 5 — Containment | T+60min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | SOC Lead — Scope Decision |
| Infected Hosts | SRV-ORION-01, SRV-ORION-02, SRV-MON-01 |
| C2 Status | Sinkholed — no confirmed live actor contact |
| Second-Stage | TEARDROP found on SRV-ORION-01 — BEACON likely active |
| Cloud Risk | Azure AD — check for Golden SAML and Service Principal backdoors |

### Expected Actions — Human

- [x] Analyst isolates all 3 infected hosts simultaneously: SRV-ORION-01, SRV-ORION-02, SRV-MON-01
- [x] Analyst confirms business impact of isolation: SolarWinds Orion monitoring is now offline — notifies IT Operations
- [x] Analyst takes memory dumps on all 3 hosts before proceeding
- [x] Analyst blocks all APT29 C2 IPs at perimeter firewall: `13.59.205.66`, `54.193.127.66`
- [x] Analyst checks Azure AD audit logs for unauthorized Service Principals (T1098.001) created in the past 14 days
- [x] Analyst checks AD FS token-signing certificate — reviews whether it was accessed or exported (Golden SAML risk, T1606.002)
- [x] Analyst checks Domain Controller event logs for Event ID 4662 — DCSync activity (T1003.006)
- [x] Analyst checks Exchange audit logs for mailbox export requests from any of the 3 infected hosts (T1114.002)
- [x] SOC Lead escalates to CISO — nation-state actor confirmed, 3 hosts infected, scope expanding
- [x] CISO activates external IR retainer — engage specialized APT29 incident response firm
- [x] Legal team notified — assess regulatory notification obligations (GDPR 72-hour clock, CISA ED 21-01)
- [x] Analyst prepares a preliminary incident summary for executive briefing: who, what, when, confirmed scope, next steps
- [x] Analyst coordinates clean SolarWinds Orion 2020.2.1 HF 2 build for eventual reinstallation after forensics complete

---

## References

- [MITRE T1071.004 — DNS C2](https://attack.mitre.org/techniques/T1071/004/)
- [MITRE T1568.002 — Domain Generation Algorithms](https://attack.mitre.org/techniques/T1568/002/)
- [MITRE ATT&CK Campaign C0024](https://attack.mitre.org/campaigns/C0024/)
- [Microsoft sinkhole of avsvmcloud.com](https://msrc-blog.microsoft.com/2020/12/13/customer-guidance-on-recent-nation-state-cyber-attacks/)
- [CISA Emergency Directive 21-01](https://www.cisa.gov/emergency-directive-21-01)
- Source Bundle: `apt29-solarwinds-stix-bundle.json` — attack-pattern T1071.004, T1568.002, indicator r8swhqn7yz0a8

> **Provenance:** DGA domain, query pattern, dormancy period, sinkhole detail, actor attribution, TTPs → ✅ APT29 STIX Bundle | Phase structure, fleet-wide scope, registry details, DGA decode narrative → 🤖 LLM (based on bundle data)

---

## Threat Scoring

| Metric | Value |
|--------|-------|
| **Threat Score** | 93 / 100 |
| **Severity** | CRITICAL |
| **Incident Priority** | P1 — Critical |
| **Response SLA** | Immediate |
| **Confidence** | 100% — CONFIRMED (hard-linked STIX) |
| **Threat Actor Attribution** | APT29 / NOBELIUM / SVR Russia |
| **Score Factors** | Active DGA beaconing: +30 · Nation-state: +25 · 3 hosts infected: +20 · Security tools disabled: +18 |
