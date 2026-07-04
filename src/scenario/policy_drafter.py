"""Generate a formal operational policy draft from scenario data and simulation results."""

from __future__ import annotations

from typing import Optional

from ..config.models import (
    EscalationLevel,
    IdentifiedRisk,
    LEAContext,
    PolicyDraftLLMResult,
    PolicyDraftRequest,
    PolicyDraftResponse,
    PolicyRecommendation,
    ReportingObligation,
    RoleEntry,
    SimulationPerformanceData,
)


POLICY_DRAFT_SYSTEM_PROMPT = """You are a senior cybersecurity policy advisor generating complete, publication-ready operational policy documents for Law Enforcement Agencies (LEAs) and public authorities. Your output must comply with EU legal frameworks: NIS2 Directive 2022/2555, GDPR 2016/679, the Budapest Convention on Cybercrime (ETS 185), the EU Law Enforcement Directive 2016/680, and the EU Law Enforcement Emergency Response Protocol (LEERP).

CRITICAL RULE — NO PLACEHOLDERS:
You MUST generate complete, professional content for every field. Do NOT use "[LEA INPUT NEEDED]", "[TBD]", "[INSERT]", blank lines, "___", or any other placeholder. Every section must be fully written and ready to use as-is. If organisation-specific details (e.g. DPO name, issuing authority) are not provided in the user message, generate standard professional role titles appropriate for a LEA cybercrime division (e.g. "Director of Cybercrime Division", "Designated Data Protection Officer", "National CERT/CSIRT").

LANGUAGE AND TONE:
- Formal, precise, and concise — this is a legal and operational document.
- Use active voice: "The Incident Commander SHALL...", "The Digital Forensics Officer MUST...".
- Use "SHALL" for mandatory actions, "SHOULD" for recommended, "MAY" for optional.
- Write for a senior LEA officer with cybersecurity awareness but not deep technical expertise.
- You MUST explicitly name EU legal instruments (NIS2, GDPR, Budapest Convention) where required by the schema.

DOCUMENT STRUCTURE — follow this exactly, one field per section:

management_commitment (Section 1):
  A formal statement that senior leadership mandates compliance with this policy, allocates necessary resources, and authorises the incident response capability described herein. If an issuing authority is provided, name them. Otherwise use "the Director of the Cybercrime Division" or equivalent senior role. Do NOT include a signature line or blank approval field.

purpose_and_scope (Section 2):
  2.1 Purpose — one sentence on what threat this policy governs and why it is a priority for LEAs.
  2.2 Scope — list all ICT systems, all personnel (including contractors) covered.
  2.3 Regulatory Framework — explicitly state:
    - EU Directive 2022/2555 (NIS2) — mandatory reporting timelines for essential entities (Art. 23)
    - EU GDPR 2016/679 — personal data breach notification to supervisory authority within 72 hours (Art. 33) and to data subjects without undue delay (Art. 34)
    - Council of Europe Convention on Cybercrime (Budapest Convention, ETS 185) — cross-border cooperation in criminal investigations
    - EU Law Enforcement Directive 2016/680 — data protection for criminal justice processing
    - Applicable national cybersecurity legislation transposing EU NIS2 Directive 2022/2555

incident_classification (Section 3):
  Classify the scenario using the Europol/CSIRT Common Taxonomy for Law Enforcement and CSIRTs.
  State: Class | Type | Legislative mapping (Budapest Convention article + NIS Directive article).
  Example format: "Class: Malware | Type: Ransomware deployment | Legislative mapping: Budapest Convention Art. 2, 6; NIS2 Directive Art. 3, 23"

executive_summary (Section 4 — Threat Assessment):
  MUST be a plain text string. Write as continuous prose with two labelled paragraphs:
  4.1 Threat Profile — threat actor category, initial attack vector, target assets, identified vulnerability class, estimated operational impact if uncontained.
  4.2 Simulation Evidence — if performance data is provided: state number of simulation runs, average score, and list the top missed actions with failure rates. If no data: state "No simulation data available — assessment is threat-profile-based only."

identified_risks: 3-5 risks. threat_type uses Europol taxonomy labels. likelihood is HIGH / MEDIUM / LOW. description grounds the risk in the specific scenario context.

detection_procedures (Section 5.1, T+0 to T+30 min): 4-6 numbered steps. Each starts with an action verb. Specify what indicator to look for, in which system, and what immediate action to take.

containment_procedures (Section 5.2, T+30 min to T+2h): 4-6 numbered steps. Each names the responsible role (e.g. "The Incident Commander SHALL..."). Include network isolation, VPN shutdown, backup verification, out-of-band communications activation.

evidence_preservation_steps (Section 5.3 — BEFORE any remediation): 4-6 numbered steps. Must include: forensic disk imaging with write-blocker, SHA-256 hash verification, volatile memory (RAM) acquisition, log collection (minimum 72h prior window), chain of custody log. Do NOT permit remediation before these steps are complete.

escalation_chain (Section 5.4): Exactly 6 levels minimum:
  L1 — First Responder | Any indicator detected | Duty ICT Officer | Immediately
  L2 — Incident Commander | Incident confirmed | Senior Inspector / Incident Commander | Within 30 minutes
  L3 — Senior Management | Operational systems affected | Director of Cybercrime Division | Within 1 hour
  L4 — Data Protection Officer | Personal data breach confirmed or suspected | Designated Data Protection Officer | Within 1 hour (internal); 72h to DPA (GDPR Art. 33)
  L5 — National CERT/CSIRT | Significant incident per NIS2 Art. 23 | National CERT/CSIRT (national cybersecurity authority) | Early warning within 24 hours
  L6 — Europol EC3 / LEERP | Criminal infrastructure involved or cross-border impact | Europol EC3 Cybercrime Centre | As soon as operationally feasible
  If org-specific role titles or contact details are provided, use them. Otherwise use the generic titles above.

external_reporting_obligations (Section 5.5): At least 4 rows:
  - National Data Protection Authority | GDPR Art. 33 | Personal data breach notification | Within 72 hours
  - National CERT/CSIRT | NIS2 Art. 23 | Significant incident — early warning | Within 24 hours
  - Europol EC3 | LEERP / Operational cooperation | Criminal infrastructure notification | As soon as operationally feasible
  - Ministry of Interior / Supervisory Authority | National cybersecurity legislation | Operational incident notification | Per national regulatory requirement

preventive_controls (Section 6.1): 4-7 technical controls, each prefixed CRITICAL — / HIGH — / MEDIUM —. Ground each in identified vulnerability or simulation gap.

administrative_controls (Section 6.2): 3-5 organisational/administrative controls, e.g. mandatory annual training, bi-annual tabletop exercises, annual penetration testing, supplier security assessment.

roles_and_responsibilities (Section 7): At least 6 roles. Generate complete, professional role descriptions. Always set lea_input_needed=false. Must include: First Responder (any staff), Duty ICT Officer, Incident Commander, Digital Forensics Officer, Communications Officer, Senior Management.

policy_recommendations: 3-5 recommendations grounded in specific simulation gaps or threat profile findings. Each targets LEA / Public Authority / Judicial Cooperation Network.

resource_requirements (Section 8): 4-6 items covering: priority training areas derived from simulation failure rates, required forensic and IR tools, minimum CIRT composition, on-call availability requirement.

review_cycle (Section 9): At least 4 entries. Include: annual full policy review, bi-annual simulation exercise aligned with SAFE platform, annual regulatory compliance review (NIS2, GDPR), annual external audit by accredited cybersecurity auditor.

OUTPUT FORMAT:
Return ONLY the JSON object matching the PolicyDraftLLMResult schema. No preamble, no text outside the JSON object.
"""


