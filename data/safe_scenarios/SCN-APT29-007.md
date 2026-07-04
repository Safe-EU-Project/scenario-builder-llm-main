# SCN-APT29-007: DCSync Attack — APT29 Credential Extraction from Domain Controller

## Description

Domain Controller security event logs show Event ID 4662 — an object access event on the `msDS-AllowedToDelegateTo` attribute, combined with Event ID 4662 for directory replication rights (`DS-Replication-Get-Changes-All`). APT29 / NOBELIUM executed a DCSync attack using Cobalt Strike BEACON after establishing lateral movement to the Domain Controller. DCSync mimics normal domain replication to extract all NTLM hashes and Kerberos keys from Active Directory — without running code directly on the DC. This is T1003.006 OS Credential Dumping: DCSync. With all domain hashes, APT29 can forge Golden Tickets, perform pass-the-hash across the entire domain, or create persistent domain admin accounts. Attribution: APT29 / NOBELIUM / SVR Russia, confidence 95%.

---

## Phase 1 — Detection | T+0

### Inject

| Field | Value |
|-------|-------|
| Alert Source | SIEM — Domain Controller Event Logs |
| Event ID | `4662` — Directory Service Access |
| Property | `{1131f6aa-9c07-11d1-f79f-00c04fc2dcd2}` (DS-Replication-Get-Changes-All) |
| Source Account | `svc-monitoring` (service account) |
| Source Host | `SRV-ORION-01` (10.10.5.22) |
| Target | `DC-01` (Active Directory) |
| Timestamp | 2024-05-07 02:31:04 UTC |
| Severity | CRITICAL |

### Expected Actions — System

- [ ] SIEM alert — replication rights accessed from non-DC host
- [ ] Alert: DCSync from `SRV-ORION-01` — not a Domain Controller
- [ ] Automatic P1 incident ticket created

---

## Phase 2 — Alert | T+3min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | SIEM Correlation |
| Rule Name | `APT29_DCSYNC_REPLICATION_ACCESS` |
| MITRE Technique | T1003.006 — DCSync |
| Requesting Host | `SRV-ORION-01` — NOT a Domain Controller |
| Account Used | `svc-monitoring` — legitimate service account (compromised) |
| BEACON Active | YES — Cobalt Strike BEACON confirmed on SRV-ORION-01 |
| Duration | ~8 minutes of replication activity |
| Estimated Hashes | All domain account NTLM hashes extracted |

### Expected Actions — System

- [ ] SIEM fires DCSync alert — replication from non-DC source
- [ ] Escalate to SOC: all domain credentials potentially compromised
- [ ] Quarantine source host

---

## Phase 3 — Triage | T+10min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | Analyst Review — AD Logs |
| Account Used | `svc-monitoring` — service account with replication rights |
| Rights Origin | Replication rights granted to monitoring account for legitimate sync — misconfiguration |
| BEACON Method | BEACON executed `lsadump::dcsync` (Mimikatz module) in memory |
| Accounts Dumped | Estimated ALL — including `krbtgt` account |
| Impact | `krbtgt` hash extracted → Golden Ticket forgery possible |
| Previous Event | AdFind enumeration 4 days prior — actor knew service account existed |

### Expected Actions — Human

- [ ] Confirm `svc-monitoring` has replication rights — this is the attack vector
- [ ] Verify BEACON used Mimikatz DCSync — check memory artifacts
- [ ] CRITICAL: `krbtgt` account extracted — must reset twice (active + RODC)
- [ ] Check if other accounts have unnecessary replication rights

---

## Phase 4 — Impact Assessment | T+30min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | AD Audit |
| Accounts at Risk | ALL domain accounts — NTLM hashes extracted |
| Highest Risk | `krbtgt` (Golden Ticket), all domain admin accounts |
| Golden Ticket Risk | APT29 can create valid Kerberos tickets for any domain user indefinitely |
| Pass-the-Hash Risk | All NTLM hashes — actor can authenticate anywhere in domain |
| Cloud Sync | Azure AD Connect syncs domain hashes — cloud accounts also at risk |
| Timeline for Attacker | Actor has had hashes for 0 hours — immediate action required |

### Expected Actions — Human

- [ ] Initiate emergency password reset for ALL domain accounts (prioritize DA)
- [ ] Reset `krbtgt` password TWICE (24 hours apart to invalidate all tickets)
- [ ] Check Azure AD Connect — confirm cloud sync, reset cloud accounts too
- [ ] Remove replication rights from all non-DC service accounts immediately
- [ ] Consider full domain-level reset protocol (Active Directory Forest Recovery)

---

## Phase 5 — Recovery | T+90min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | SOC Lead — Recovery Phase |
| Scope | Full domain compromise confirmed |
| Azure Risk | ADFS signing cert may have been extracted — Golden SAML risk (T1606.002) |
| Cloud Accounts | Check Azure AD Service Principals for unauthorized entries (T1098.001) |
| Forensics | Preserve event logs and BEACON memory before reimaging |

### Expected Actions — Human

- [ ] Preserve DC event logs in secure offline storage
- [ ] Memory dump of BEACON on SRV-ORION-01 before containment
- [ ] Notify legal and external incident response (nation-state attacker)
- [ ] Begin full domain recovery procedure — assume all credentials burned
- [ ] External communication: clients, partners if data accessed (GDPR)

---

## References

- [MITRE T1003.006 — DCSync](https://attack.mitre.org/techniques/T1003/006/)
- [MITRE S0154 — Cobalt Strike BEACON](https://attack.mitre.org/software/S0154/)
- [Microsoft Event ID 4662 — Directory Service Access](https://docs.microsoft.com/en-us/windows/security/threat-protection/auditing/event-4662)
- [MITRE ATT&CK Campaign C0024](https://attack.mitre.org/campaigns/C0024/)
- Source Bundle: `apt29-solarwinds-stix-bundle.json` — attack-pattern T1003.006, relationship r011

> **Provenance:** DCSync technique, BEACON use, AdFind pre-enumeration, actor attribution, TTPs → ✅ APT29 STIX Bundle | Event IDs, replication rights misconfiguration, krbtgt detail, recovery steps → 🤖 LLM (based on bundle data)

---

## Threat Scoring

| Metric | Value |
|--------|-------|
| **Threat Score** | 98 / 100 |
| **Severity** | CRITICAL |
| **Incident Priority** | P1 — Critical / Domain-Wide |
| **Response SLA** | Immediate — Mass Credential Reset Required |
| **Confidence** | 95% — HIGH (hard-linked STIX) |
| **Threat Actor Attribution** | APT29 / NOBELIUM / SVR Russia |
| **Score Factors** | Full domain credential compromise: +40 · krbtgt extracted: +25 · Nation-state: +20 · Cloud sync risk: +13 |
