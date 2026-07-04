# APT29 / SolarWinds Compromise — Complete Scenario Index

## Data Sources

| Source | Content |
|--------|---------|
| ✅ **APT29 STIX Bundle** | IOC hashes, C2 IPs, malware names, TTPs, relationships, actor attribution |
| 🌐 **Internet / Public Intel** | CISA advisories, MITRE ATT&CK, FireEye analysis, Microsoft MSRC |
| 🤖 **LLM Generated** | Phase structure, timelines, alert messages, thresholds, remediation steps |

All scenarios mark provenance at the bottom of each file.

---

## Complete Scenario List — 15 Scenarios

### Category A — IOC-Based (Hash / Domain / IP / Behavioral Artifact)

| ID | Title | IOC Type | MITRE | Threat Score |
|----|-------|----------|-------|-------------|
| [SCN-APT29-001](SCN-APT29-001.md) | SUNBURST DLL Hash Detected in SolarWinds Orion | File Hash (MD5 + SHA-256) | T1195.002 | 95/100 |
| [SCN-APT29-002](SCN-APT29-002.md) | DNS Beaconing to avsvmcloud.com | C2 Domain (DGA) | T1071.004 + T1568.002 | 93/100 |
| [SCN-APT29-004](SCN-APT29-004.md) | TEARDROP Dropper — gracious_truth.jpg in SysWOW64 | File Path + Name | T1036.005 | 96/100 |
| [SCN-APT29-005](SCN-APT29-005.md) | Outbound Connection to APT29 C2 Infrastructure | IP Address | T1071.001 | 94/100 |
| [SCN-APT29-006](SCN-APT29-006.md) | SUNBURST Single-Instance Mutex Named Pipe | Named Pipe | T1587.001 | 95/100 |

### Category B — TTP-Based (Adversary Technique / Behavior)

| ID | Title | Technique | MITRE | Threat Score |
|----|-------|-----------|-------|-------------|
| [SCN-APT29-003](SCN-APT29-003.md) | Golden SAML — ADFS Token Forgery | Cloud Auth Bypass | T1606.002 | 98/100 |
| [SCN-APT29-007](SCN-APT29-007.md) | DCSync Attack — Credential Extraction from Domain Controller | Credential Dumping | T1003.006 | 98/100 |
| [SCN-APT29-008](SCN-APT29-008.md) | Security Tool Disable via Registry | Defense Evasion | T1562.001 | 87/100 |
| [SCN-APT29-009](SCN-APT29-009.md) | Azure AD Backdoor — Unauthorized Service Principal | Cloud Persistence | T1098.001 | 96/100 |
| [SCN-APT29-010](SCN-APT29-010.md) | Remote Email Collection via Exchange PowerShell | Data Collection | T1114.002 | 90/100 |
| [SCN-APT29-011](SCN-APT29-011.md) | 7-Zip Archiving + Data Staging for Exfiltration | Collection + Staging | T1560.001 | 89/100 |
| [SCN-APT29-012](SCN-APT29-012.md) | Evidence Removal via SDelete | Anti-Forensics | T1070.004 | 82/100 |
| [SCN-APT29-013](SCN-APT29-013.md) | Code Signing Bypass — SUNBURST Signed Malicious DLL | Trust Subversion | T1553.002 | 97/100 |
| [SCN-APT29-014](SCN-APT29-014.md) | Dormant Account Lateral Movement | Credential Abuse | T1078 | 88/100 |
| [SCN-APT29-015](SCN-APT29-015.md) | Obfuscated C2 Traffic — BEACON HTTP Masquerade | Stealth C2 | T1027 + T1071.001 | 86/100 |

---

## Playbook Templates (4 Types)

Located in `playbooks/templates/`:

| Template | File | Use Case |
|----------|------|---------|
| Tabletop Exercise | [TEMPLATE-tabletop.md](playbooks/templates/TEMPLATE-tabletop.md) | Group discussion, management + SOC |
| SOC Analyst Drill | [TEMPLATE-soc-drill.md](playbooks/templates/TEMPLATE-soc-drill.md) | Individual alert-based training |
| Automated Playbook | [TEMPLATE-automated-playbook.md](playbooks/templates/TEMPLATE-automated-playbook.md) | SIEM/SOAR machine-executable |
| Detection Rule Test | [TEMPLATE-detection-rule-test.md](playbooks/templates/TEMPLATE-detection-rule-test.md) | Verify detection coverage |

## Playbook Scenarios (4 Types — SUNBURST Hash)

Located in `playbooks/scenarios/`:

| Scenario | File |
|----------|------|
| Tabletop Exercise | [SCN-APT29-TABLETOP.md](playbooks/scenarios/SCN-APT29-TABLETOP.md) |
| SOC Analyst Drill | [SCN-APT29-SOC-DRILL.md](playbooks/scenarios/SCN-APT29-SOC-DRILL.md) |
| Automated Playbook | [SCN-APT29-PLAYBOOK.md](playbooks/scenarios/SCN-APT29-PLAYBOOK.md) |
| Detection Rule Test | [SCN-APT29-DETECTION-TEST.md](playbooks/scenarios/SCN-APT29-DETECTION-TEST.md) |

---

## STIX Bundle Coverage

The 15 scenarios above cover:

- **10 IOCs** from the bundle: 2 file hashes, 1 C2 domain, 2 C2 IPs, 1 dropper file, 1 named pipe, 3 additional domains
- **15 TTPs** from the bundle: all MITRE ATT&CK techniques linked in STIX relationships
- **3 Malware families**: SUNBURST, TEARDROP, GoldMax
- **2 Tools**: Cobalt Strike BEACON, AdFind
- **1 Campaign**: SolarWinds Compromise (C0024)
- **1 Threat Actor**: APT29 / NOBELIUM / SVR Russia

---

## Scenario Structure

Each scenario follows a 5-phase incident simulation:

```
Phase 1 — Detection:      System alert fires (automated)
Phase 2 — Alert:          SIEM correlation confirms threat
Phase 3 — Triage:         Analyst investigates and confirms
Phase 4 — Investigation:  Deep analysis, scope, impact
Phase 5 — Containment/Hardening: Remediation + prevention
```

Each phase has:
- An **Inject table** with specific technical details (IOCs, timestamps, commands)
- An **Expected Actions** checklist (System automated + Human manual)

---

## Summary Presentation

`APT29_Threat_Intelligence_Playbooks.pptx` — 11-slide English PowerPoint summarizing:
- APT29 bundle analysis
- Comparison: APT1 (OpenCTI / no IOCs) vs APT29 (STIX bundle / full data)
- STIX vs LLM contributions per scenario
- 4 playbook types explained
- Full pipeline: STIX bundle → Scenario generation