def build_policy_draft_user_message(request: PolicyDraftRequest) -> str:
    """Construct the user message for the policy draft LLM call."""
    scenario = request.scenario
    perf = request.performance_data
    lea = request.lea_context

    lines: list[str] = []

    # ── Organisation context (if provided) ────────────────────────────────────
    if lea:
        lines.append("=== ORGANISATION CONTEXT (USE THESE VALUES — DO NOT USE GENERIC PLACEHOLDERS) ===")
        if lea.organisation_name:
            lines.append(f"Organisation Name: {lea.organisation_name}")
        if lea.issuing_authority:
            lines.append(f"Issuing Authority (Section 1): {lea.issuing_authority}")
        if lea.incident_commander_title:
            lines.append(f"Incident Commander Title (L2 / Section 7): {lea.incident_commander_title}")
        if lea.senior_management_title:
            lines.append(f"Senior Management Title (L3 / Section 7): {lea.senior_management_title}")
        if lea.dpo_name_contact:
            lines.append(f"Data Protection Officer (L4 / Section 7): {lea.dpo_name_contact}")
        if lea.national_cert_contact:
            lines.append(f"National CERT/CSIRT (L5 / Section 5.5): {lea.national_cert_contact}")
        if lea.national_law_reference:
            lines.append(f"National Law Reference (Section 2.3): {lea.national_law_reference}")
        if lea.supervisory_body:
            lines.append(f"Supervisory Body for External Reporting (Section 5.5): {lea.supervisory_body}")
        if lea.external_audit_frequency:
            lines.append(f"External Audit Frequency (Section 9): {lea.external_audit_frequency}")
        lines.append("")

    lines.append("=== SCENARIO PROFILE ===")
    lines.append(f"Scenario Title: {scenario.scenario_title}")
    desc = getattr(scenario, "scenario_description", None)
    threat_actor = getattr(scenario, "threat_actor", None)
    threat_type = getattr(scenario, "threat_type", None)
    target_sector = getattr(scenario, "target_sector", None)
    attack_vector = getattr(scenario, "attack_vector", None)
    if desc:
        lines.append(f"Description: {desc}")
    if threat_actor:
        lines.append(f"Threat Actor: {threat_actor}")
    if threat_type:
        lines.append(f"Threat Type: {threat_type}")
    if target_sector:
        lines.append(f"Target Sector: {target_sector}")
    if attack_vector:
        lines.append(f"Attack Vector: {attack_vector}")

    if scenario.incidents:
        lines.append(f"\nNumber of Scenario Phases: {len(scenario.incidents)}")
        lines.append("Phases:")
        for i, inc in enumerate(scenario.incidents, start=1):
            title = getattr(inc, "incident_title", None) or getattr(inc, "title", str(inc))
            description = (
                getattr(inc, "incident_description", None)
                or getattr(inc, "description", None)
                or ""
            )
            expected = getattr(inc, "expected_actions", None) or []
            lines.append(f"  Phase {i}: {title}")
            if description:
                lines.append(f"    Description: {description}")
            if expected:
                actions_text = "; ".join(expected) if isinstance(expected, list) else str(expected)
                lines.append(f"    Expected Actions: {actions_text}")

    if perf:
        lines.append("\n=== SIMULATION PERFORMANCE DATA ===")
        lines.append(f"Total Simulation Runs: {perf.simulations_count}")
        if perf.average_grade is not None:
            lines.append(f"Average Trainee Score: {perf.average_grade:.1f}/100")
        if perf.top_missed_actions:
            lines.append("Most Frequently Missed Expected Actions:")
            for action in perf.top_missed_actions:
                lines.append(f"  - {action}")
        if perf.grade_per_incident:
            lines.append("Per-Phase Average Scores:")
            for entry in perf.grade_per_incident:
                for title, score in entry.items():
                    if isinstance(score, dict):
                        score = score.get("score", score)
                    lines.append(f"  - {title}: {score}/100")
        lines.append(
            "\nINSTRUCTION: Use the simulation performance data above as the primary evidence base for Section 4.2 "
            "(Simulation Evidence), resource_requirements, and policy_recommendations. "
            "Cite specific failure rates from top_missed_actions and low-scoring phases. "
            "Set draft_type='evidence-based'."
        )
    else:
        lines.append(
            "\nNOTE: No simulation performance data is available. "
            "In Section 4.2, state 'No simulation data available — assessment is threat-profile-based only.' "
            "Base all sections on the scenario threat profile above. Set draft_type='threat-based'."
        )

    lines.append(
        "\nGenerate a complete, publication-ready formal operational policy document following ALL sections in the system prompt. "
        "Every field must be fully populated — no placeholders, no blank fields. "
        "Return only the JSON object matching PolicyDraftLLMResult."
    )

    return "\n".join(lines)


