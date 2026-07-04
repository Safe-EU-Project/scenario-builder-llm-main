# SCN-APT29-009: Azure AD Backdoor — Unauthorized Service Principal Created

## Description

Azure AD audit logs show the creation of a new OAuth 2.0 Service Principal with `AppRoleAssignment.ReadWrite.All` and `Directory.ReadWrite.All` permissions, created by an account not authorized to perform such operations. APT29 / NOBELIUM used this technique (T1098.001 — Account Manipulation: Additional Cloud Credentials) extensively during the SolarWinds Compromise to establish persistent cloud access that survived on-premises remediation. Even if the compromised SolarWinds server is wiped, the cloud backdoor remains. The Service Principal can be used to read all Azure AD users, create new admin accounts, access Microsoft 365 data, and modify conditional access policies. Attribution: APT29 / NOBELIUM / SVR Russia, confidence 92%.

---

## Phase 1 — Detection | T+0

### Inject

| Field | Value |
|-------|-------|
| Alert Source | Azure AD Audit Log / Microsoft Defender for Cloud Apps |
| Alert Type | New Service Principal created with high-privilege permissions |
| Service Principal Name | `Microsoft_365_Monitoring_Service` |
| Created By | `svc-monitoring@corp.local` (compromised service account) |
| Permissions Granted | `AppRoleAssignment.ReadWrite.All`, `Directory.ReadWrite.All` |
| Timestamp | 2024-05-08 01:44:22 UTC |
| Consent Type | Application-level — no user consent dialog |
| Severity | CRITICAL |

### Expected Actions — System

- [ ] Azure AD alert — high-privilege Service Principal created by non-admin account
- [ ] Microsoft Defender for Cloud Apps alert — suspicious OAuth app registered
- [ ] SIEM receives Azure AD audit log event

---

## Phase 2 — Alert | T+5min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | SIEM Correlation |
| Rule Name | `APT29_AZURE_SERVICE_PRINCIPAL_BACKDOOR` |
| MITRE Technique | T1098.001 — Additional Cloud Credentials |
| Application ID | `a7f34d12-8e91-4c2b-b3c7-5d8a9e4f1234` |
| Certificate Credential | Self-signed cert added to Service Principal (exfiltration method) |
| Cloud Tenant | `corp.onmicrosoft.com` |
| On-Prem Correlation | `svc-monitoring` account — same account used in DCSync (T1003.006) |

### Expected Actions — System

- [ ] SIEM correlates: same compromised account used for DCSync (on-prem) AND cloud backdoor
- [ ] Alert SOC: cloud persistence established — on-prem wipe insufficient
- [ ] Revoke `svc-monitoring` OAuth tokens immediately

---

## Phase 3 — Triage | T+15min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | Azure AD Admin Review |
| Service Principal Age | Created 4 hours ago |
| Activity Since Creation | 3 API calls already made: `GET /users`, `GET /groups`, `GET /conditionalAccessPolicies` |
| Exfiltrated Data | Azure AD user list (all accounts), group memberships, Conditional Access rules |
| Certificate | Self-signed cert uploaded — actor holds private key externally |
| Legitimate SP Confusion | SP name mimics Microsoft 365 Monitoring — intentional masquerading (T1036) |

### Expected Actions — Human

- [ ] Verify Service Principal is unauthorized — compare against approved app registry
- [ ] Check activity log — what data has already been accessed?
- [ ] Revoke all credentials on Service Principal immediately
- [ ] Identify self-signed certificate and block it from Azure AD
- [ ] Check if actor used API to enumerate Conditional Access Policies — bypass preparation

---

## Phase 4 — Cloud-Wide Audit | T+40min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | Azure AD Audit — Extended Search |
| Additional Findings | 2 more unauthorized Service Principals found — created over past 5 days |
| SP-2 | `AzureHealthMonitor` — `Mail.Read` and `Files.ReadWrite.All` permissions |
| SP-3 | `M365DiagnosticHelper` — `User.ReadWrite.All` and `RoleManagement.ReadWrite.Directory` |
| ADFS Impact | Azure AD Connect was active — domain admin hashes in cloud tenant |
| Golden SAML Risk | ADFS token-signing cert may have been exfiltrated for cloud token forgery (T1606.002) |

### Expected Actions — Human

- [ ] Audit ALL Service Principals in Azure AD tenant — enumerate unauthorized apps
- [ ] Revoke all three unauthorized Service Principals
- [ ] Check ADFS token-signing certificate — revoke and re-issue if compromise suspected
- [ ] Review `Mail.Read` Service Principal — determine if emails were accessed
- [ ] Enable Conditional Access: MFA required for all privileged operations

---

## Phase 5 — Cloud Hardening | T+120min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | SOC Lead — Cloud Remediation |
| Azure AD Connect | Was enabled — domain-to-cloud sync allowed cross-boundary persistence |
| Recommendation | Implement Privileged Identity Management (PIM) for all Azure roles |

### Expected Actions — Human

- [ ] Disable Azure AD Connect until on-prem domain is fully clean
- [ ] Enable PIM — require approval and justification for admin role activation
- [ ] Enable continuous access evaluation for all cloud sessions
- [ ] Monitor for re-registration of Service Principals with similar names
- [ ] Establish cloud-specific SIEM alerting for all SP creation events (regardless of permissions)

---

## References

- [MITRE T1098.001 — Additional Cloud Credentials](https://attack.mitre.org/techniques/T1098/001/)
- [MITRE ATT&CK Campaign C0024](https://attack.mitre.org/campaigns/C0024/)
- [Microsoft: Detecting SolarWinds Service Principal abuse](https://www.microsoft.com/en-us/security/blog/2020/12/28/using-microsoft-365-defender-to-coordinate-protection-against-solorigate/)
- [CISA Alert AA21-008A — Azure Cloud Compromise via SolarWinds](https://www.cisa.gov/uscert/ncas/alerts/aa21-008a)
- Source Bundle: `apt29-solarwinds-stix-bundle.json` — attack-pattern T1098.001, relationship r015

> **Provenance:** Service Principal backdoor technique, cloud persistence method, actor attribution, TTPs → ✅ APT29 STIX Bundle | Specific SP names, API call details, three-SP discovery, PIM recommendations → 🤖 LLM (based on bundle data)

---

## Threat Scoring

| Metric | Value |
|--------|-------|
| **Threat Score** | 96 / 100 |
| **Severity** | CRITICAL |
| **Incident Priority** | P1 — Critical / Cloud Compromise |
| **Response SLA** | Immediate |
| **Confidence** | 92% — HIGH (hard-linked STIX) |
| **Threat Actor Attribution** | APT29 / NOBELIUM / SVR Russia |
| **Score Factors** | Cloud persistence surviving on-prem remediation: +35 · 3 backdoors found: +25 · Nation-state: +20 · ADFS + Golden SAML risk: +16 |
