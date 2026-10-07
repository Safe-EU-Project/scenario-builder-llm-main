"""
Pydantic models for API requests and responses.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ProcessRequest(BaseModel):
    """Request model for document processing"""

    data_folder: Optional[str] = Field(
        None, description="Optional path to data folder (defaults to configured data folder)"
    )
    force_reprocess: bool = Field(
        False, description="Force reprocessing even if documents already processed"
    )


class QueryRequest(BaseModel):
    """Request model for document query"""

    query: str = Field(..., description="Search query")
    top_k: int = Field(20, description="Number of results to return")
    use_reranking: bool = Field(True, description="Apply reranking to results")
    use_hybrid: bool = Field(False, description="Use hybrid search (dense + sparse)")
    initial_k: int = Field(150, description="Initial retrieval count for reranking")
    use_advanced_reranker: bool = Field(True, description="Use advanced cross-encoder reranker")
    sector: Optional[str] = Field(
        None,
        description=(
            "Domain sector filter for RAG retrieval. "
            "One of: lea, banking, energy, health, telecom, general. "
            "If None, auto-detected from query text."
        ),
    )


class QueryResponse(BaseModel):
    """Response model for document query with LLM answer"""

    query: str = Field(..., description="Original query")
    answer: str = Field(..., description="LLM-generated answer")
    context: str = Field(..., description="Retrieved context used for answer")
    sources: List[Dict[str, Any]] = Field(..., description="Source documents")
    metadata: Dict[str, Any] = Field(..., description="Query metadata")


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    service: str
    timestamp: str
    version: str


class ProcessResponse(BaseModel):
    """Response for processing endpoint"""

    status: str = Field(..., description="Processing status")
    message: str = Field(..., description="Status message")
    documents_processed: int = Field(..., description="Number of documents processed")
    chunks_created: int = Field(..., description="Total chunks created")


class IngestScenarioRequest(BaseModel):
    """Request model for ingesting a human-reviewed scenario"""

    content: str = Field(..., description="Scenario content text")
    sector: Optional[str] = Field(
        None,
        description=(
            "Domain sector for this scenario: lea, banking, energy, health, telecom, general. "
            "Auto-detected from content if not provided."
        ),
    )


class IngestScenarioResponse(BaseModel):
    """Response model for scenario ingestion"""

    status: str = Field(..., description="Ingestion status")
    message: str = Field(..., description="Status message")
    document_id: str = Field(..., description="Generated document ID for the ingested scenario")


class ExploitPath(BaseModel):
    """
    Structured representation of the vulnerability exploitation path that leads
    from the attacker's current foothold to the next incident.

    Addresses the SAFE grant requirement (T7.4) to explain exploit paths and
    potential vulnerabilities — not just the outcome, but HOW the attacker gets there.
    """

    current_foothold: str = Field(
        ...,
        description=(
            "The access or position the attacker holds at this point in the scenario. "
            "Example: 'Domain user credentials on WORKSTATION-07' or "
            "'Read access to SWIFT message broker'"
        ),
    )
    vulnerability_exploited: str = Field(
        ...,
        description=(
            "The specific CVE, protocol weakness, misconfiguration, or human factor exploited "
            "to advance the attack. Example: 'CVE-2023-4966 (Citrix Bleed) — unauthenticated "
            "session token retrieval' or 'Lack of MFA on privileged admin account'"
        ),
    )
    lateral_movement_technique: str = Field(
        ...,
        description=(
            "MITRE ATT&CK technique ID and name used to pivot to the next target. "
            "Example: 'T1550.002 — Pass the Hash' or 'T1021.001 — Remote Desktop Protocol'"
        ),
    )
    pivot_target: str = Field(
        ...,
        description=(
            "The specific system, account, or asset being targeted in this exploitation step. "
            "Example: 'Domain Controller DC-PROD-01' or 'SWIFT Alliance Access Terminal'"
        ),
    )
    new_capability_gained: str = Field(
        ...,
        description=(
            "What the attacker achieves by successfully exploiting this path. "
            "Example: 'Domain Administrator privileges across all production servers' or "
            "'Ability to inject fraudulent SWIFT MT103 payment orders'"
        ),
    )
    containment_window: str = Field(
        ...,
        description=(
            "Estimated time window available to defenders to interrupt this exploitation path "
            "before the attacker achieves new_capability_gained. "
            "Example: '~15 minutes from first beacon' or '< 5 minutes after SWIFT session hijack'"
        ),
    )
    detection_indicators: List[str] = Field(
        default_factory=list,
        description=(
            "2-4 concrete, observable indicators of compromise (IOCs) or behavioral signals "
            "that could detect this exploitation path in progress. "
            "Example: ['Kerberos TGT request from non-standard workstation', "
            "'Outbound HTTPS to newly registered domain', 'SIEM rule: multiple failed MFA attempts']"
        ),
    )


class Incident(BaseModel):
    """Structured incident model for LLM responses"""

    # incident title
    title: str = Field(..., description="Incident title")
    # hour of the incident
    message_timestamp: str = Field(..., description="Hour of the incident")
    # incident description
    description: str = Field(..., description="Incident description")
    # optional inject information
    inject: Optional[str] = Field(None, description="Inject information (optional)")
    # expected actions
    expected_actions: List[str] = Field(
        default_factory=list, description="List of expected actions"
    )
    # predictive analysis metadata — populated by LLM during scenario generation
    attack_technique: Optional[str] = Field(
        None,
        description=(
            "Primary attack technique used in this incident "
            "(e.g. 'phishing', 'lateral movement', 'ransomware deployment', 'SQL injection')"
        ),
    )
    target_asset: Optional[str] = Field(
        None,
        description=(
            "System or asset targeted in this incident "
            "(e.g. 'email server', 'database', 'workstation', 'network switch')"
        ),
    )
    vulnerability_class: Optional[str] = Field(
        None,
        description=(
            "Class of vulnerability or misconfiguration exploited "
            "(e.g. 'misconfiguration', 'unpatched CVE', 'weak credentials', 'social engineering')"
        ),
    )
    estimated_impact: Optional[str] = Field(
        None,
        description=(
            "Estimated operational impact if the incident is not contained "
            "(e.g. 'data exfiltration', 'service disruption', 'credential compromise', 'financial loss')"
        ),
    )
    exploit_path: Optional[ExploitPath] = Field(
        None,
        description=(
            "Structured breakdown of the vulnerability exploitation path that leads TO this incident "
            "from the previous attacker foothold. Explains HOW the attacker got here — the specific "
            "vulnerability, technique, pivot target, and detection window. "
            "Null for the first incident (initial access stage)."
        ),
    )


class Scenario(BaseModel):
    """Complete scenario with title and multiple incidents"""

    scenario_title: str = Field(..., description="Overall scenario title")
    incidents: List[Incident] = Field(..., description="List of incidents in the scenario")
    # Optional metadata fields — used by policy_draft and future endpoints
    scenario_description: Optional[str] = Field(None, description="High-level description of the scenario")
    threat_actor: Optional[str] = Field(None, description="Threat actor name or group, e.g. 'LockBit 3.0'")
    threat_type: Optional[str] = Field(None, description="Threat category, e.g. 'Ransomware', 'Phishing'")
    target_sector: Optional[str] = Field(None, description="Target sector, e.g. 'Government', 'Healthcare'")
    attack_vector: Optional[str] = Field(None, description="Primary attack vector, e.g. 'Spear-phishing email'")


class AttackChainNode(BaseModel):
    """
    One node in the attack chain — maps to a single scenario incident.
    Contains the MITRE technique, attacker objective, and the exploit path
    that led the attacker from the previous node to this one.
    """

    incident_index: int = Field(..., ge=0, description="0-based index matching scenario.incidents")
    incident_title: str = Field(..., description="Title of the incident (from scenario)")
    mitre_technique_id: str = Field(
        ...,
        description="Primary MITRE ATT&CK technique ID, e.g. 'T1566.001'. Use 'T0000' if unknown.",
    )
    mitre_technique_name: str = Field(
        ..., description="Human-readable ATT&CK technique name matching the ID"
    )
    attacker_objective: str = Field(
        ..., description="What the attacker aims to achieve in this step (1 sentence)"
    )
    exploit_path: Optional[ExploitPath] = Field(
        None,
        description=(
            "Full exploit path from the previous node to this one. "
            "MUST be null for incident_index=0 (initial access). "
            "MUST be populated for all subsequent nodes."
        ),
    )
    best_defensive_action: str = Field(
        ...,
        description="The single most impactful action that would have interrupted this exploit path",
    )
    defensive_opportunity_missed: bool = Field(
        ...,
        description="True if the scenario implies defenders had a realistic window to stop this but did not",
    )
    attack_stage: str = Field(
        ...,
        description=(
            "One of: initial_access, execution, persistence, privilege_escalation, "
            "defense_evasion, credential_access, lateral_movement, collection, "
            "command_and_control, exfiltration, impact, financial_fraud"
        ),
    )


class AttackChain(BaseModel):
    """
    Full attack chain for a scenario — machine-readable, graph-ready.
    Returned by /exploit_path endpoint and used by the SAFE dashboard
    to render the exploitation path visualization.
    """

    threat_actor: str = Field(..., description="Name or group of the threat actor")
    threat_actor_motivation: str = Field(
        ...,
        description="Primary motivation: financial gain, espionage, disruption, hacktivism, sabotage",
    )
    initial_access_vector: str = Field(
        ..., description="How the attacker first entered the environment"
    )
    total_dwell_time: str = Field(
        ...,
        description="Estimated total attacker dwell time from initial access to detection/containment",
    )
    kill_chain_phases: List[str] = Field(
        default_factory=list,
        description="MITRE ATT&CK / Cyber Kill Chain phases present in this scenario",
    )
    financial_impact_summary: str = Field(
        ...,
        description="Total financial impact: ransom, fraud amounts, recovery cost, fine exposure",
    )
    nodes: List[AttackChainNode] = Field(
        ..., description="One node per incident, ordered by incident_index"
    )


class ExploitPathRequest(BaseModel):
    """Request model for /exploit_path — takes a full Scenario."""

    scenario: Scenario = Field(
        ..., description="Complete structured scenario (from /query_structured or equivalent)"
    )
    use_rag: bool = Field(
        True,
        description=(
            "If true, retrieve RAG context to calibrate the attack chain against "
            "real-world incident data stored in the knowledge base."
        ),
    )


class ExploitPathResponse(BaseModel):
    """Response model for /exploit_path."""

    scenario_title: str = Field(..., description="Title of the analysed scenario")
    attack_chain: AttackChain = Field(
        ..., description="Full attack chain with per-incident exploit paths"
    )
    calibration_sources: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="RAG sources used to calibrate the attack chain against historical incidents",
    )
    incidents_with_exploit_paths: int = Field(
        ..., description="Number of incidents that have a fully populated exploit_path"
    )
    total_incidents: int = Field(..., description="Total number of incidents in the scenario")


class StructuredQueryResponse(BaseModel):
    """Response model for structured query with Incident"""

    query: str = Field(..., description="Original query")
    incident: Incident = Field(..., description="Structured incident generated by LLM")
    context: str = Field(..., description="Retrieved context used for generation")
    sources: List[Dict[str, Any]] = Field(..., description="Source documents")
    metadata: Dict[str, Any] = Field(..., description="Query metadata")


class StructuredScenarioResponse(BaseModel):
    """Response model for structured query with complete Scenario"""

    query: str = Field(..., description="Original query")
    scenario: Scenario = Field(..., description="Complete scenario with multiple incidents")
    context: str = Field(..., description="Retrieved context used for generation")
    sources: List[Dict[str, Any]] = Field(..., description="Source documents")
    metadata: Dict[str, Any] = Field(..., description="Query metadata")
    calibration_score: float = Field(
        0.0,
        description=(
            "Average semantic similarity score (0-1) between the query and retrieved historical scenarios. "
            "Higher = scenario is well-grounded in real historical incidents."
        ),
    )
    calibration_sources_count: int = Field(
        0,
        description="Number of historical sources used to ground the generated scenario.",
    )


class GetDocumentResponse(BaseModel):
    """Response model for retrieving a document by ID"""

    document_id: str = Field(..., description="Document identifier")
    content: str = Field(..., description="Full document content (all chunks concatenated)")


class TraineeIncidentView(BaseModel):
    """Incident fields shown to the trainee (expected_actions hidden)."""

    title: str = Field(..., description="Incident title")
    message_timestamp: str = Field(..., description="Time notation for the incident")
    description: str = Field(..., description="What is happening")
    inject: Optional[str] = Field(None, description="Inject / artefact text")


class NextStepLLMCore(BaseModel):
    """Structured LLM output without exploit_path. Used when include_exploit_path is false."""

    chosen_incident_index: int = Field(..., description="Index of the next incident to show (0-based)")
    rationale: str = Field(
        ...,
        min_length=10,
        description=(
            "REQUIRED. 1-2 sentences explaining WHY this incident follows causally from "
            "the trainee's action and the simulation history. Must reference the trainee's action."
        ),
    )
    predicted_threat_vector: Optional[str] = Field(
        None,
        description=(
            "Predict the NEXT attack technique the adversary will likely use, based on the trainee's response gap. "
            "Example: 'lateral movement via compromised credentials' or 'ransomware deployment on backup servers'. "
            "1 sentence max. Null if scenario is nearly complete."
        ),
    )
    predicted_impact: Optional[str] = Field(
        None,
        description=(
            "Predict the operational impact if the trainee fails to contain the situation at this step. "
            "Example: 'full data exfiltration within 2 hours' or 'service outage affecting 500 patients'. "
            "1 sentence max. Null if scenario is nearly complete."
        ),
    )


class NextStepLLMResult(NextStepLLMCore):
    """Full next-step output, including exploit_path. Used when include_exploit_path is true."""

    exploit_path: Optional[ExploitPath] = Field(
        None,
        description=(
            "Structured breakdown of the exploitation path the attacker will use to transition "
            "from the current incident to the chosen next incident. "
            "Explains the specific vulnerability, lateral movement technique, pivot target, "
            "new capability gained, time window, and detection indicators. "
            "Null only if the scenario is complete (is_scenario_complete=true)."
        ),
    )


class NextStepRequest(BaseModel):
    """
    State for choosing the next incident after the trainee submits their real action.

    visited_incident_indices must include current_incident_index (all steps already shown).
    """

    scenario: Scenario = Field(..., description="Full structured scenario from query_structured (or equivalent)")
    current_incident_index: int = Field(..., ge=0, description="Incident the trainee just responded to")
    user_action: str = Field(..., min_length=1, description="What the trainee actually did / decided (free text)")
    visited_incident_indices: List[int] = Field(
        ...,
        description="0-based indices already presented to the trainee; must include current_incident_index",
    )
    use_llm: bool = Field(
        True,
        description="If false, always use linear default next (no LLM call; useful for tests / outages)",
    )
    adapt_inject: bool = Field(
        False,
        description=(
            "If true, rewrite description+inject of the chosen incident so it acknowledges "
            "the trainee's real action and focuses on what still needs to be done. "
            "Requires use_llm=true; ignored otherwise."
        ),
    )
    include_exploit_path: bool = Field(
        False,
        description=(
            "If true, the next-step LLM also writes a full exploit_path "
            "(foothold, CVE, technique, IOCs, containment window). "
            "Closed by default so the exercise response stays short. "
            "Ignored when use_llm is false."
        ),
    )
    history_summary: Optional[str] = Field(
        None,
        description=(
            "Optional free-text summary of previous trainee actions, one line per step. "
            "Example: 'Step 0: isolated workstation\\nStep 1: blocked outbound IP'. "
            "Passed to the adapt LLM so it can reference the full session history."
        ),
    )


class AdaptLLMResult(BaseModel):
    """Structured LLM output for inject adaptation."""

    adapted_description: str = Field(
        ...,
        description="Rewritten description that acknowledges the trainee's action and surfaces what remains unresolved.",
    )
    adapted_inject: Optional[str] = Field(
        None,
        description="Rewritten inject artefact text (email, log, alert) updated to reflect trainee's prior actions.",
    )


class GradeRequest(BaseModel):
    """Request model for grading a single trainee action against expected actions."""

    scenario_title: str = Field(..., description="Title of the scenario")
    incident_title: str = Field(..., description="Title of the incident being graded")
    expected_actions: List[str] = Field(
        ..., min_length=1, description="Pre-authored expected actions (hidden from trainee)"
    )
    user_action: str = Field(..., min_length=1, description="What the trainee actually did (free text)")


class GradeLLMResult(BaseModel):
    """Structured LLM output for step grading."""

    score: float = Field(
        ..., ge=0.0, le=1.0, description="Score from 0.0 (nothing correct) to 1.0 (fully correct)"
    )
    level: str = Field(
        ..., description="One of: 'missing', 'partial', 'good', 'excellent'"
    )
    feedback: str = Field(
        ..., min_length=10, description="1-3 sentences of constructive feedback for the trainee"
    )
    matched_actions: List[str] = Field(
        default_factory=list, description="Expected actions the trainee covered (paraphrased)"
    )
    missed_actions: List[str] = Field(
        default_factory=list, description="Expected actions the trainee did NOT cover"
    )


class GradeResponse(BaseModel):
    """Response model for grade_step endpoint."""

    score: float = Field(..., description="0.0 – 1.0")
    level: str = Field(..., description="missing | partial | good | excellent")
    feedback: str = Field(..., description="Constructive feedback for the trainee")
    matched_actions: List[str] = Field(default_factory=list)
    missed_actions: List[str] = Field(default_factory=list)
    used_fallback: bool = Field(
        False, description="True if LLM failed and cosine-similarity fallback was used"
    )


class NextStepResponse(BaseModel):
    """Next incident for the trainee view, plus debug metadata for spikes."""

    next_incident: Optional[TraineeIncidentView] = Field(
        None, description="Next step payload without expected_actions"
    )
    next_incident_index: Optional[int] = Field(None, description="Index of next_incident in scenario.incidents")
    is_scenario_complete: bool = Field(
        False, description="True when there are no remaining incidents to show"
    )
    default_next_incident_index: Optional[int] = Field(
        None, description="Linear default: first index after current, else earliest unseen"
    )
    chosen_matches_default: bool = Field(
        False, description="True if LLM choice equals default_next_incident_index"
    )
    used_fallback: bool = Field(
        False,
        description="True if LLM was invalid/unavailable and server used default_next_incident_index",
    )
    rationale: Optional[str] = Field(None, description="From LLM when use_llm=true")
    inject_adapted: bool = Field(
        False,
        description="True if description/inject were rewritten to reflect trainee's action.",
    )
    predicted_threat_vector: Optional[str] = Field(
        None,
        description="Predicted next adversary technique based on trainee response quality.",
    )
    predicted_impact: Optional[str] = Field(
        None,
        description="Predicted operational impact if situation is not contained at this step.",
    )
    exploit_path: Optional[ExploitPath] = Field(
        None,
        description=(
            "Structured exploitation path the attacker will use to reach the chosen next incident. "
            "Contains foothold, vulnerability exploited, lateral movement technique, pivot target, "
            "new capability, containment window, and detection indicators. "
            "Present only when include_exploit_path=true, use_llm=true, and the scenario is not complete."
        ),
    )


class DebriefHistoryEntry(BaseModel):
    """One step of the simulation history for debrief input."""

    incident_index: int = Field(..., description="Index of the incident in the scenario")
    incident_title: str = Field(..., description="Title of the incident")
    user_action: str = Field(..., description="What the trainee did (free text)")
    grade_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Score from grade_step (0-1)")
    grade_level: Optional[str] = Field(None, description="Level from grade_step: missing/partial/good/excellent")


class DebriefRequest(BaseModel):
    """Request model for end-of-simulation debrief."""

    scenario: Scenario = Field(..., description="Full scenario object")
    history: List[DebriefHistoryEntry] = Field(
        ..., min_length=1, description="Ordered list of steps the trainee went through"
    )


class DebriefLLMResult(BaseModel):
    """Structured LLM output for the debrief."""

    overall_score: float = Field(
        ..., ge=0.0, le=1.0, description="Weighted overall performance score 0-1"
    )
    overall_level: str = Field(
        ..., description="One of: missing, partial, good, excellent"
    )
    summary: str = Field(
        ..., min_length=20, description="2-4 sentence narrative summary of the trainee's overall performance"
    )
    strengths: List[str] = Field(
        default_factory=list, description="2-4 things the trainee did well across the simulation"
    )
    gaps: List[str] = Field(
        default_factory=list, description="2-4 areas where performance was consistently weak"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="2-4 concrete, actionable improvement recommendations"
    )


class DebriefResponse(BaseModel):
    """Response model for the debrief endpoint."""

    overall_score: float = Field(..., description="0.0 – 1.0")
    overall_level: str = Field(..., description="missing | partial | good | excellent")
    summary: str = Field(..., description="Narrative summary of overall performance")
    strengths: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    used_fallback: bool = Field(False, description="True if LLM failed and score was averaged from grades")


# ── Policy Draft models ───────────────────────────────────────────────────────

class SimulationPerformanceData(BaseModel):
    """Aggregate trainee performance data for a scenario — used to enrich policy drafts."""

    simulations_count: int = Field(0, description="Number of completed simulation runs for this scenario")
    average_grade: Optional[float] = Field(None, description="Average trainee score 0-100 across all runs")
    top_missed_actions: List[str] = Field(
        default_factory=list,
        description="Most frequently missed expected actions across all runs",
    )
    grade_per_incident: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Per-incident average grades — list of {incident_title: avg_score}",
    )


class LEAContext(BaseModel):
    """Organisation-specific context provided by the LEA to replace [LEA INPUT NEEDED] placeholders."""

    organisation_name: Optional[str] = Field(None, description="Full name of the LEA/organisation, e.g. 'Hellenic Police, Cybercrime Division'")
    issuing_authority: Optional[str] = Field(None, description="Name and role of the signing authority, e.g. 'Chief Superintendent Andreas Papadopoulos'")
    incident_commander_title: Optional[str] = Field(None, description="Role title for the Incident Commander, e.g. 'Detective Inspector'")
    senior_management_title: Optional[str] = Field(None, description="Role title for senior management escalation, e.g. 'Deputy Commissioner'")
    dpo_name_contact: Optional[str] = Field(None, description="Data Protection Officer name and contact, e.g. 'Dr. Maria Nikolaou, dpo@police.gr'")
    national_cert_contact: Optional[str] = Field(None, description="National CERT/CSIRT name and contact, e.g. 'CERT-GR, cert@grnet.gr'")
    national_law_reference: Optional[str] = Field(None, description="National transposition law or internal directive, e.g. 'Law 4577/2018 (NIS transposition)'")
    supervisory_body: Optional[str] = Field(None, description="Ministry or supervisory body for external reporting, e.g. 'Hellenic Data Protection Authority (HDPA)'")
    external_audit_frequency: Optional[str] = Field(None, description="External security audit frequency, e.g. 'Annually by accredited external auditor'")


class PolicyDraftRequest(BaseModel):
    """Request model for policy draft generation."""

    scenario: Scenario = Field(..., description="Full scenario object with threat metadata")
    performance_data: Optional[SimulationPerformanceData] = Field(
        None,
        description=(
            "Aggregate simulation performance data. "
            "If provided, produces an evidence-based draft; otherwise threat-based only."
        ),
    )
    lea_context: Optional[LEAContext] = Field(
        None,
        description="Organisation-specific details from the LEA to fill policy placeholders. If omitted, generic placeholders are used.",
    )


class IdentifiedRisk(BaseModel):
    """A single identified risk entry in the policy draft."""

    threat_type: str = Field(..., description="Name/category of the threat per Europol taxonomy, e.g. 'Ransomware — Malware class'")
    likelihood: str = Field(..., description="HIGH | MEDIUM | LOW — based on simulation performance or threat profile")
    description: str = Field(..., description="1-2 sentences describing the risk and its potential impact")

    @field_validator("likelihood")
    @classmethod
    def validate_likelihood(cls, v: str) -> str:
        allowed = {"HIGH", "MEDIUM", "LOW"}
        normalised = v.strip().upper()
        if normalised not in allowed:
            raise ValueError(f"likelihood must be one of {allowed}, got: {v!r}")
        return normalised


class PolicyRecommendation(BaseModel):
    """A single policy recommendation for public authorities or LEAs."""

    policy_title: str = Field(..., description="Short action-oriented title, e.g. 'Mandatory MFA on all remote access'")
    rationale: str = Field(..., description="1-2 sentences grounding the recommendation in specific simulation findings or threat data")
    target_audience: str = Field(..., description="'LEA' | 'Public Authority' | 'Judicial Cooperation Network'")


class RoleEntry(BaseModel):
    """One row in the Roles and Responsibilities table."""

    role: str = Field(..., description="Role title, e.g. 'Incident Commander', 'Digital Forensics Officer'")
    responsibilities: str = Field(..., description="Concise description of duties during a cyber incident")
    lea_input_needed: bool = Field(
        False,
        description="Deprecated — always set to false. Role titles are generated as complete professional content.",
    )


class EscalationLevel(BaseModel):
    """One level in the escalation chain (L1 to L6)."""

    level: str = Field(..., description="e.g. 'L1', 'L2', 'L3'")
    trigger: str = Field(..., description="Condition that activates this escalation level")
    notify: str = Field(..., description="Role or external body to notify; use '[LEA INPUT NEEDED]' where org-specific")
    timeframe: str = Field(..., description="Maximum time allowed, e.g. 'Immediately', 'Within 30 minutes', 'Within 24 hours'")

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        stripped = v.strip().upper()
        if not stripped.startswith("L"):
            raise ValueError(f"Escalation level must start with 'L' (e.g. L1, L2), got: {v!r}")
        return stripped


class ReportingObligation(BaseModel):
    """One row in the external reporting obligations table."""

    body: str = Field(..., description="Reporting body, e.g. 'National Data Protection Authority', 'National CERT/CSIRT', 'Europol EC3'")
    legal_basis: str = Field(..., description="Legal basis, e.g. 'GDPR Art. 33', 'NIS2 Art. 23'")
    obligation: str = Field(..., description="What must be reported")
    deadline: str = Field(..., description="Reporting deadline, e.g. 'Within 72 hours of becoming aware'")

    # Known mandatory EU deadlines that must not be changed by the LLM
    _MANDATORY_DEADLINES: dict = {
        "gdpr": "72",          # GDPR Art.33 — 72h
        "nis2": "24",          # NIS2 Art.23 — 24h early warning
    }

    @field_validator("deadline")
    @classmethod
    def validate_deadline(cls, v: str) -> str:
        lower = v.lower()
        # If this row references GDPR, the deadline MUST be 72h
        return v  # value returned as-is; cross-field check done in PolicyDraftLLMResult validator

    @field_validator("legal_basis")
    @classmethod
    def validate_legal_basis(cls, v: str) -> str:
        """Reject clearly fabricated legal references."""
        known_instruments = [
            "gdpr", "nis2", "nis 2", "2022/2555", "2016/679",
            "budapest", "ets 185", "leerp", "led", "2016/680",
            "lea input",      # legacy placeholders still accepted
            "national",       # national legislation references
            "ministry",       # ministry directives
            "supervisory",    # supervisory authority references
            "regulation",     # generic regulatory references
            "directive",      # EU/national directives
        ]
        lower = v.lower()
        if not any(inst in lower for inst in known_instruments):
            raise ValueError(
                f"legal_basis does not reference a recognised EU instrument: {v!r}. "
                "Use GDPR, NIS2, Budapest Convention, LEERP, or national legislation."
            )
        return v


class PolicyDraftLLMResult(BaseModel):
    """Structured LLM output for policy draft generation — aligned with NIST 800-61r3, LEERP, and Europol Taxonomy."""

    document_title: str = Field(
        ..., description="Formal title, e.g. 'Ransomware Incident Response Operational Policy for Law Enforcement Agencies'"
    )
    classification: str = Field(
        "RESTRICTED — LAW ENFORCEMENT SENSITIVE",
        description="Document classification level",
    )
    # Section 1
    management_commitment: str = Field(
        ...,
        min_length=50,
        description=(
            "Formal statement of management commitment to this policy. "
            "State that leadership mandates compliance, allocates resources, and authorises the incident response capability. "
            "End with: 'Requires signature from: [LEA INPUT NEEDED — issuing authority role and name].'"
        ),
    )
    # Section 2
    purpose_and_scope: str = Field(
        ...,
        min_length=80,
        description=(
            "Section 2 — Purpose and Scope. "
            "2.1 Purpose: one sentence stating what threat this policy governs and why it exists for LEAs. "
            "2.2 Scope: who and what it applies to (all ICT systems, all staff, third-party contractors). "
            "2.3 Regulatory Framework: explicitly name EU NIS2 Directive 2022/2555 (Art. 23), "
            "EU GDPR 2016/679 (Art. 33-34), Budapest Convention on Cybercrime (ETS 185), "
            "EU Law Enforcement Directive 2016/680, and add '[LEA INPUT NEEDED — national transposition law]'."
        ),
    )
    # Section 3
    incident_classification: str = Field(
        ...,
        min_length=40,
        description=(
            "Section 3 — Incident Classification using the Europol/CSIRT Common Taxonomy. "
            "State: Class (e.g. Malware, Availability, Intrusion), Type (specific subtype), "
            "and Legislative mapping (Budapest Convention article + NIS Directive article). "
            "Example: 'Class: Malware | Type: Ransomware deployment | Legislative mapping: Budapest Art. 2, 6; NIS2 Directive Art. 3'."
        ),
    )
    # Section 4 (threat assessment)
    executive_summary: str = Field(
        ...,
        min_length=50,
        description=(
            "Section 4 — Threat Assessment. MUST be a plain text string, NOT a JSON object. "
            "Write as continuous prose with two labelled paragraphs: "
            "4.1 Threat Profile: threat actor, initial vector, target assets, vulnerability class, estimated impact. "
            "4.2 Simulation Evidence: if data available, state number of runs, average score, and top 3 missed actions with failure rates; "
            "if no data, state 'No simulation data available — assessment is threat-profile-based only'."
        ),
    )

    @field_validator("executive_summary", mode="before")
    @classmethod
    def coerce_executive_summary(cls, v: object) -> str:
        """Coerce dict/object from LLM into a prose string if needed."""
        if isinstance(v, str):
            return v
        if isinstance(v, dict):
            parts: list[str] = []
            tp = v.get("threat_profile") or v.get("4.1") or {}
            se = v.get("simulation_evidence") or v.get("4.2") or {}
            if tp:
                parts.append("4.1 Threat Profile")
                for k, val in tp.items():
                    label = k.replace("_", " ").capitalize()
                    parts.append(f"  {label}: {val}")
            if se:
                parts.append("4.2 Simulation Evidence")
                for k, val in se.items():
                    if isinstance(val, list):
                        parts.append(f"  {k.replace('_', ' ').capitalize()}:")
                        for item in val:
                            parts.append(f"    - {item}")
                    else:
                        parts.append(f"  {k.replace('_', ' ').capitalize()}: {val}")
            return "\n".join(parts) if parts else str(v)
        return str(v)
    # Section 5.1-5.2
    identified_risks: List[IdentifiedRisk] = Field(
        ..., min_length=2, description="3-5 identified risks grounded in scenario threat profile and simulation data"
    )
    detection_procedures: List[str] = Field(
        ..., min_length=3, description="Section 5.1 — Detection and Initial Assessment steps (T+0 to T+30 min), each starting with an action verb"
    )
    containment_procedures: List[str] = Field(
        ..., min_length=3, description="Section 5.2 — Containment steps (T+30 min to T+2 hours), each naming the responsible role"
    )
    # Section 5.3
    evidence_preservation_steps: List[str] = Field(
        ..., min_length=3, description="Section 5.3 — Forensic evidence preservation steps; MUST precede remediation; include SHA-256 hashing and chain of custody"
    )
    # Section 5.4
    escalation_chain: List[EscalationLevel] = Field(
        ...,
        min_length=4,
        description=(
            "Section 5.4 — Escalation chain with at least 6 levels: "
            "L1 First Responder (immediate), L2 Incident Commander (30 min), L3 Senior Management (1 hour), "
            "L4 Data Protection Officer (1 hour internal / 72h to DPA), "
            "L5 National CERT/CSIRT (NIS2 Art.23 — 24h early warning), "
            "L6 Europol EC3 (if criminal infrastructure involved). "
            "Use '[LEA INPUT NEEDED]' for org-specific contacts."
        ),
    )
    # Section 5.5
    external_reporting_obligations: List[ReportingObligation] = Field(
        ...,
        min_length=3,
        description=(
            "Section 5.5 — External reporting obligations table. "
            "Must include: National DPA (GDPR Art.33, 72h), National CERT/CSIRT (NIS2 Art.23, 24h early warning), "
            "Europol EC3 (if criminal infrastructure), and one '[LEA INPUT NEEDED]' row for internal chain of command."
        ),
    )
    # Section 6
    preventive_controls: List[str] = Field(
        ..., min_length=3, description="Section 6.1 — Technical preventive controls prefixed with CRITICAL / HIGH / MEDIUM"
    )
    administrative_controls: List[str] = Field(
        ..., min_length=2, description="Section 6.2 — Administrative/organisational controls, e.g. mandatory training, tabletop exercises, penetration testing"
    )
    # Section 7
    roles_and_responsibilities: List[RoleEntry] = Field(
        ...,
        min_length=4,
        description=(
            "Section 7 — Roles and Responsibilities table. "
            "Must include: First Responder, Duty ICT Officer, Incident Commander, Digital Forensics Officer, "
            "Communications Officer, Senior Management. Set lea_input_needed=true for roles requiring LEA validation."
        ),
    )
    # Section 8
    policy_recommendations: List[PolicyRecommendation] = Field(
        ..., min_length=3, description="3-5 formal policy recommendations grounded in simulation findings or threat data"
    )
    resource_requirements: List[str] = Field(
        ..., min_length=2, description="Section 8 — Training gaps (from simulation), tools, and personnel requirements"
    )
    # Section 9
    review_cycle: List[str] = Field(
        ...,
        min_length=3,
        description=(
            "Section 9 — Review and Update Cycle. Each entry is one review activity with its frequency, "
            "e.g. 'Full policy review — Annually or after any significant incident', "
            "'SAFE simulation exercise — Bi-annual', 'Regulatory compliance review (NIS2, GDPR) — Annually'."
        ),
    )
    draft_type: str = Field(
        ..., description="'threat-based' if no simulation data; 'evidence-based' if simulation performance data was used"
    )

    @field_validator("draft_type")
    @classmethod
    def validate_draft_type(cls, v: str) -> str:
        allowed = {"threat-based", "evidence-based"}
        stripped = v.strip().lower()
        if stripped not in allowed:
            raise ValueError(f"draft_type must be one of {allowed}, got: {v!r}")
        return stripped

    @field_validator("external_reporting_obligations")
    @classmethod
    def validate_eu_deadlines(cls, obligations: list) -> list:
        """
        Enforce that mandatory EU deadlines are not hallucinated away.
        GDPR Art.33 = 72h, NIS2 Art.23 = 24h early warning.
        Raises ValueError if a known row has a clearly wrong deadline.
        """
        for ob in obligations:
            lb = ob.legal_basis.lower()
            dl = ob.deadline.lower()
            if "gdpr" in lb or "art. 33" in lb or "art.33" in lb:
                if "72" not in dl and "lea input" not in dl:
                    raise ValueError(
                        f"GDPR Art.33 deadline must be 72 hours, got: {ob.deadline!r}"
                    )
            # Only enforce the 24-hour NIS2 Art.23 deadline when the entry is
            # specifically the CERT/CSIRT early-warning obligation (Art. 23 must be
            # explicitly named). Generic references to NIS2 on other rows (e.g.
            # Ministry entries) may have a different national deadline.
            if "art. 23" in lb or "art.23" in lb:
                if "24" not in dl and "lea input" not in dl:
                    raise ValueError(
                        f"NIS2 Art.23 early warning deadline must be 24 hours, got: {ob.deadline!r}"
                    )
        return obligations

    @field_validator("purpose_and_scope")
    @classmethod
    def validate_regulatory_references(cls, v: str) -> str:
        """Ensure the Regulatory Framework section mentions all mandatory EU instruments."""
        upper = v.upper()
        missing = []
        if "NIS2" not in upper and "2022/2555" not in upper:
            missing.append("NIS2 Directive 2022/2555")
        if "GDPR" not in upper and "2016/679" not in upper:
            missing.append("GDPR 2016/679")
        if "BUDAPEST" not in upper and "ETS 185" not in upper:
            missing.append("Budapest Convention (ETS 185)")
        if missing:
            raise ValueError(
                f"purpose_and_scope is missing required regulatory references: {missing}"
            )
        return v


class PolicyDraftResponse(BaseModel):
    """Response model for the policy_draft endpoint."""

    document_title: str
    classification: str
    generated_at: str = Field(..., description="ISO 8601 timestamp of generation")
    scenario_name: str
    draft_type: str = Field(..., description="'threat-based' or 'evidence-based'")
    simulations_used: int = Field(0, description="Number of simulation runs used as evidence base")
    management_commitment: str = Field(default="")
    purpose_and_scope: str = Field(default="")
    incident_classification: str = Field(default="")
    executive_summary: str
    identified_risks: List[IdentifiedRisk] = Field(default_factory=list)
    detection_procedures: List[str] = Field(default_factory=list)
    containment_procedures: List[str] = Field(default_factory=list)
    evidence_preservation_steps: List[str] = Field(default_factory=list)
    escalation_chain: List[EscalationLevel] = Field(default_factory=list)
    external_reporting_obligations: List[ReportingObligation] = Field(default_factory=list)
    preventive_controls: List[str] = Field(default_factory=list)
    administrative_controls: List[str] = Field(default_factory=list)
    roles_and_responsibilities: List[RoleEntry] = Field(default_factory=list)
    policy_recommendations: List[PolicyRecommendation] = Field(default_factory=list)
    resource_requirements: List[str] = Field(default_factory=list)
    review_cycle: List[str] = Field(default_factory=list)
    used_fallback: bool = Field(False, description="True if LLM failed and a minimal fallback response was returned")
    validation_warnings: List[str] = Field(
        default_factory=list,
        description=(
            "Non-fatal content warnings raised by post-generation checks. "
            "Each warning describes a potential hallucination or omission that a human reviewer must address."
        ),
    )
