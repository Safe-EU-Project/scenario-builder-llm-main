# SCN-APT29-003: Golden SAML Token Forgery — APT29 Cloud Lateral Movement

## Description

An anomalous SAML authentication event was detected: a CFO account that had been dormant for 90 days logged into Office 365 without an MFA challenge, from an IP outside any known range, followed immediately by Exchange PowerShell activity. This is characteristic of a Golden SAML attack — APT29 exfiltrated the private key of the AD FS SAML signing certificate and forged tokens for any user, bypassing MFA entirely. There is no file hash IOC — detection is exclusively behavioral. Attribution: APT29 / NOBELIUM / SVR Russia, confidence 95%.

---

## Phase 1 — Detection | T+0

### Inject

| Field | Value |
|-------|-------|
| Alert Source | Azure AD Sign-in Logs |
| Alert Type | Anomalous SAML authentication |
| User | `cfo@targetorg.com` |
| Account Status | Dormant — last login: 90 days ago |
| MFA | Bypassed — SAML token does not contain MFA claim |
| Source IP | `185.220.101.47` |
| Geolocation | Moscow, Russia |
| Expected Location | Washington DC, USA |
| Resources Accessed | Exchange Online, SharePoint, Azure AD |
| Severity | CRITICAL |

### Expected Actions — System

- [x] Azure AD Conditional Access fires alert — MFA bypass detected on dormant account
- [x] SIEM fires impossible travel alert: Washington DC → Moscow, 3 minutes elapsed
- [x] Azure AD revokes active session tokens for `cfo@targetorg.com`
- [x] Microsoft Defender for Cloud Apps (MCAS) alerts — anomalous cloud activity pattern
- [x] SIEM ingests Azure AD sign-in log and correlates with threat feed
- [x] Automatic P1 incident ticket created in ITSM

### Expected Actions — Human

- [x] SOC analyst acknowledges P1 alert and reviews Azure AD sign-in log for `cfo@targetorg.com`
- [x] Analyst confirms: SAML authentication succeeded with no MFA claim — unusual for this account
- [x] Analyst checks the source IP `185.220.101.47` against threat intel feeds — confirms Tor exit node / Russia-associated IP
- [x] Analyst checks geolocation: login from Moscow, Russia — account's last known location was Washington DC
- [x] Analyst confirms the account has been dormant for 90 days — verifies no legitimate business reason for login
- [x] Analyst checks what resources were accessed immediately after login: Exchange Online, SharePoint, Azure AD Portal
- [x] Analyst checks if `cfo@targetorg.com` received any login notification emails — determines whether the real CFO is aware
- [x] Analyst contacts CFO directly (phone) to confirm: did you log in to Office 365 in the last 30 minutes?

---

## Phase 2 — Alert | T+5min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | SIEM Correlation |
| Rule Name | `APT29_GOLDEN_SAML_MFA_BYPASS` |
| MITRE Technique | T1606.002 — Forge Web Credentials: SAML Tokens |
| SAML Issuer | `ADFS.targetorg.com` — on-premises AD FS server |
| Token Lifetime | 10 hours — extended beyond normal policy |
| MFA Claim | MISSING — normal tokens contain `amr: mfa` |
| Token Attributes | No device compliance check, no location constraint |
| Attribution | APT29 / NOBELIUM / SVR Russia (95%) |

### Expected Actions — System

- [x] SIEM correlation enriches alert with MITRE T1606.002 and APT29 attribution
- [x] SIEM checks for other accounts with similar anomalous SAML logins in past 24 hours
- [x] SIEM sends alert to SOC team with priority: CRITICAL
- [x] Azure AD Conditional Access blocks further logins from IP `185.220.101.47`
- [x] SIEM opens incident case with all correlated events: sign-in log, MCAS alert, impossible travel

### Expected Actions — Human

