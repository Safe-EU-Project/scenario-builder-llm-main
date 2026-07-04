# SCN-APT29-010: Remote Email Collection via Exchange PowerShell — APT29 Data Collection

## Description

Exchange Online audit logs and on-premises Exchange Management Shell logs reveal a series of PowerShell cmdlets executed remotely by a compromised account. The commands used `New-MailboxExportRequest`, `Get-Mailbox`, and `Search-Mailbox` to collect and stage emails from senior executives and IT administrators. APT29 / NOBELIUM used this technique (T1114.002 — Email Collection: Remote Email Collection) to gather intelligence on internal security responses, peer organization communications, and government contracts. The collection was timed to occur during off-hours and targeted specific keywords: "solarwinds", "incident", "remediation", "classified". Attribution: APT29 / NOBELIUM / SVR Russia, confidence 88%.

---

## Phase 1 — Detection | T+0

### Inject

| Field | Value |
|-------|-------|
| Alert Source | Microsoft Defender for Office 365 / Exchange Audit Logs |
| Alert Type | `New-MailboxExportRequest` cmdlet executed |
| Executed By | `svc-monitoring@corp.local` |
| Source Host | `SRV-ORION-01` (10.10.5.22) |
| Target Mailboxes | `ciso@corp.local`, `cto@corp.local`, `security-team@corp.local` |
| Keywords Searched | `"solarwinds"`, `"incident"`, `"remediation"`, `"classified"` |
| Timestamp | 2024-05-09 03:15:00 UTC |
| Severity | HIGH |

### Expected Actions — System

- [ ] Exchange audit alert — mailbox export request from non-admin account
- [ ] Microsoft Defender for Office 365 alert — unusual mailbox access pattern
- [ ] SIEM ingests Exchange audit log

---

## Phase 2 — Alert | T+5min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | SIEM Correlation |
| Rule Name | `APT29_EMAIL_COLLECTION_REMOTE_PS` |
| MITRE Technique | T1114.002 — Remote Email Collection |
| Cmdlets Used | `Get-Mailbox`, `Search-Mailbox`, `New-MailboxExportRequest` |
| Connection | Remote PowerShell from `SRV-ORION-01` to `EXCH-01` |
| Mailboxes Targeted | 14 mailboxes — CISO, CTO, CFO, Legal, Security Team, IT Admins |
| Export Destination | `\\SRV-ORION-01\C$\Temp\MailExport\` — local staging on compromised server |

### Expected Actions — System

- [ ] SIEM alert — remote PS email collection targeting executive mailboxes
- [ ] Block further connections from SRV-ORION-01 to EXCH-01
- [ ] Alert SOC: email collection in progress

---

## Phase 3 — Triage | T+15min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | Exchange Admin Review |
| Emails Exported | ~4,200 emails matching keywords across 14 mailboxes |
| Export Files | `.pst` files created at `\\SRV-ORION-01\C$\Temp\MailExport\` |
| File Sizes | Total 2.8 GB — partially staged |
| Time Window | Collection active for ~90 minutes before detection |
| Sensitive Content | Legal counsel correspondence, CISO incident response drafts, IT remediation plans |

### Expected Actions — Human

- [ ] Confirm export files exist on SRV-ORION-01 — DO NOT delete yet (forensics)
- [ ] Determine which emails were exported — review `.pst` content
- [ ] Assess sensitivity — classify what APT29 likely has
- [ ] Check if exports were already exfiltrated before detection (check C2 traffic)

---

## Phase 4 — Exfiltration Check | T+35min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | Firewall + Proxy Logs |
| Finding | 2.1 GB outbound transfer to `13.59.205.66:443` — 48 minutes after collection started |
| Transfer Method | BEACON HTTPS channel — encrypted, evaded DLP |
| Exfiltrated | ~74% of collected emails — 3,100 emails transferred before C2 blocked |
| Remaining | 26% (1,100 emails) still on SRV-ORION-01 staging folder |
| DLP Status | Office 365 DLP did not trigger — transfer occurred over BEACON C2, not email |

### Expected Actions — Human

- [ ] Confirm 2.1 GB was transferred to APT29 C2 — classify as confirmed data breach
- [ ] Notify Data Protection Officer — GDPR/regulatory breach notification may be required
- [ ] Determine which emails were NOT exfiltrated (remaining 26%) — preserve for context
- [ ] Review: why did DLP not catch this? BEACON C2 bypassed DLP entirely

---

## Phase 5 — Legal + Remediation | T+90min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | Legal and SOC Lead |
| Breach Scope | 3,100 emails from 14 executive/admin mailboxes — confirmed breach |
| Regulatory | Potentially subject to GDPR, HIPAA (if health data), ITAR (government contracts) |
| Notification Timeline | GDPR: 72-hour notification window starts now |

### Expected Actions — Human

- [ ] Initiate breach notification process — contact legal and DPO immediately
- [ ] Notify board: APT29 confirmed exfiltrated senior leadership communications
- [ ] Remove export PSTs from SRV-ORION-01 after forensic imaging
- [ ] Enable audit logging on all mailboxes permanently going forward
- [ ] Restrict `New-MailboxExportRequest` to Exchange admins only via RBAC

---

## References

- [MITRE T1114.002 — Remote Email Collection](https://attack.mitre.org/techniques/T1114/002/)
- [MITRE ATT&CK Campaign C0024](https://attack.mitre.org/campaigns/C0024/)
- [CISA Alert AA20-352A — Email collection in SolarWinds](https://www.cisa.gov/uscert/ncas/alerts/aa20-352a)
- [Microsoft Exchange Audit Logging](https://docs.microsoft.com/en-us/exchange/policy-and-compliance/mailbox-audit-logging/mailbox-audit-logging)
- Source Bundle: `apt29-solarwinds-stix-bundle.json` — attack-pattern T1114.002, relationship r018

> **Provenance:** Email collection technique, Exchange PS use, actor attribution, staging + exfil chain → ✅ APT29 STIX Bundle | Keyword list, mailbox count, GB volumes, DLP bypass, regulatory references → 🤖 LLM (based on bundle data)

---

## Threat Scoring

| Metric | Value |
|--------|-------|
| **Threat Score** | 90 / 100 |
| **Severity** | HIGH — Data Breach |
| **Incident Priority** | P1 — Critical |
| **Response SLA** | Immediate — Regulatory Timer Active |
| **Confidence** | 88% — HIGH (hard-linked STIX) |
| **Threat Actor Attribution** | APT29 / NOBELIUM / SVR Russia |
| **Score Factors** | Confirmed data exfiltration: +35 · Executive comms compromised: +25 · Regulatory exposure: +20 · DLP bypass: +10 |
