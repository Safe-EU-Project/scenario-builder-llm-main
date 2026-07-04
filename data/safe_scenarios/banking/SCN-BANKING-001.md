# SCN-BANKING-001: SWIFT Financial Fraud via Compromised Operator Credentials

## Sector
banking

## Description

A European commercial bank's SWIFT Alliance Access terminal received unauthorized payment messages after an operator's credentials were stolen via a spear-phishing campaign. The attacker submitted 7 fraudulent SWIFT MT103 transfer instructions totalling €4.2M directed to correspondent banks in Southeast Asia before anomaly detection flagged the activity. The attack mirrors the Bangladesh Bank heist pattern (2016) and the SWIFT Alliance CACTUS campaign attributed to Lazarus Group.

Attack Type: Financial fraud via SWIFT operator compromise  
MITRE ATT&CK: T1566.001 (Spear Phishing), T1078 (Valid Accounts), T1048 (Exfiltration Over Alternative Protocol)  
Financial Impact: €4.2M fraudulent transfers  
Attribution: Lazarus Group / APT38 (North Korea-linked), confidence HIGH

---

## Phase 1 — Detection | T+0

### Inject

| Field | Value |
|-------|-------|
| Alert Source | SWIFT Alliance Fraud Detection |
| Alert Type | Anomalous MT103 batch — off-hours, unusual beneficiary pattern |
| Operator Account | `swift_ops_mireille.dubois` |
| Session Start | 02:14 UTC (outside business hours) |
| Source IP | `185.220.101.47` (Tor exit node — not operator's registered IP) |
| Transactions | 7 × MT103 messages, total €4,200,000 |
| Beneficiary Banks | 3 banks in Cambodia, Myanmar, Philippines |
| SWIFT BIC Receiver | `BCELKHPP`, `KBPHMYKL`, `MBCBMYKL` |
| Severity | CRITICAL |

### Expected Actions — System

- SWIFT fraud detection module flags off-hours login from unregistered IP
- Automatic transaction hold applied to 4 pending MT103 messages (3 already sent)
- SIEM correlation rule fires: `SWIFT_OFFHOURS_UNUSUAL_BENEFICIARY`
- SOC alert generated — P1 financial fraud incident ticket created
- SWIFT operator session logged for audit trail

### Expected Actions — Human

- SOC analyst acknowledges P1 alert within ≤5 minutes
- Analyst contacts SWIFT Alliance administrator to immediately revoke session for `swift_ops_mireille.dubois`
- Analyst confirms with the physical operator (phone/badge system) whether she is present at the workstation — she is not (it is 02:14 UTC)
- Analyst places an immediate transaction recall request for the 3 already-sent MT103 messages via SWIFT GPI tracker
- Analyst documents the 7 transaction reference numbers for investigation
- Analyst notifies the Head of Financial Crime Compliance and CISO

---

## Phase 2 — Credential Investigation | T+15min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | Email Security Gateway |
| Subject | `Urgent: SWIFT Maintenance Window — Verify Credentials` |
| Sender | `swift-ops-noreply@swlft-maintenance.eu` (typosquat) |
| Recipient | `mireille.dubois@bank.eu` |
| Date | 3 days prior — Monday 09:15 |
| Attachment | `SWIFTnet_AuthUpdate.html` (HTML credential harvester) |
| Action Taken | Delivered — gateway did not block |
| Credential Captured | SWIFT Alliance username + password + 2FA seed |

### Expected Actions — Human

- Analyst reviews email gateway logs for the compromised operator — identifies phishing email delivered 3 days prior
- Analyst extracts the phishing domain `swlft-maintenance.eu` — checks WHOIS (registered 5 days ago)
- Analyst submits the phishing domain for immediate DNS blackholing
- Analyst checks if any other SWIFT operator received the same phishing email — queries email gateway logs
- Analyst checks if the 2FA TOTP seed was compromised — confirms the HTML harvester captured the 6-digit OTP via real-time relay (adversary-in-the-middle phishing)
- Analyst notifies all SWIFT operators: password reset mandatory, new 2FA enrollment required
- Analyst preserves the phishing email as forensic evidence (EML export)
- Analyst reports phishing domain to SWIFT ISAC and national financial CERT

---

## Phase 3 — Transaction Recall & Correspondent Bank Coordination | T+30min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | SWIFT GPI Tracker |
| MT103 #1 (€1,200,000) | Status: ACSC — funds credited to beneficiary account |
| MT103 #2 (€800,000) | Status: ACSC — funds credited |
| MT103 #3 (€500,000) | Status: PDNG — pending at correspondent bank |
| MT103 #4-7 (€1,700,000) | Status: HOLD — frozen by fraud detection |
| Correspondent Bank | Phnom Penh Commercial Bank (BCELKHPP) |
| Contact | +855-23-XXX-XXX — Financial Crime Unit |

### Expected Actions — Human

- Analyst initiates formal SWIFT gpi recall request (MT192) for the 3 sent transactions
- Analyst calls the Financial Crime Unit at BCELKHPP (Phnom Penh) directly — requests freeze on beneficiary accounts
- Analyst contacts correspondent banks in Myanmar and Philippines — same freeze request
- Analyst opens a formal case with the national financial intelligence unit (FIU/FINTRAC equivalent)
- Analyst documents the beneficiary IBAN/account numbers for law enforcement referral
- Head of Compliance notifies the national central bank within required timeframe (typically ≤2h for major fraud)
- Legal team initiates inter-bank legal hold procedures
- Analyst checks whether the beneficiary accounts have already been emptied (often within minutes via mule accounts)

---

## Phase 4 — Containment & Forensics | T+60min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | Endpoint Forensics — Operator Workstation |
| Host | `WS-SWIFT-OPS-04` (operator Mireille Dubois) |
| Keylogger Found | `winupdater.exe` — disguised keylogger in AppData\Roaming |
| First Seen | Same day as phishing email delivery |
| C2 Communication | Outbound HTTPS to `api.cloudflare-analytics-cdn.net` (DGA) |
| SWIFT Credentials Exfil | Confirmed via network capture |
| Lateral Movement | SWIFT operator workstations `WS-SWIFT-OPS-01` through `WS-SWIFT-OPS-06` — lateral movement detected via WMI |

### Expected Actions — Human

- Analyst isolates `WS-SWIFT-OPS-04` from the network immediately
- Analyst images the workstation disk for forensic preservation before reimaging
- Analyst takes a memory dump of the live system (captures keylogger in memory)
- Analyst scans all 6 SWIFT operator workstations for `winupdater.exe` and related IOCs
- Analyst blocks the C2 domain `api.cloudflare-analytics-cdn.net` at the perimeter firewall and DNS resolver
- Analyst checks whether the attacker accessed any other SWIFT operator credentials stored on the compromised host
- SWIFT Alliance administrator disables all operator accounts — requires re-authentication with fresh credentials before next business day
- CISO convenes emergency response team — engages external forensic IR firm
- Legal team assesses regulatory notification obligations: ECB, national banking regulator, data protection authority (GDPR Article 33)

---

## Phase 5 — Legal Reporting & Recovery | T+4h

### Inject

| Field | Value |
|-------|-------|
| Recovered Funds | MT103 #3 (€500,000) recovered via recall — correspondent bank froze before credit |
| Lost Funds | €2,000,000 (MT103 #1 and #2) — accounts emptied within 8 minutes |
| Insurance | Cyber liability policy — €5M coverage, €250,000 deductible |
| Regulatory Deadline | National banking regulator requires notification within 4 hours of confirmed major incident |
| Law Enforcement | Financial cybercrime unit formally engaged |

### Expected Actions — Human

- Head of Compliance formally notifies the national banking regulator within the 4-hour deadline
- Legal team files police report with the financial cybercrime unit — provides all transaction details, IOCs, and forensic evidence
- Compliance officer notifies the ECB TIBER-EU framework contact for cross-border coordination
- CISO notifies SWIFT ISAC with full technical IOC package for industry-wide sharing
- Communications team drafts internal staff notice — no public statement until law enforcement cleared
- Finance team begins insurance claim process — documents total financial exposure (€2M direct loss + investigation costs)
- IT Security team implements SWIFT hardening: hardware MFA tokens for all operators, IP whitelisting for SWIFT Alliance access, out-of-band transaction verification for amounts >€100,000

---

## References

- SWIFT ISAC Customer Security Programme (CSP) Mandatory Controls
- SWIFT MT103 Single Customer Credit Transfer standard
- Lazarus Group / APT38 SWIFT campaign analysis — BAE Systems / SWIFT (2016-2020)
- Bangladesh Bank heist post-mortem — Financial Stability Board (2017)
- ECB Cyber Incident Taxonomy — European Central Bank
- MITRE ATT&CK Financial Sector — T1566.001, T1078, T1048, T1657

## Threat Scoring

| Metric | Value |
|--------|-------|
| **Threat Score** | 92 / 100 |
| **Severity** | CRITICAL |
| **Incident Priority** | P1 — Critical |
| **Financial Impact** | €2,000,000 direct loss |
| **Response SLA** | Immediate |
| **Confidence** | HIGH — confirmed fraud pattern |
| **Sector** | Banking / Financial Services |
| **Threat Actor** | Lazarus Group / APT38 (DPRK-linked) |