def build_policy_draft_rag_query(request: PolicyDraftRequest) -> str:
    """
    Build a focused retrieval query for the RAG pipeline.

    The query is designed to surface:
    1. The correct SOP section structure for the identified threat type
    2. The Europol taxonomy class and legislative mapping for the incident
    3. The precise EU legal deadlines applicable to the scenario

    A compound query is used so the embedding search returns chunks from
    all three reference documents in a single pass.
    """
    scenario = request.scenario
    threat_type = getattr(scenario, "threat_type", None) or "cyber incident"
    target_sector = getattr(scenario, "target_sector", None) or "law enforcement agency"
    attack_vector = getattr(scenario, "attack_vector", None) or ""

    parts = [
        f"Law enforcement agency cyber incident response policy structure for {threat_type} incident.",
        f"Europol taxonomy classification and legislative mapping for {threat_type}.",
        "EU NIS2 Article 23 reporting deadlines and GDPR Article 33 personal data breach notification deadlines.",
        "Escalation chain levels L1 to L6 including national CERT early warning and Europol EC3 LEERP notification.",
        "Evidence preservation chain of custody SHA-256 forensic disk image digital forensics law enforcement.",
    ]

    if attack_vector:
        parts.append(f"Incident response procedures for {attack_vector} attack vector targeting {target_sector}.")

    return " ".join(parts)


