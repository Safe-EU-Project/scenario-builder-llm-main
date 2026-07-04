# SCN-APT29-015: Obfuscated C2 Traffic — BEACON HTTP Masquerading as Legitimate Traffic

## Description

Network traffic analysis reveals that Cobalt Strike BEACON's C2 communications were deliberately configured by APT29 to masquerade as legitimate web traffic to well-known CDN and update services. BEACON used a custom malleable C2 profile that mimicked Amazon CloudFront update traffic — normal-looking User-Agent strings, standard HTTP headers, and responses shaped like legitimate web content. The payload was embedded in Base64-encoded values within standard HTTP headers. This is T1027 (Obfuscated Files or Information) combined with T1071.001 (Application Layer Protocol: Web Protocols). The technique was the reason BEACON's C2 traffic was not flagged by network DLP or IDS for 3 days. Attribution: APT29 / NOBELIUM / SVR Russia, confidence 85%.

---

## Phase 1 — Detection | T+0

### Inject

| Field | Value |
|-------|-------|
| Alert Source | Network Threat Hunting — PCAP Analysis |
| Alert Type | HTTP traffic pattern anomaly — periodic beaconing interval |
| Destination | `13.59.205.66` — APT29 C2 IP |
| Beacon Interval | Every 4 hours ±12 min jitter |
| HTTP Method | GET and POST to `/favicon.ico` and `/updates/check` |
| User-Agent | `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 — CloudFront` |
| Encoding | C2 response encoded in HTTP Cookie values — Base64 |
| Timestamp | 2024-05-07 02:00:00 UTC (first detected via hunt) |
| Severity | HIGH |

### Expected Actions — System

- [ ] No automated alert — IDS considered traffic legitimate (HTTP pattern match)
- [ ] Detection only via manual threat hunt — periodic beaconing pattern analysis
- [ ] After hunt identifies: SIEM rule created and backfilled to find historical traffic

---

## Phase 2 — Alert | T+30min (Hunt Finding)

### Inject

| Field | Value |
|-------|-------|
| Alert Source | Threat Hunt Team |
| Finding | Cobalt Strike malleable C2 profile — mimics CloudFront CDN traffic |
| MITRE T1027 | Obfuscated payload in HTTP Cookie headers — Base64 encoded commands |
| MITRE T1071.001 | Application layer (HTTP) C2 — bypasses L3/L4 firewall rules |
| Profile Signature | URI paths, User-Agent, header ordering — matches known APT29 BEACON profile |
| Traffic Volume | 4.2 MB over 3 days — low-and-slow to avoid volume alerts |
| IDS Status | 0 IDS alerts — profile evaded signature detection |

### Expected Actions — System

- [ ] Threat hunt team reports finding — create SIEM detection rule immediately
- [ ] Backfill: apply new rule to 30-day log history — find all C2 sessions
- [ ] Block destination IP at perimeter firewall

---

## Phase 3 — Traffic Analysis | T+60min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | Network Analysis Team — Full PCAP Review |
| C2 Sessions Found | 18 sessions over 3 days — beaconing every ~4 hours |
| Commands Sent by Actor | Session 1: `whoami /all` · Session 3: `net view /domain` · Session 7: AdFind exec |
| Data Returned | Domain enumeration results, user list, file share contents (compressed, sent as HTTP POST body) |
| Jitter | ±12 min randomization — prevents exact-interval detection |
| Second C2 IP | `54.193.127.66` — used as backup C2 (same malleable profile) |

### Expected Actions — Human

- [ ] Reconstruct C2 sessions — extract actor commands from HTTP sessions (18 sessions)
- [ ] Build timeline of actor activity — what was done in each C2 session
- [ ] Identify data returned to actor — what was exfiltrated through C2 channel
- [ ] Analyze jitter: verify ±12 min matches known APT29 BEACON configuration

---

## Phase 4 — Detection Gap Analysis | T+90min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | Security Architecture Review |
| Gap 1 | IDS rule set relies on payload signatures — Base64-obfuscated BEACON evaded |
| Gap 2 | HTTP traffic to port 443 from internal servers not logged — TLS inspection not deployed |
| Gap 3 | Destination IP reputation blocking was not in place (IP was clean before APT29 use) |
| Gap 4 | No beaconing interval detection rule in SIEM |

### Expected Actions — Human

- [ ] Understand: signature-based IDS is insufficient for malleable C2 profiles
- [ ] Deploy TLS inspection for server-originated HTTPS traffic
- [ ] Add SIEM rule: periodic connection to single external IP from server = alert
- [ ] Implement DNS allowlisting — server should only talk to known CDNs, not arbitrary AWS IPs
- [ ] Consider: JA3/JA3S fingerprinting to detect Cobalt Strike TLS profiles

---

## Phase 5 — Hardening | T+120min

### Inject

| Field | Value |
|-------|-------|
| Alert Source | SOC Lead — Prevention |
| BEACON C2 Profile | Extracted from memory dump — custom malleable profile recovered |
| Sharing | Profile shared with threat intel community for detection signature development |

### Expected Actions — Human

- [ ] Share extracted BEACON malleable C2 profile with ISAC / threat intel partners
- [ ] Create Suricata/Snort rule for this specific HTTP header pattern
- [ ] Add JA3 fingerprint for this BEACON configuration to IDS
- [ ] Enforce server egress via proxy — servers should not directly reach internet
- [ ] Quarterly threat hunting exercise: beaconing interval analysis on all egress traffic

---

## References

- [MITRE T1027 — Obfuscated Files or Information](https://attack.mitre.org/techniques/T1027/)
- [MITRE T1071.001 — Application Layer Protocol: Web Protocols](https://attack.mitre.org/techniques/T1071/001/)
- [MITRE S0154 — Cobalt Strike BEACON](https://attack.mitre.org/software/S0154/)
- [Cobalt Strike Malleable C2 Profiles](https://github.com/Cobalt-Strike/Malleable-C2-Profiles)
- [MITRE ATT&CK Campaign C0024](https://attack.mitre.org/campaigns/C0024/)
- Source Bundle: `apt29-solarwinds-stix-bundle.json` — attack-pattern T1027, T1071.001, malware s0154 (BEACON), relationship r025

> **Provenance:** Obfuscation technique, BEACON C2, HTTP masquerade, actor attribution → ✅ APT29 STIX Bundle | HTTP profile details, Cookie encoding, 18 sessions, CloudFront masquerade, JA3 recommendations → 🤖 LLM (based on bundle data)

---

## Threat Scoring

| Metric | Value |
|--------|-------|
| **Threat Score** | 86 / 100 |
| **Severity** | HIGH — Stealth C2 |
| **Incident Priority** | P1 — Critical |
| **Response SLA** | Immediate |
| **Confidence** | 85% — HIGH (hard-linked STIX) |
| **Threat Actor Attribution** | APT29 / NOBELIUM / SVR Russia |
| **Score Factors** | IDS/IPS complete bypass: +30 · 3-day undetected C2: +25 · Nation-state: +20 · Low-volume evasion: +11 |