- [x] Analyst reviews the SAML token attributes — confirms the `amr` (authentication methods references) claim is missing the `mfa` value
- [x] Analyst checks the token lifetime — confirms it is 10 hours (extended beyond the organization's 1-hour Conditional Access policy)
- [x] Analyst identifies the SAML issuer: `ADFS.targetorg.com` — the on-premises AD FS server that signed this token
- [x] Analyst checks Azure AD for all SAML authentications from `ADFS.targetorg.com` in the past 7 days — looks for other forged tokens
- [x] Analyst checks AD FS event logs (Event ID 1200, 1201) on the AD FS server for all token issuance events
- [x] Analyst determines whether the AD FS signing certificate private key has been accessed recently — reviews AD FS server file access logs
- [x] Analyst checks AD FS configuration: was the signing certificate recently accessed or exported?
- [x] Analyst checks SIEM for any process activity on the AD FS server involving certificate stores (`certutil`, `mimikatz`, `ADFSDump`)
- [x] Analyst documents the forged token details: user, issuer, timestamp, resource, IP

---

## Phase 3 — Triage | T+15min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | AD FS Server Investigation |
| Tool Evidence | `ADFSDump.exe` found in `C:\Windows\Temp\` on AD FS server |
| ADFSDump | Tool used to extract ADFS token-signing certificate and its private key |
| Certificate Extracted | `ADFS Token Signing Certificate` — private key confirmed exported |
| Export Timestamp | 2024-05-07 01:44:29 UTC (6 days before Golden SAML use) |
| Actor Action | Actor had 6-day gap between key extraction and Golden SAML login |

### Expected Actions — Human

- [x] Analyst navigates to `C:\Windows\Temp\` on the AD FS server — confirms `ADFSDump.exe` exists
- [x] Analyst hashes `ADFSDump.exe` and cross-checks against known ADFSDump tool hashes — confirms it is the APT29-linked version
- [x] Analyst reviews when `ADFSDump.exe` was created and executed — confirms export timestamp: 2024-05-07 01:44:29 UTC
- [x] Analyst checks how `ADFSDump.exe` was delivered to the AD FS server — traces back process lineage (likely via BEACON lateral movement from SRV-ORION-01)
- [x] Analyst reviews AD FS event logs on the day of extraction — identifies Event ID 1202 (token-signing certificate access)
- [x] Analyst confirms the ADFS signing certificate private key was successfully exported — checks if it was written to disk or exfiltrated via BEACON
- [x] Analyst checks BEACON C2 traffic logs for the 6-day gap — confirms actor exfiltrated the certificate private key before using it
- [x] Analyst identifies the scope: with the private key, the actor can forge tokens for ANY user in the organization indefinitely
- [x] Analyst immediately revokes the current AD FS token-signing certificate
- [x] Analyst checks if a new AD FS signing certificate has been automatically generated (AD FS rotates certificates every year by default)
- [x] Analyst checks what other accounts the actor has used Golden SAML tokens for in the past 6 days
- [x] Analyst documents all findings in the incident case

---

## Phase 4 — Impact Assessment | T+45min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | Azure AD Audit — 7-day Lookback |
| Forged Tokens Found | 8 accounts logged in via forged SAML tokens over 6 days |
| Accounts | CFO, CTO, CISO, 3 × IT Admins, 2 × Legal Counsel |
| Resources Accessed | Exchange Online, SharePoint, Azure AD, Azure Key Vault |
| Data Accessed | Executive emails, legal contracts, Azure Key Vault secrets |
| Azure Key Vault | Actor accessed 3 secrets: API key, database connection string, storage account key |

### Expected Actions — Human

- [x] Analyst enumerates all 8 accounts that were accessed via forged SAML tokens — records each login timestamp, source IP, resources accessed
- [x] Analyst checks Exchange Online audit logs for each affected account — identifies all emails read or exported
- [x] Analyst checks SharePoint audit logs — identifies all files accessed or downloaded per account
- [x] Analyst checks Azure AD audit logs — identifies any administrative actions performed by the actor
- [x] Analyst reviews Azure Key Vault access logs — confirms which secrets were accessed: API key, database connection string, storage account key
- [x] Analyst immediately rotates all Azure Key Vault secrets that were accessed: API key, DB connection string, storage account key
- [x] Analyst checks whether the actor used the accessed API keys to authenticate to external services
- [x] Analyst checks whether the database connection string was used to query or export database data
- [x] Analyst documents full data access scope for legal and regulatory review
- [x] Analyst notifies Data Protection Officer: executive email access + Key Vault secrets confirmed
- [x] Legal team assesses GDPR breach notification requirement — 72-hour clock starts
- [x] Analyst prepares executive briefing: all 8 impacted accounts listed with access details

---

## Phase 5 — Containment & Cloud Hardening | T+90min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | SOC Lead — Remediation Plan |
| Immediate Risk | Actor still has valid certificate private key — can forge new tokens any time |
| Remediation | Must replace AD FS signing certificate AND revoke all existing tokens |

### Expected Actions — Human

- [x] Analyst revokes the compromised AD FS token-signing certificate immediately
- [x] Analyst generates a new AD FS token-signing certificate with a new key pair
- [x] Analyst forces AD FS to re-sign all future SAML tokens with the new certificate
- [x] Analyst revokes all current Azure AD session tokens for all users: forces re-authentication globally
- [x] Analyst disables the AD FS server temporarily while certificate replacement is in progress
- [x] Analyst removes `ADFSDump.exe` from the AD FS server and quarantines it for forensics
- [x] Analyst isolates the AD FS server from the network until forensic investigation is complete
- [x] Analyst configures Azure AD Conditional Access: reject any SAML token missing the `amr: mfa` claim — even if AD FS is the issuer
- [x] Analyst implements Privileged Identity Management (PIM) for all admin accounts — require just-in-time approval
- [x] SOC Lead escalates to CISO: 8 executive and admin accounts compromised, Key Vault accessed
- [x] External IR team engaged to perform full forensic investigation of the AD FS server
- [x] Legal team prepares breach notifications for affected parties and regulators

---

## References

- [MITRE T1606.002 — Forge Web Credentials: SAML Tokens](https://attack.mitre.org/techniques/T1606/002/)
- [MITRE ATT&CK Campaign C0024](https://attack.mitre.org/campaigns/C0024/)
- [CyberArk — Golden SAML attack research](https://www.cyberark.com/resources/threat-research-blog/golden-saml-newly-discovered-attack-technique-forges-authentication-to-cloud-services)
- [Microsoft — Detecting and mitigating Golden SAML](https://www.microsoft.com/security/blog/2021/01/20/microsoft-365-defender-detects-solorigate-compromise-and-provides-full-visibility-into-attack/)
- Source Bundle: `apt29-solarwinds-stix-bundle.json` — attack-pattern T1606.002, relationship r017

> **Provenance:** Golden SAML technique, AD FS certificate extraction, actor attribution, TTPs → ✅ APT29 STIX Bundle | CFO account scenario, ADFSDump detail, 8 accounts, Key Vault access, remediation steps → 🤖 LLM (based on bundle data)

---

## Threat Scoring

| Metric | Value |
|--------|-------|
| **Threat Score** | 98 / 100 |
| **Severity** | CRITICAL |
| **Incident Priority** | P1 — Critical |
| **Response SLA** | Immediate |
| **Confidence** | 95% — HIGH (hard-linked STIX) |
| **Threat Actor Attribution** | APT29 / NOBELIUM / SVR Russia |
| **Score Factors** | MFA bypass via token forgery: +35 · 8 executive accounts: +25 · Nation-state: +20 · Key Vault secrets accessed: +18 |