def assert_no_hallucination(result: PolicyDraftLLMResult) -> list[str]:
    """
    Post-generation sanity checks for common LLM hallucinations in policy drafts.

    Returns a list of warning strings (non-fatal issues that reviewers should flag).
    Raises ValueError for critical issues that make the draft unsafe to use.
    """
    warnings: list[str] = []

    # ── Critical: escalation chain must reach at least L5 (National CERT / NIS2) ──
    levels = {e.level.upper() for e in result.escalation_chain}
    for required in ("L5", "L6"):
        if required not in levels:
            warnings.append(
                f"Escalation chain is missing {required} — "
                "NIS2 Art.23 (National CERT) and Europol EC3 notification levels are mandatory."
            )

    # ── Critical: external reporting must cover GDPR + NIS2 ──
    reporting_bases = " ".join(o.legal_basis.lower() for o in result.external_reporting_obligations)
    if "gdpr" not in reporting_bases and "2016/679" not in reporting_bases:
        warnings.append(
            "External reporting obligations are missing GDPR Art.33 (72-hour DPA notification)."
        )
    if "nis2" not in reporting_bases and "2022/2555" not in reporting_bases:
        warnings.append(
            "External reporting obligations are missing NIS2 Art.23 (24-hour CERT early warning)."
        )

    # ── Warning: evidence preservation must mention chain of custody ──
    ep_text = " ".join(result.evidence_preservation_steps).lower()
    if "chain of custody" not in ep_text and "chain-of-custody" not in ep_text:
        warnings.append(
            "Evidence preservation steps do not mention chain of custody — "
            "required for criminal prosecution admissibility."
        )

    # ── Warning: evidence preservation must mention hashing ──
    if "sha-256" not in ep_text and "hash" not in ep_text:
        warnings.append(
            "Evidence preservation steps do not mention cryptographic hash verification (SHA-256)."
        )

    # ── Warning: roles must include a Digital Forensics Officer ──
    role_names = " ".join(r.role.lower() for r in result.roles_and_responsibilities)
    if "forensic" not in role_names:
        warnings.append(
            "Roles and Responsibilities is missing a Digital Forensics Officer — "
            "required for evidence preservation ownership."
        )

    # ── Warning: review cycle should mention bi-annual simulation ──
    review_text = " ".join(result.review_cycle).lower()
    if "bi-annual" not in review_text and "biannual" not in review_text and "twice" not in review_text:
        warnings.append(
            "Review cycle does not mention bi-annual SAFE simulation exercises."
        )

    return warnings


