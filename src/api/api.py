"""
FastAPI application for Scenario Builder Service.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

import structlog
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ..config.models import (
    AdaptLLMResult,
    AttackChain,
    DebriefLLMResult,
    DebriefRequest,
    DebriefResponse,
    ExploitPathRequest,
    ExploitPathResponse,
    GetDocumentResponse,
    GradeLLMResult,
    GradeRequest,
    GradeResponse,
    HealthResponse,
    IdentifiedRisk,
    IngestScenarioRequest,
    IngestScenarioResponse,
    NextStepLLMResult,
    NextStepRequest,
    NextStepResponse,
    PolicyDraftLLMResult,
    PolicyDraftRequest,
    PolicyDraftResponse,
    PolicyRecommendation,
    ProcessRequest,
    ProcessResponse,
    QueryRequest,
    QueryResponse,
    Scenario,
    StructuredScenarioResponse,
)
from ..config.settings import settings
from ..embeddings.embeddings import EmbeddingService
from ..embeddings.sparse_embeddings import SparseEmbeddingService
from ..extraction.extractor import DocumentExtractor
from ..llm.llm_client import LLMClient
from ..processing.processors import DocumentProcessor, detect_sector
from ..retrieval.retrieval import RetrievalSystem
from ..scenario.next_step import (
    ADAPT_INJECT_SYSTEM_PROMPT,
    NEXT_STEP_SYSTEM_PROMPT,
    apply_adapt_result,
    build_adapt_user_message,
    build_next_step_user_message,
    build_visited_summary,
    current_incident_summary,
    default_next_index,
    eligible_indices,
    incident_to_trainee_view,
    summarize_incidents_for_prompt,
    validate_next_step_request,
)
from ..scenario.grader import (
    GRADE_SYSTEM_PROMPT,
    build_grade_user_message,
    cosine_fallback,
)
from ..scenario.debriefer import (
    DEBRIEF_SYSTEM_PROMPT,
    build_debrief_user_message,
    score_fallback,
)
from ..scenario.policy_drafter import (
    POLICY_DRAFT_SYSTEM_PROMPT,
    _fallback_response,
    assert_no_hallucination,
    build_policy_draft_rag_query,
    build_policy_draft_user_message,
)
from ..scenario.scenario_generator import (
    SCENARIO_GENERATION_SYSTEM_PROMPT,
    build_scenario_generation_prompt,
)
from ..scenario.exploit_path_analyzer import (
    EXPLOIT_PATH_SYSTEM_PROMPT,
    build_exploit_path_user_message,
    summarize_incidents_for_exploit_path,
)
from ..storage.vector_store import VectorStore

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

log = structlog.get_logger()

# Global service components
document_extractor: Optional[DocumentExtractor] = None
document_processor: Optional[DocumentProcessor] = None
embedding_service: Optional[EmbeddingService] = None
sparse_embedding_service: Optional[SparseEmbeddingService] = None
vector_store: Optional[VectorStore] = None
retrieval_system: Optional[RetrievalSystem] = None
llm_client: Optional[LLMClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    log.info("starting_scenario_builder_service", version="1.0.0")
    await initialize_services()
    yield
    # Shutdown
    log.info("shutting_down_scenario_builder_service")


app = FastAPI(
    title=settings.service_name,
    description="Scenario builder service with document extraction, RAG, and LLM integration",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create API v1 router
api_v1 = APIRouter(prefix="/api/v1", tags=["v1"])


async def initialize_services():
    """Initialize all service components"""
    global document_extractor, document_processor, embedding_service, sparse_embedding_service
    global vector_store, retrieval_system, llm_client

    try:
        log.info("initializing_services")

        # Initialize document extractor
        document_extractor = DocumentExtractor(data_folder=str(settings.data_folder))

        # Initialize document processor for chunking
        document_processor = DocumentProcessor()

        # Initialize embedding service
        embedding_service = EmbeddingService()

        # Initialize sparse embedding service (optional)
        try:
            sparse_embedding_service = SparseEmbeddingService()
            log.info("sparse_embedding_service_initialized")
        except Exception as e:
            log.warning("sparse_embedding_service_init_failed", error=str(e))
            sparse_embedding_service = None

        # Initialize vector store (Qdrant + SQLite) — non-fatal if Qdrant is unavailable.
        # The service will start without RAG; all LLM endpoints still work.
        try:
            vector_store = VectorStore()
            retrieval_system = RetrievalSystem(
                embedding_service, vector_store, sparse_embedding_service
            )
            log.info("vector_store_and_retrieval_initialized")
        except Exception as qdrant_err:
            log.warning(
                "qdrant_unavailable_starting_without_rag",
                error=str(qdrant_err),
                hint=(
                    "Set QDRANT_HOST and QDRANT_PORT correctly to enable RAG. "
                    "All LLM endpoints (policy_draft, grade_step, debrief, next_step) work without RAG."
                ),
            )
            vector_store = None
            retrieval_system = None

        # Initialize LLM client
        llm_client = LLMClient()

        log.info("services_initialized_successfully", rag_enabled=(retrieval_system is not None))

    except Exception as e:
        log.error("service_initialization_failed", error=str(e))
        raise


# Health endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        service=settings.service_name,
        timestamp=datetime.now().isoformat(),
        version="1.0.0",
    )


# Process endpoint
@api_v1.post("/process", response_model=ProcessResponse)
async def process_documents(request: ProcessRequest):
    """
    Process documents from the data folder.

    Extracts text from all supported documents, chunks them, generates embeddings,
    and stores them in the vector database.
    """
    try:
        if not all([document_extractor, document_processor, embedding_service, vector_store]):
            raise HTTPException(status_code=500, detail="Services not initialized")

        # Determine data folder
        data_folder = request.data_folder or str(settings.data_folder)

        log.info("processing_started", data_folder=data_folder)

        # Step 1: Extract documents from folder
        extracted_docs = document_extractor.extract_from_folder(data_folder)

        if not extracted_docs:
            log.warning("no_documents_found", data_folder=data_folder)
            return ProcessResponse(
                status="completed",
                message="No documents found to process",
                documents_processed=0,
                chunks_created=0,
            )

        total_chunks = 0
        processed_docs = 0

        # Step 2: Process each extracted document
        for doc_data in extracted_docs:
            try:
                # Check if already processed (unless force_reprocess)
                document_id = document_processor._generate_document_id(doc_data["file_path"])

                if not request.force_reprocess:
                    # Check if document exists in vector store
                    existing_doc = vector_store.get_document_metadata(document_id)
                    if existing_doc:
                        log.info(
                            "document_already_processed",
                            document_id=document_id,
                            file_name=doc_data["file_name"],
                        )
                        continue

                # Chunk the document
                chunks = document_processor.process_extracted_document(doc_data)

                if not chunks:
                    log.warning("no_chunks_created", file_name=doc_data["file_name"])
                    continue

                # Generate embeddings for chunks
                chunk_contents = [chunk.content for chunk in chunks]
                embeddings = embedding_service.embed_documents(chunk_contents)

                # Generate sparse embeddings if available
                sparse_embeddings = None
                if sparse_embedding_service:
                    try:
                        sparse_embeddings = sparse_embedding_service.embed_documents(chunk_contents)
                    except Exception as e:
                        log.warning("sparse_embedding_failed", error=str(e))

                # Store chunks in vector database
                vector_store.add_chunks(chunks, embeddings, sparse_embeddings)

                total_chunks += len(chunks)
                processed_docs += 1

                log.info(
                    "document_stored",
                    document_id=document_id,
                    file_name=doc_data["file_name"],
                    chunks=len(chunks),
                )

            except Exception as e:
                log.error(
                    "document_processing_error",
                    file_name=doc_data.get("file_name", "unknown"),
                    error=str(e),
                )
                continue

        log.info(
            "processing_completed", documents_processed=processed_docs, total_chunks=total_chunks
        )

        return ProcessResponse(
            status="completed",
            message=f"Successfully processed {processed_docs} documents",
            documents_processed=processed_docs,
            chunks_created=total_chunks,
        )

    except Exception as e:
        log.error("process_endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


# Query endpoint with LLM integration
@api_v1.post("/query", response_model=QueryResponse)
async def query_with_llm(request: QueryRequest):
    """
    Query documents and generate an answer using LLM.

    Steps:
    1. Retrieve relevant context from vector database
    2. Build system prompt + context + query
    3. Call LLM to generate answer
    4. Return answer with sources
    """
    try:
        if not all([retrieval_system, llm_client]):
            raise HTTPException(status_code=500, detail="Services not initialized")

        sector = request.sector or detect_sector(request.query)
        log.info("query_received", query=request.query[:100], sector=sector)

        # Step 1: Retrieve relevant context
        search_results = retrieval_system.search(
            query=request.query,
            top_k=request.top_k,
            use_reranking=request.use_reranking,
            use_hybrid=request.use_hybrid,
            initial_k=request.initial_k,
            use_advanced_reranker=request.use_advanced_reranker,
            sector_filter=sector if sector != "general" else None,
        )

        # Step 2: Extract context and sources
        context_parts = []
        sources = []

        for result in search_results.get("results", []):
            if "content" in result:
                document_name = result.get("document_name", "Unknown Document")

                # Add to context
                context_with_source = f"[Source: {document_name}]\n{result['content']}"
                context_parts.append(context_with_source)

                # Add to sources list
                sources.append(
                    {
                        "document_name": document_name,
                        "document_type": result.get("document_type", "unknown"),
                        "score": result.get("score", 0.0),
                        "chunk_id": result.get("chunk_id", ""),
                    }
                )

        # Combine context
        combined_context = "\n\n---\n\n".join(context_parts)

        # if not combined_context:
        #     log.warning("no_context_found", query=request.query)
        #     return QueryResponse(
        #         query=request.query,
        #         answer="I couldn't find any relevant information to answer your question.",
        #         context="",
        #         sources=[],
        #         metadata=search_results.get("metadata", {})
        #     )

        # Step 3: Generate answer using LLM
        answer = llm_client.generate_answer(query=request.query, context=combined_context)

        # Step 4: Return response
        response = QueryResponse(
            query=request.query,
            answer=answer,
            context=combined_context,
            sources=sources,
            metadata=search_results.get("metadata", {}),
        )

        log.info(
            "query_completed",
            query_length=len(request.query),
            answer_length=len(answer),
            sources_count=len(sources),
            answer = answer #TODO remove the whole answer from logs 
        )

        return response

    except Exception as e:
        log.error("query_endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


# Structured query endpoint with Scenario model
@api_v1.post("/query_structured", response_model=StructuredScenarioResponse)
async def query_with_structured_output(request: QueryRequest):
    """
    Query documents and generate a complete structured Scenario using LLM.

    This endpoint uses Ollama's structured output feature (JSON schema mode) to return
    a validated Scenario object with a scenario title and multiple incidents.
    It leverages Pydantic validation to ensure consistent, type-safe responses.

    Steps:
    1. Retrieve relevant context from vector database
    2. Build specialized system prompt for scenario generation
    3. Call LLM with structured output (JSON schema mode)
    4. Validate response against Scenario model
    5. Return structured Scenario with sources
    """
    try:
        if not all([retrieval_system, llm_client]):
            raise HTTPException(status_code=500, detail="Services not initialized")

        sector = request.sector or detect_sector(request.query)
        log.info("structured_query_received", query=request.query[:100], sector=sector)

        # Step 1: Retrieve relevant context (same as regular query)
        search_results = retrieval_system.search(
            query=request.query,
            top_k=request.top_k,
            use_reranking=request.use_reranking,
            use_hybrid=request.use_hybrid,
            initial_k=request.initial_k,
            use_advanced_reranker=request.use_advanced_reranker,
            sector_filter=sector if sector != "general" else None,
        )

        # Step 2: Extract context and sources
        context_parts = []
        sources = []

        for result in search_results.get("results", []):
            if "content" in result:
                document_name = result.get("document_name", "Unknown Document")

                # Add to context
                context_with_source = f"[Source: {document_name}]\n{result['content']}"
                context_parts.append(context_with_source)

                # Add to sources list
                sources.append(
                    {
                        "document_name": document_name,
                        "document_type": result.get("document_type", "unknown"),
                        "score": result.get("score", 0.0),
                        "chunk_id": result.get("chunk_id", ""),
                    }
                )

        # Combine context
        combined_context = "\n\n---\n\n".join(context_parts)

        # Step 3: Generate structured scenario using LLM
        # Build sector-aware user message and use the SAFE scenario generation prompt
        scenario_user_msg = build_scenario_generation_prompt(
            trainer_instructions=request.query,
            sector=sector,
        )
        scenario = llm_client.generate_structured_answer(
            query=scenario_user_msg,
            context=combined_context,
            response_model=Scenario,
            system_prompt=SCENARIO_GENERATION_SYSTEM_PROMPT,
        )

        # Step 4: Return structured response
        source_scores = [s.get("score", 0.0) for s in sources if s.get("score") is not None]
        calibration_score = round(sum(source_scores) / len(source_scores), 4) if source_scores else 0.0

        response = StructuredScenarioResponse(
            query=request.query,
            scenario=scenario,
            context=combined_context,
            sources=sources,
            metadata=search_results.get("metadata", {}),
            calibration_score=calibration_score,
            calibration_sources_count=len(source_scores),
        )

        log.info(
            "structured_query_completed",
            query_length=len(request.query),
            scenario_title=scenario.scenario_title,
            incidents_count=len(scenario.incidents),
            sources_count=len(sources),
        )

        return response

    except Exception as e:
        log.error("structured_query_endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Structured query failed: {str(e)}")


@api_v1.post("/next_step", response_model=NextStepResponse)
async def next_training_step(request: NextStepRequest):
    """
    Choose the next incident to show after the trainee submits their real action.

    Stateless: the client sends the full scenario plus visit history. The next index
    is always chosen from incidents not yet in ``visited_incident_indices`` (allowlist).
    Trainee-facing payload omits ``expected_actions``.

    If only one incident remains, the selection LLM is skipped. If ``use_llm`` is false,
    the linear default (next unseen index after current, else wrap) is used.

    Set ``adapt_inject=true`` (requires ``use_llm=true``) to rewrite description+inject
    so they acknowledge what the trainee already did and surface what still needs to be done.
    """
    try:
        if not llm_client:
            raise HTTPException(status_code=500, detail="LLM client not initialized")

        scenario = request.scenario
        ok, err_msg = validate_next_step_request(
            scenario, request.current_incident_index, request.visited_incident_indices
        )
        if not ok:
            raise HTTPException(status_code=400, detail=err_msg)

        n = len(scenario.incidents)
        eligible = eligible_indices(n, request.visited_incident_indices)
        if not eligible:
            return NextStepResponse(is_scenario_complete=True)

        default_idx = default_next_index(
            n, request.visited_incident_indices, request.current_incident_index
        )
        if default_idx is None:
            default_idx = eligible[0]

        chosen: int
        rationale: Optional[str] = None
        used_fallback = False
        parsed: Optional[NextStepLLMResult] = None

        # --- Step 1: choose which incident index comes next ---
        if not request.use_llm:
            chosen = default_idx
        else:
            current_inc = scenario.incidents[request.current_incident_index]
            user_msg = build_next_step_user_message(
                scenario.scenario_title,
                request.current_incident_index,
                current_incident_summary(current_inc),
                request.user_action,
                eligible,
                summarize_incidents_for_prompt(scenario, eligible),
                visited_summary=build_visited_summary(
                    scenario, request.visited_incident_indices, request.current_incident_index
                ),
            )
            try:
                parsed = llm_client.generate_structured_answer(
                    query=user_msg,
                    context="",
                    response_model=NextStepLLMResult,
                    system_prompt=NEXT_STEP_SYSTEM_PROMPT,
                )
                if parsed.chosen_incident_index not in eligible:
                    log.warning(
                        "next_step_llm_invalid_index",
                        got=parsed.chosen_incident_index,
                        eligible=eligible,
                    )
                    chosen = default_idx
                    used_fallback = True
                else:
                    chosen = parsed.chosen_incident_index
                    rationale = parsed.rationale
            except Exception as e:
                log.error("next_step_llm_error", error=str(e))
                chosen = default_idx
                used_fallback = True

        chosen_incident = scenario.incidents[chosen]
        inject_adapted = False

        # --- Step 2 (optional): rewrite description+inject to reflect trainee's action ---
        if request.adapt_inject and request.use_llm:
            adapt_msg = build_adapt_user_message(
                scenario_title=scenario.scenario_title,
                user_action=request.user_action,
                chosen_incident=chosen_incident,
                history_summary=request.history_summary or "",
            )
            try:
                adapt_result: AdaptLLMResult = llm_client.generate_structured_answer(
                    query=adapt_msg,
                    context="",
                    response_model=AdaptLLMResult,
                    system_prompt=ADAPT_INJECT_SYSTEM_PROMPT,
                )
                next_inc = apply_adapt_result(chosen_incident, adapt_result)
                inject_adapted = True
                log.info("next_step_inject_adapted", chosen=chosen, scenario_title=scenario.scenario_title)
            except Exception as e:
                log.warning("next_step_adapt_failed_fallback", error=str(e))
                next_inc = incident_to_trainee_view(chosen_incident)
        else:
            next_inc = incident_to_trainee_view(chosen_incident)

        return NextStepResponse(
            next_incident=next_inc,
            next_incident_index=chosen,
            is_scenario_complete=False,
            default_next_incident_index=default_idx,
            chosen_matches_default=(chosen == default_idx),
            used_fallback=used_fallback,
            rationale=rationale,
            inject_adapted=inject_adapted,
            predicted_threat_vector=parsed.predicted_threat_vector if (parsed and not used_fallback) else None,
            predicted_impact=parsed.predicted_impact if (parsed and not used_fallback) else None,
            exploit_path=parsed.exploit_path if (parsed and not used_fallback) else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        log.error("next_step_endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"next_step failed: {str(e)}")


@api_v1.post("/exploit_path", response_model=ExploitPathResponse)
async def analyze_exploit_path(request: ExploitPathRequest):
    """
    Analyze the full attack chain for a scenario and return structured exploit paths.

    Takes a complete Scenario (from /query_structured or equivalent) and produces an
    AttackChain with one node per incident, each containing:
      - MITRE ATT&CK technique ID and name
      - Attacker objective for this step
      - Full ExploitPath (foothold → vulnerability → technique → pivot target → new capability)
      - Best defensive action that would have interrupted this path
      - Estimated containment window (how long defenders had to act)
      - Detection indicators (IOCs/behavioural signals observable during the exploit)

    This endpoint fulfils the SAFE grant requirement (T7.4) to explain exploitation paths
    and potential vulnerabilities — not just the outcome, but HOW the attacker gets there.
    Designed to feed the SAFE dashboard's attack chain visualization.

    The attack chain is optionally calibrated against real-world incident data in the RAG
    knowledge base (use_rag=true, default).
    """
    try:
        if not llm_client:
            raise HTTPException(status_code=500, detail="LLM client not initialized")

        scenario = request.scenario

        if not scenario.incidents:
            raise HTTPException(status_code=400, detail="Scenario has no incidents")

        log.info(
            "exploit_path_requested",
            scenario_title=scenario.scenario_title,
            incident_count=len(scenario.incidents),
            use_rag=request.use_rag,
        )

        # Step 1: Optionally retrieve RAG context for calibration
        calibration_sources: list = []
        rag_context = ""

        if request.use_rag and retrieval_system:
            rag_query = (
                f"exploit path attack chain {scenario.scenario_title} "
                f"{scenario.threat_actor or ''} {scenario.threat_type or ''}"
            )
            sector = detect_sector(scenario.scenario_title)
            try:
                search_results = retrieval_system.search(
                    query=rag_query,
                    top_k=8,
                    sector_filter=sector if sector != "general" else None,
                    use_reranking=True,
                    use_hybrid=False,
                )
                raw_results = search_results.get("results", [])
                context_parts = []
                for result in raw_results:
                    document_name = result.get("document_name", "Unknown")
                    context_parts.append(f"[Source: {document_name}]\n{result['content']}")
                    calibration_sources.append(
                        {
                            "document_name": document_name,
                            "document_type": result.get("document_type", "unknown"),
                            "score": result.get("score", 0.0),
                        }
                    )
                rag_context = "\n\n---\n\n".join(context_parts)
            except Exception as e:
                log.warning("exploit_path_rag_failed", error=str(e))

        # Step 2: Build prompt
        incidents_summary = summarize_incidents_for_exploit_path(scenario.incidents)
        user_msg = build_exploit_path_user_message(scenario.scenario_title, incidents_summary)

        # Step 3: Call LLM for structured attack chain
        system_content = EXPLOIT_PATH_SYSTEM_PROMPT
        if rag_context:
            system_content += f"\n\n---\n\nHistorical Incident Context (for calibration):\n{rag_context}"

        attack_chain: AttackChain = llm_client.generate_structured_answer(
            query=user_msg,
            context=rag_context,
            response_model=AttackChain,
            system_prompt=EXPLOIT_PATH_SYSTEM_PROMPT,
        )

        # Step 4: Count populated exploit paths
        incidents_with_paths = sum(
            1 for node in attack_chain.nodes if node.exploit_path is not None
        )

        log.info(
            "exploit_path_completed",
            scenario_title=scenario.scenario_title,
            nodes=len(attack_chain.nodes),
            incidents_with_paths=incidents_with_paths,
            threat_actor=attack_chain.threat_actor,
        )

        return ExploitPathResponse(
            scenario_title=scenario.scenario_title,
            attack_chain=attack_chain,
            calibration_sources=calibration_sources,
            incidents_with_exploit_paths=incidents_with_paths,
            total_incidents=len(scenario.incidents),
        )

    except HTTPException:
        raise
    except Exception as e:
        log.error("exploit_path_endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"exploit_path analysis failed: {str(e)}")


# Grade step endpoint
@api_v1.post("/grade_step", response_model=GradeResponse)
async def grade_step(request: GradeRequest):
    """
    Grade a single trainee action against the pre-authored expected actions for an incident.

    The LLM evaluates semantically — different wording or order that conveys the same intent
    counts as a match. Returns score (0-1), level, constructive feedback, matched and missed actions.

    Falls back to cosine-similarity grading if the LLM is unavailable.
    """
    try:
        if not llm_client:
            raise HTTPException(status_code=500, detail="LLM client not initialized")

        if not request.expected_actions:
            raise HTTPException(status_code=400, detail="expected_actions must not be empty")

        user_msg = build_grade_user_message(
            scenario_title=request.scenario_title,
            incident_title=request.incident_title,
            expected_actions=request.expected_actions,
            user_action=request.user_action,
        )

        used_fallback = False
        try:
            result: GradeLLMResult = llm_client.generate_structured_answer(
                query=user_msg,
                context="",
                response_model=GradeLLMResult,
                system_prompt=GRADE_SYSTEM_PROMPT,
            )
            log.info(
                "grade_step_llm_ok",
                incident=request.incident_title,
                score=result.score,
                level=result.level,
            )
        except Exception as e:
            log.warning("grade_step_llm_failed_fallback", error=str(e))
            result = cosine_fallback(request.expected_actions, request.user_action)
            used_fallback = True

        return GradeResponse(
            score=result.score,
            level=result.level,
            feedback=result.feedback,
            matched_actions=result.matched_actions,
            missed_actions=result.missed_actions,
            used_fallback=used_fallback,
        )

    except HTTPException:
        raise
    except Exception as e:
        log.error("grade_step_endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"grade_step failed: {str(e)}")


# Debrief endpoint
@api_v1.post("/debrief", response_model=DebriefResponse)
async def debrief(request: DebriefRequest):
    """
    Generate an end-of-simulation debrief report.

    Call this once when ``is_scenario_complete`` is True. Pass the full scenario and
    the ordered history of steps (incident index, title, user action, and optional
    grade score/level from grade_step).

    Returns overall score, level, narrative summary, strengths, gaps, and recommendations.
    Falls back to a simple average if the LLM is unavailable.
    """
    try:
        if not llm_client:
            raise HTTPException(status_code=500, detail="LLM client not initialized")

        if not request.history:
            raise HTTPException(status_code=400, detail="history must not be empty")

        user_msg = build_debrief_user_message(
            scenario=request.scenario,
            history=request.history,
        )

        used_fallback = False
        try:
            result: DebriefLLMResult = llm_client.generate_structured_answer(
                query=user_msg,
                context="",
                response_model=DebriefLLMResult,
                system_prompt=DEBRIEF_SYSTEM_PROMPT,
            )
            log.info(
                "debrief_llm_ok",
                scenario=request.scenario.scenario_title,
                overall_score=result.overall_score,
                overall_level=result.overall_level,
            )
        except Exception as e:
            log.warning("debrief_llm_failed_fallback", error=str(e))
            result = score_fallback(request.history)
            used_fallback = True

        return DebriefResponse(
            overall_score=result.overall_score,
            overall_level=result.overall_level,
            summary=result.summary,
            strengths=result.strengths,
            gaps=result.gaps,
            recommendations=result.recommendations,
            used_fallback=used_fallback,
        )

    except HTTPException:
        raise
    except Exception as e:
        log.error("debrief_endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"debrief failed: {str(e)}")


# Policy draft endpoint
@api_v1.post("/policy_draft", response_model=PolicyDraftResponse)
async def policy_draft(request: PolicyDraftRequest):
    """
    Generate a formal operational policy document from a scenario and optional simulation data.

    - If ``performance_data`` is provided (simulations_count > 0), the draft is
      evidence-based and references specific capability gaps identified during training.
    - If ``performance_data`` is omitted or empty, the draft is threat-based and relies
      solely on the scenario's threat profile.

    Returns a structured policy document suitable for review by LEAs and public authorities.
    """
    try:
        if not llm_client:
            raise HTTPException(status_code=500, detail="LLM client not initialized")

        user_msg = build_policy_draft_user_message(request)

        # ── RAG: retrieve authoritative SOP reference context ─────────────────
        sop_context = ""
        if retrieval_system:
            try:
                rag_query = build_policy_draft_rag_query(request)
                policy_sector = detect_sector(
                    f"{request.scenario.scenario_title} {rag_query}"
                )
                rag_results = retrieval_system.search(
                    query=rag_query,
                    top_k=8,
                    use_reranking=False,
                    use_hybrid=True,
                    sector_filter=policy_sector if policy_sector != "general" else None,
                )
                context_parts = [
                    r["content"]
                    for r in rag_results.get("results", [])
                    if r.get("content")
                ]
                sop_context = "\n\n---\n\n".join(context_parts)
                if sop_context:
                    log.info(
                        "policy_draft_rag_ok",
                        scenario=request.scenario.scenario_title,
                        chunks_retrieved=len(context_parts),
                    )
                else:
                    log.warning(
                        "policy_draft_rag_empty",
                        scenario=request.scenario.scenario_title,
                        hint="Run POST /api/v1/process to ingest data/sop_reference/ documents first.",
                    )
            except Exception as rag_err:
                log.warning("policy_draft_rag_failed", error=str(rag_err))

        used_fallback = False
        try:
            result: PolicyDraftLLMResult = llm_client.generate_structured_answer(
                query=user_msg,
                context=sop_context,
                response_model=PolicyDraftLLMResult,
                system_prompt=POLICY_DRAFT_SYSTEM_PROMPT,
            )
            log.info(
                "policy_draft_llm_ok",
                scenario=request.scenario.scenario_title,
                draft_type=result.draft_type,
            )
        except Exception as e:
            log.warning("policy_draft_llm_failed_fallback", error=str(e))
            result = _fallback_response(request)
            used_fallback = True

        # ── Post-generation hallucination checks ──────────────────────────────
        validation_warnings: list[str] = []
        try:
            validation_warnings = assert_no_hallucination(result)
            if validation_warnings:
                log.warning(
                    "policy_draft_validation_warnings",
                    scenario=request.scenario.scenario_title,
                    warnings=validation_warnings,
                )
        except Exception as val_err:
            log.error("policy_draft_validation_error", error=str(val_err))
            validation_warnings = [f"Validation check failed: {val_err}"]

        from datetime import timezone

        return PolicyDraftResponse(
            document_title=result.document_title,
            classification=result.classification,
            generated_at=datetime.now(timezone.utc).isoformat(),
            scenario_name=request.scenario.scenario_title,
            draft_type=result.draft_type,
            simulations_used=(
                request.performance_data.simulations_count
                if request.performance_data
                else 0
            ),
            management_commitment=result.management_commitment,
            purpose_and_scope=result.purpose_and_scope,
            incident_classification=result.incident_classification,
            executive_summary=result.executive_summary,
            identified_risks=result.identified_risks,
            detection_procedures=result.detection_procedures,
            containment_procedures=result.containment_procedures,
            evidence_preservation_steps=result.evidence_preservation_steps,
            escalation_chain=result.escalation_chain,
            external_reporting_obligations=result.external_reporting_obligations,
            preventive_controls=result.preventive_controls,
            administrative_controls=result.administrative_controls,
            roles_and_responsibilities=result.roles_and_responsibilities,
            policy_recommendations=result.policy_recommendations,
            resource_requirements=result.resource_requirements,
            review_cycle=result.review_cycle,
            used_fallback=used_fallback,
            validation_warnings=validation_warnings,
        )

    except HTTPException:
        raise
    except Exception as e:
        log.error("policy_draft_endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"policy_draft failed: {str(e)}")


# Ingest scenario endpoint
@api_v1.post("/ingest_scenario", response_model=IngestScenarioResponse)
async def ingest_scenario(request: IngestScenarioRequest):
    """
    Ingest a human-reviewed scenario into the RAG pipeline.

    Takes a scenario content (LLM-generated but human-reviewed), chunks it,
    generates embeddings, and stores it in the vector database for future retrieval.

    Steps:
    1. Validate and prepare scenario content
    2. Chunk the scenario text
    3. Generate dense and sparse embeddings
    4. Store in vector database (Qdrant) and metadata database (SQLite)
    """
    try:
        if not all([document_processor, embedding_service, vector_store]):
            raise HTTPException(status_code=500, detail="Services not initialized")

        log.debug(
            "ingest_scenario_request_received",
            request_data=request.dict(),
            content_preview=request.content,
        )

        sector = request.sector or detect_sector(request.content)
        log.info("scenario_ingestion_started", content_length=len(request.content), sector=sector)

        # Validate content
        if not request.content.strip():
            raise HTTPException(status_code=400, detail="Scenario content cannot be empty")

        # Generate a unique document ID based on content hash
        import hashlib
        from datetime import datetime

        content_hash = hashlib.md5(request.content.encode()).hexdigest()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        document_id = f"scenario_{timestamp}_{content_hash[:8]}"

        # Prepare metadata for chunking
        metadata = {
            "document_id": document_id,
            "file_name": f"scenario_{timestamp}.txt",
            "file_path": f"/ingested/scenarios/{document_id}.txt",
            "file_type": "scenario",
            "file_size": len(request.content),
            "sector": sector,
        }

        # Create DocumentChunk objects using the chunker

        chunks = document_processor.chunker.chunk_document(request.content, metadata)

        if not chunks:
            log.warning("no_chunks_created_from_scenario")
            raise HTTPException(
                status_code=400, detail="Failed to create chunks from scenario content"
            )

        # Update chunk metadata to reflect this is an ingested scenario
        for chunk in chunks:
            chunk.project_name = "ingested_scenarios"
            chunk.document_type = "scenario"

        # Generate embeddings for chunks
        chunk_contents = [chunk.content for chunk in chunks]
        embeddings = embedding_service.embed_documents(chunk_contents)

        # Generate sparse embeddings if available
        sparse_embeddings = None
        if sparse_embedding_service:
            try:
                sparse_embeddings = sparse_embedding_service.embed_documents(chunk_contents)
            except Exception as e:
                log.warning("sparse_embedding_failed_for_scenario", error=str(e))

        # Store chunks in vector database
        success = vector_store.add_chunks(chunks, embeddings, sparse_embeddings)

        if not success:
            raise HTTPException(
                status_code=500, detail="Failed to store scenario in vector database"
            )

        log.info(
            "scenario_ingested_successfully", document_id=document_id, chunks_created=len(chunks)
        )

        return IngestScenarioResponse(
            status="success",
            message=f"Scenario successfully ingested with {len(chunks)} chunks",
            document_id=document_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        log.error("ingest_scenario_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Scenario ingestion failed: {str(e)}")


# Get document by ID endpoint
@api_v1.get("/document/{document_id}", response_model=GetDocumentResponse)
async def get_document(document_id: str):
    """
    Retrieve a complete document by its ID.

    Returns the full content of the document by concatenating all its chunks
    in the correct order.

    Args:
        document_id: The document identifier (e.g., scenario_20251027_142544_04746b33)

    Returns:
        Document ID and full concatenated content
    """
    try:
        if not vector_store:
            raise HTTPException(status_code=500, detail="Vector store not initialized")

        log.info("get_document_request", document_id=document_id)

        # Get document content from vector store
        content = vector_store.get_document_content(document_id)

        if content is None:
            log.warning("document_not_found", document_id=document_id)
            raise HTTPException(
                status_code=404, detail=f"Document with ID '{document_id}' not found"
            )

        log.info("document_retrieved", document_id=document_id, content_length=len(content))

        return GetDocumentResponse(document_id=document_id, content=content)

    except HTTPException:
        raise
    except Exception as e:
        log.error("get_document_error", document_id=document_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve document: {str(e)}")


# Include v1 router in app
app.include_router(api_v1)
