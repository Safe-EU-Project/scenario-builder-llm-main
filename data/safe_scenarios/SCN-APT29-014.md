# SCN-APT29-014: Dormant Account Lateral Movement — Valid Credentials for Persistence

## Description

Active Directory logs show authentication events from accounts that have not been used for 90+ days — dormant accounts that were previously missed in offboarding or created as "break-glass" service accounts. APT29 / NOBELIUM specifically targeted these accounts (T1078 — Valid Accounts) because dormant accounts are less likely to be monitored for anomalous authentication and their use does not generate the same alerts as newly created accounts. BEACON extracted dormant account credentials via DCSync and then used them to authenticate across the domain — avoiding detection by User Behavior Analytics (UBA) which compares current behavior to historical baselines (no history = no baseline = no alert). Attribution: APT29 / NOBELIUM / SVR Russia, confidence 87%.

---

## Phase 1 — Detection | T+0

### Inject

| Field | Value |
|-------|-------|
| Alert Source | UEBA — Unusual Authentication |
| Alert Type | Account authentication after 120+ days of inactivity |
| Account | `svc-backup-legacy` — service account, last active 134 days ago |
| Authentication | NTLM login to `DC-01` from `SRV-ORION-01` |
| Timestamp | 2024-05-08 03:44:29 UTC |
| Account Status | Enabled — never disabled after service decommissioned |
| Severity | HIGH |

### Expected Actions — System

- [ ] UEBA alert — dormant account authenticated after 134 days
- [ ] Check AD account status — confirm account should be disabled
- [ ] SIEM receives authentication event from Domain Controller

---

## Phase 2 — Alert | T+5min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | SIEM Correlation |
| Rule Name | `APT29_DORMANT_ACCOUNT_LATERAL_MOVEMENT` |
| MITRE Technique | T1078 — Valid Accounts |
| Accounts Used | `svc-backup-legacy`, `admin-2019-deprecated`, `helpdesk-test-01` |
| Source | All authenticated from `SRV-ORION-01` (compromised Orion server) |
| Credential Origin | DCSync attack (SCN-APT29-007) — all hashes extracted from DC |
| UEBA Bypass | No behavioral baseline for dormant accounts → no anomaly alert from UBA |

### Expected Actions — System

- [ ] SIEM fires alert — multiple dormant accounts authenticating from same source
- [ ] Pattern: 3 dormant accounts used within 8-minute window — automated (BEACON)
- [ ] Alert SOC: lateral movement via credential reuse from DCSync

---

## Phase 3 — Triage | T+15min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | AD Admin Review |
| Account 1 | `svc-backup-legacy` — had write access to file server shares (NEVER cleaned up) |
| Account 2 | `admin-2019-deprecated` — Domain Admin privileges (NEVER revoked post-offboarding) |
| Account 3 | `helpdesk-test-01` — read access to HR system (test account left active) |
| Most Dangerous | `admin-2019-deprecated` — DOMAIN ADMIN — actor used this for DC operations |
| Files Accessed | Finance shares, HR employee data, Security configurations |

### Expected Actions — Human

- [ ] Disable ALL three accounts immediately
- [ ] CRITICAL: `admin-2019-deprecated` is Domain Admin — actor had DA access
- [ ] Determine what actor did with Domain Admin rights: new accounts? GPO changes?
- [ ] Audit all accounts with DA privileges — remove stale DA accounts

---

## Phase 4 — Scope of Access | T+30min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | AD Audit + File Server Logs |
| DA Account Activity | `admin-2019-deprecated` created new AD account `helpdesk-support-01` 2 days ago |
| New Account | `helpdesk-support-01` — NOT legitimate — actor created for persistence |
| New Account Privileges | Domain Admin — actor ensured persistence before being detected |
| Files Accessed | `\\FILESERVER\HR\` — 340 employee records viewed via `helpdesk-test-01` |
| GPO Check | No GPO modifications — actor used account but did not modify policy |

### Expected Actions — Human

- [ ] Disable `helpdesk-support-01` immediately — APT29-created persistence account
- [ ] Audit ALL accounts created in last 30 days — verify each is legitimate
- [ ] HR data breach confirmed: 340 employee records accessed — notify HR Director
- [ ] Run full AD audit: compare current state to last known-good backup
- [ ] GDPR: employee personal data compromised — regulatory notification required

---

## Phase 5 — Hardening | T+90min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | SOC Lead — Systemic Gap |
| Root Cause | No regular review of dormant accounts — standard practice required |
| Gap | UBA has no baseline for dormant accounts — blind spot |
| Gap 2 | Domain Admin accounts from 2019 never revoked — offboarding process failure |

### Expected Actions — Human

- [ ] Implement quarterly AD account review: disable any account inactive > 60 days
- [ ] Reduce Domain Admin account count — principle of least privilege
- [ ] Enable just-in-time privileged access (PIM) for Domain Admin operations
- [ ] Configure UBA rule: ANY authentication after 90+ days inactivity = immediate alert
- [ ] Implement offboarding process: account disable within 1 business day of departure

---

## References

- [MITRE T1078 — Valid Accounts](https://attack.mitre.org/techniques/T1078/)
- [MITRE T1078.002 — Domain Accounts](https://attack.mitre.org/techniques/T1078/002/)
- [MITRE ATT&CK Campaign C0024](https://attack.mitre.org/campaigns/C0024/)
- [CIS Control 5 — Account Management](https://www.cisecurity.org/controls/account-management)
- Source Bundle: `apt29-solarwinds-stix-bundle.json` — attack-pattern T1078, relationship r016

> **Provenance:** Valid accounts technique, dormant account abuse, actor attribution → ✅ APT29 STIX Bundle | Specific account names, 134-day dormancy, HR data breach, UBA blind spot, persistence account creation → 🤖 LLM (based on bundle data)

---

## Threat Scoring

| Metric | Value |
|--------|-------|
| **Threat Score** | 88 / 100 |
| **Severity** | CRITICAL — Domain Admin via Dormant Account |
| **Incident Priority** | P1 — Critical |
| **Response SLA** | Immediate |
| **Confidence** | 87% — HIGH (hard-linked STIX) |
| **Threat Actor Attribution** | APT29 / NOBELIUM / SVR Russia |
| **Score Factors** | Domain Admin compromised: +30 · HR data breach: +25 · Persistence account created: +20 · UBA blind spot: +13 |
