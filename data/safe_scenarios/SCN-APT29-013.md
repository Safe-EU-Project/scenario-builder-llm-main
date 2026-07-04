# SCN-APT29-013: Code Signing Bypass — SUNBURST Malicious DLL with Valid Certificate

## Description

The SUNBURST backdoor DLL (`SolarWinds.Orion.Core.BusinessLayer.dll`) was compiled with a valid code signing certificate issued to SolarWinds Corporation. APT29 / NOBELIUM compromised the SolarWinds software build pipeline (T1195.002 — Supply Chain Compromise) and injected malicious code into a legitimate DLL before it was signed with SolarWinds' own certificate. This is T1553.002 — Subvert Trust Controls: Code Signing. Because the DLL carries a trusted digital signature from a legitimate software vendor, Windows SmartScreen, most AV engines, and EDR file-based detection bypassed it entirely. The signed certificate was the primary reason SUNBURST evaded detection for 14+ months in real-world incidents. Attribution: APT29 / NOBELIUM / SVR Russia, confidence 100%.

---

## Phase 1 — Detection | T+0

### Inject

| Field | Value |
|-------|-------|
| Alert Source | Threat Hunt Team — Retrospective Analysis |
| Finding | SUNBURST DLL has valid SolarWinds digital signature — legitimate cert |
| Binary | `SolarWinds.Orion.Core.BusinessLayer.dll` |
| Signer | `SolarWinds Corporation` — verified valid certificate |
| Certificate Issuer | DigiCert SHA2 Assured ID Code Signing CA |
| Certificate Thumbprint | `47d92d49e6f73f488121de7da4653bf` |
| Current AV Status | ZERO detections on file (AV bypassed by valid signature) |
| Severity | CRITICAL — Detection Bypassed |

### Expected Actions — System

- [ ] No automated alert — AV/EDR trusted the signed binary
- [ ] Detection only possible via: behavior monitoring, threat hunting, or IOC feed matching on file hash
- [ ] SIEM receives alert only after manual hash submitted to correlation rule

---

## Phase 2 — Alert | T+10min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | SIEM — Manual Threat Hunt Rule |
| Rule Name | `APT29_SUNBURST_HASH_MATCH` |
| Matched Hash | MD5: `b91ce2fa41029f6955bff20079468448` |
| Matched Hash | SHA-256: `ce77d116a074dab7a22a0fd4f2c1ab475f16eec42e1ded3c0b0aa8211fe858d6` |
| IOC Source | CISA AA20-352A IOC feed — manually loaded |
| Signature Status | VALID — signed with real SolarWinds cert |
| File Location | `C:\Program Files (x86)\SolarWinds\Orion\SolarWinds.Orion.Core.BusinessLayer.dll` |

### Expected Actions — System

- [ ] SIEM fires alert — hash matches SUNBURST IOC despite valid signature
- [ ] Alert SOC: valid-signed DLL flagged as malware — unusual, critical
- [ ] Note: this detection ONLY worked because IOC hash was manually loaded

---

## Phase 3 — Triage | T+15min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | Analyst Review — Code Signing Investigation |
| DLL Version | `2020.2.0.0` — in affected build range |
| Legitimate Version | `2020.2.1.0` — clean version available |
| Code Comparison | 4,002 lines of malicious code injected into legitimate DLL |
| Injection Method | SUNBURST code inserted into `OrionImprovementBusinessLayer.Initialize()` method |
| Build Pipeline Attack | Injected at compile time — binary signed AFTER injection |
| Detection Challenge | Binary is IDENTICAL in all metadata except hash — same file name, same version string |

### Expected Actions — Human

- [ ] Understand: AV bypassed because SIGNATURE is valid — code signing is trusted
- [ ] Verify DLL hash against known-good hash from clean 2020.2.1.0 build
- [ ] Do NOT trust signature alone — hash verification is required
- [ ] Escalate: supply chain compromise — ALL systems running this version are affected

---

## Phase 4 — Scope Assessment | T+30min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | IT Asset Management |
| Affected Systems | 12 servers running SolarWinds Orion `2020.2.0.0` |
| Download Source | Legitimate SolarWinds update server — all downloads were trojanized |
| Detection Gap | This DLL was deployed for 8 months before detection |
| Scope Implication | All 12 servers had active SUNBURST, all sent DNS beacons |
| IOC Source | Hash-based detection only — signature detection was useless |

### Expected Actions — Human

- [ ] Identify all systems running SolarWinds `2020.2.0.0` — fleet-wide hash scan
- [ ] Confirm 12 servers affected — each is a potential SUNBURST host
- [ ] Understand: 8-month exposure window — scope analysis for all 12 servers
- [ ] Vendor notification: inform SolarWinds security team (they may already know)
- [ ] Certificate revocation: notify DigiCert to revoke compromised signing cert

---

## Phase 5 — Hardening | T+120min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | SOC Lead + Security Architecture |
| Lesson | Code signing is not a sufficient security control against supply chain attacks |
| Required | Hash verification of all third-party software against vendor-published checksums |

### Expected Actions — Human

- [ ] Implement software supply chain verification: verify SHA-256 hash on all software updates
- [ ] Subscribe to vendor security advisories — immediate hash-based IOC correlation
- [ ] Deploy behavioral detection rules: SUNBURST specific behaviors (named pipe, DNS DGA)
- [ ] Consider: Software Composition Analysis (SCA) for all third-party dependencies
- [ ] Update AV/EDR policy: do NOT auto-exempt from scanning based on signature alone

---

## References

- [MITRE T1553.002 — Subvert Trust Controls: Code Signing](https://attack.mitre.org/techniques/T1553/002/)
- [MITRE T1195.002 — Supply Chain Compromise](https://attack.mitre.org/techniques/T1195/002/)
- [MITRE S0559 — SUNBURST](https://attack.mitre.org/software/S0559/)
- [FireEye — SUNBURST supply chain analysis](https://cloud.google.com/blog/topics/threat-intelligence/evasive-attacker-leverages-solarwinds-supply-chain-compromises-with-sunburst-backdoor)
- Source Bundle: `apt29-solarwinds-stix-bundle.json` — attack-pattern T1553.002, indicator hash objects, relationship r001

> **Provenance:** Code signing technique, DLL hash, SolarWinds supply chain compromise, actor attribution → ✅ APT29 STIX Bundle | Specific code injection details, 4,002 lines, injected method name, 8-month timeline → 🤖 LLM (based on bundle data)

---

## Threat Scoring

| Metric | Value |
|--------|-------|
| **Threat Score** | 97 / 100 |
| **Severity** | CRITICAL — Supply Chain |
| **Incident Priority** | P1 — Critical |
| **Response SLA** | Immediate — Fleet-Wide |
| **Confidence** | 100% — CONFIRMED (hard-linked STIX) |
| **Threat Actor Attribution** | APT29 / NOBELIUM / SVR Russia |
| **Score Factors** | Signed malware bypassed AV: +35 · 8-month exposure: +25 · Nation-state: +20 · 12 servers affected: +17 |