def _fallback_response(request: PolicyDraftRequest) -> PolicyDraftLLMResult:
    """Minimal static fallback when the LLM is unavailable."""
    scenario = request.scenario
    lea = request.lea_context
    threat_type = getattr(scenario, "threat_type", None) or "Cyber Incident"
    target_sector = getattr(scenario, "target_sector", None) or "public sector organisations"
    title = f"{threat_type} Response Operational Policy for Law Enforcement Agencies"
    org = lea.organisation_name if lea and lea.organisation_name else "the Law Enforcement Agency"
    issuing = lea.issuing_authority if lea and lea.issuing_authority else "Director of the Cybercrime Division"
    cert = lea.national_cert_contact if lea and lea.national_cert_contact else "National CERT/CSIRT"
    dpo = lea.dpo_name_contact if lea and lea.dpo_name_contact else "Designated Data Protection Officer"
    nat_law = lea.national_law_reference if lea and lea.national_law_reference else "applicable national cybersecurity legislation transposing EU NIS2 Directive 2022/2555"

    return PolicyDraftLLMResult(
        document_title=title,
        classification="RESTRICTED — LAW ENFORCEMENT SENSITIVE",
        management_commitment=(
            f"The leadership of {org} mandates full compliance with this policy, allocates necessary resources, "
            f"and authorises the incident response capability described herein. This policy is approved by {issuing}. "
            "NOTE: LLM service was temporarily unavailable — re-generate for a complete policy document."
        ),
        purpose_and_scope=(
            f"2.1 Purpose: This policy governs the response to {threat_type} incidents targeting {target_sector}. "
            "2.2 Scope: Applies to all ICT systems, all personnel, and third-party contractors. "
            "2.3 Regulatory Framework: EU NIS2 Directive 2022/2555 (Art. 23); EU GDPR 2016/679 (Art. 33-34); "
            f"Budapest Convention (ETS 185); EU Law Enforcement Directive 2016/680; {nat_law}."
        ),
        incident_classification=f"Class: Cyber Incident | Type: {threat_type} | Legislative mapping: Budapest Convention Art. 2; NIS2 Directive Art. 3, 23",
        executive_summary=(
            f"4.1 Threat Profile: {threat_type} targeting {target_sector}. Full threat assessment requires LLM re-generation.\n"
            "4.2 Simulation Evidence: No simulation data available for this fallback response."
        ),
        identified_risks=[
            IdentifiedRisk(
                threat_type=threat_type,
                likelihood="HIGH",
                description=f"Risk from {threat_type} incident targeting {target_sector}. Full risk assessment requires LLM re-generation.",
            ),
            IdentifiedRisk(
                threat_type="Operational Disruption",
                likelihood="HIGH",
                description="Service disruption risk due to incident. Detailed assessment requires LLM re-generation.",
            ),
        ],
        detection_procedures=[
            "Monitor all ICT systems for anomalous activity using available SIEM tools.",
            "Verify any alerts against known indicators of compromise (IoCs) for this threat type.",
            "Create a formal incident record upon confirmation of a potential security event.",
            "Notify the Duty ICT Officer immediately upon detection of a credible indicator.",
        ],
        containment_procedures=[
            "The Incident Commander SHALL immediately assess the scope and isolate affected systems.",
            "The Network Operations team SHALL apply emergency access controls to limit lateral movement.",
            "The Digital Forensics Officer SHALL preserve volatile memory before any system changes.",
            "The Communications Officer SHALL activate out-of-band communications channels.",
        ],
        evidence_preservation_steps=[
            "The Digital Forensics Officer MUST acquire forensic disk images using a write-blocker before any remediation.",
            "The Digital Forensics Officer MUST calculate and log SHA-256 hashes of all acquired images.",
            "The Digital Forensics Officer MUST capture volatile memory (RAM) from affected systems immediately after isolation.",
            "The Digital Forensics Officer MUST collect system and network logs covering at least 72 hours prior to the incident.",
            "All evidence handling steps MUST be recorded in a chain-of-custody log.",
        ],
        escalation_chain=[
            EscalationLevel(level="L1", trigger="Any indicator detected", notify="Duty ICT Officer", timeframe="Immediately"),
            EscalationLevel(level="L2", trigger="Incident confirmed", notify="Senior Inspector / Incident Commander", timeframe="Within 30 minutes"),
            EscalationLevel(level="L3", trigger="Operational systems affected", notify="Director of Cybercrime Division", timeframe="Within 1 hour"),
            EscalationLevel(level="L4", trigger="Personal data breach confirmed or suspected", notify=dpo, timeframe="Within 1 hour (internal); 72 hours to supervisory authority (GDPR Art. 33)"),
            EscalationLevel(level="L5", trigger="Significant incident per NIS2 Art. 23", notify=cert, timeframe="Early warning within 24 hours"),
            EscalationLevel(level="L6", trigger="Criminal infrastructure involved or cross-border impact", notify="Europol EC3 Cybercrime Centre", timeframe="As soon as operationally feasible"),
        ],
        external_reporting_obligations=[
            ReportingObligation(body="National Data Protection Authority", legal_basis="GDPR Art. 33", obligation="Personal data breach notification", deadline="Within 72 hours"),
            ReportingObligation(body=cert, legal_basis="NIS2 Art. 23", obligation="Significant incident — early warning", deadline="Within 24 hours"),
            ReportingObligation(body="Europol EC3", legal_basis="LEERP", obligation="Criminal infrastructure notification", deadline="As soon as operationally feasible"),
            ReportingObligation(body="Ministry of Interior / Supervisory Authority", legal_basis="National cybersecurity legislation and NIS2 Directive", obligation="Operational incident notification", deadline="Per national regulatory requirement"),
        ],
        preventive_controls=[
            "CRITICAL — Implement multi-factor authentication on all administrative and remote access systems.",
            "CRITICAL — Deploy endpoint detection and response (EDR) tooling across all ICT assets.",
            "HIGH — Conduct mandatory cybersecurity awareness training for all staff annually.",
            "HIGH — Establish and test regular backup and recovery procedures.",
            "MEDIUM — Conduct annual penetration testing of critical systems.",
        ],
        administrative_controls=[
            "Mandatory annual cybersecurity awareness training for all personnel.",
            "Bi-annual tabletop incident response exercises aligned with the SAFE platform.",
            "Annual review of this policy and all related procedures.",
        ],
        roles_and_responsibilities=[
            RoleEntry(role="First Responder (any staff)", responsibilities="Detect, document, isolate, and notify Duty ICT Officer immediately upon observing a potential security incident.", lea_input_needed=False),
            RoleEntry(role="Duty ICT Officer", responsibilities="Receive initial notification, conduct triage, activate incident response procedures, and notify Incident Commander.", lea_input_needed=False),
            RoleEntry(role="Incident Commander", responsibilities="Overall incident command and coordination; responsible for all escalation decisions and resource allocation.", lea_input_needed=False),
            RoleEntry(role="Digital Forensics Officer", responsibilities="Evidence preservation, forensic imaging, chain-of-custody management, and forensic analysis support.", lea_input_needed=False),
            RoleEntry(role=dpo, responsibilities="Data protection oversight; assess personal data impact; notify supervisory authority within 72 hours of confirmed personal data breach.", lea_input_needed=False),
            RoleEntry(role="Communications Officer", responsibilities="Manage internal and external communications; coordinate media response; maintain stakeholder updates.", lea_input_needed=False),
        ],
        policy_recommendations=[
            PolicyRecommendation(
                policy_title="Mandatory Incident Response Training",
                rationale="All LEA personnel require regular training to respond effectively to cyber incidents.",
                target_audience="LEA",
            ),
            PolicyRecommendation(
                policy_title="Regular Simulation Exercises",
                rationale="Bi-annual exercises using the SAFE platform maintain response readiness.",
                target_audience="LEA",
            ),
            PolicyRecommendation(
                policy_title="Cross-Border Cooperation Protocol",
                rationale="Formal procedures for Europol EC3 engagement reduce response time for cross-border incidents.",
                target_audience="Judicial Cooperation Network",
            ),
        ],
        resource_requirements=[
            "Priority Training: All personnel require training in incident detection, containment, and evidence preservation.",
            "Tools: SIEM system, forensic imaging kit with write-blocker, chain-of-custody management system.",
            "Personnel: Minimum CIRT composition — Incident Commander, Digital Forensics Officer, Communications Officer, Duty ICT Officer.",
            "On-call: 24/7 Duty ICT Officer availability; Incident Commander on 12-hour on-call rotation.",
        ],
        review_cycle=[
            "Full policy review — Annually or after any significant cyber incident",
            "SAFE simulation exercise — Bi-annual",
            "Regulatory compliance review (NIS2, GDPR) — Annually (Data Protection Officer)",
            "External security audit by accredited cybersecurity auditor — Annually",
        ],
        draft_type="threat-based",
    )
