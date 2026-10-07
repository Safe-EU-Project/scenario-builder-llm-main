"""
LLM client for generating answers based on retrieved context.
"""

import json
import time
from typing import Dict, List, Type, TypeVar
from urllib.parse import urlparse

import requests
import structlog
from openai import OpenAI
from pydantic import BaseModel

from ..config.settings import settings

# Type variable for generic Pydantic models
T = TypeVar("T", bound=BaseModel)

log = structlog.get_logger()


class LLMClient:
    """
    Client for calling open-source LLM APIs.

    Generates answers based on system prompts, context, and user queries.
    """

    def __init__(
        self,
        api_url: str = None,
        model: str = None,
        temperature: float = None,
        seed: int = None,
        stream: bool = None,
    ):
        """
        Initialize LLM client.

        Args:
            api_url: LLM API endpoint
            model: Model name to use
            temperature: Temperature for response generation
            seed: Seed for deterministic results
            stream: Whether to use streaming mode
        """
        self.api_url = api_url or settings.llm_api_url
        self.model = model or settings.llm_model
        self.temperature = temperature if temperature is not None else settings.llm_temperature
        self.seed = seed if seed is not None else settings.llm_seed
        self.stream = stream if stream is not None else settings.llm_stream
        self.keep_alive = settings.llm_keep_alive

        # Initialize OpenAI client for structured output
        # Extract base URL properly: http://host:port/v1/chat/completions -> http://host:port/v1
        base_url = self.api_url
        if "/chat/completions" in base_url:
            base_url = base_url.split("/chat/completions")[0]
        elif not base_url.endswith("/v1"):
            base_url = base_url.rstrip("/") + "/v1"

        self.openai_client = OpenAI(
            base_url=base_url, api_key="ollama"  # Ollama doesn't require a real API key
        )

        log.info(
            "llm_client_initialized",
            api_url=self.api_url,
            model=self.model,
            temperature=self.temperature,
            keep_alive=self.keep_alive,
        )

    def _ollama_origin(self) -> str:
        """http://host:11435/v1/chat/completions -> http://host:11435"""
        parsed = urlparse(self.api_url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def is_model_loaded(self) -> bool:
        """True when Ollama already has this model in memory."""
        url = f"{self._ollama_origin()}/api/ps"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        wanted = self.model.strip()
        for item in response.json().get("models") or []:
            loaded = (item.get("model") or item.get("name") or "").strip()
            if loaded == wanted or loaded.startswith(wanted + ":"):
                return True
        return False

    def warmup(self) -> None:
        """Load the model and pin it in memory with a one-token generate."""
        url = f"{self._ollama_origin()}/api/generate"
        payload = {
            "model": self.model,
            "prompt": "ok",
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {"num_predict": 1, "temperature": 0},
        }
        started = time.perf_counter()
        response = requests.post(url, json=payload, timeout=180)
        response.raise_for_status()
        log.info(
            "llm_warmup_ok",
            model=self.model,
            elapsed_s=round(time.perf_counter() - started, 1),
            keep_alive=self.keep_alive,
        )

    def generate_answer(self, query: str, context: str, system_prompt: str = None) -> str:
        """
        Generate an answer using the LLM.

        Args:
            query: User query
            context: Retrieved context from documents
            system_prompt: System prompt (optional)

        Returns:
            Generated answer from LLM
        """
        try:
            # Build messages
            messages = []

            # Add system prompt
            if system_prompt:
                messages.append({"role": "user", "content": system_prompt})
            else:
                # Default system prompt
                messages.append({"role": "user", "content": self._get_default_system_prompt()})

            # Add context as a system message
            messages.append({"role": "user", "content": f"Context:\n{context}"})

            # Add user query
            messages.append({"role": "user", "content": query})

            # Call LLM
            answer = self._call_llm(messages)

            log.info(
                "answer_generated",
                query_length=len(query),
                context_length=len(context),
                answer_length=len(answer),
            )

            return answer

        except Exception as e:
            log.error("answer_generation_error", query=query[:100], error=str(e))
            return f"Error generating answer: {str(e)}"

    def generate_structured_answer(
        self, query: str, context: str, response_model: Type[T], system_prompt: str = None
    ) -> T:
        """
        Generate a structured answer using the LLM with Pydantic model validation.

        This method uses OpenAI SDK's beta.chat.completions.parse to ensure
        the LLM returns a response that conforms to the provided Pydantic model.

        Args:
            query: User query
            context: Retrieved context from documents
            response_model: Pydantic model class to structure the response
            system_prompt: System prompt (optional)

        Returns:
            Instance of the provided Pydantic model with validated data

        Raises:
            Exception: For errors during generation
        """
        try:
            # Build messages - combine system prompt and context into one system message
            messages = []

            # Build combined system message
            system_content = (
                system_prompt if system_prompt else self._get_structured_incident_system_prompt()
            )
            system_content += f"\n\n---\n\nContext:\n{context}"

            messages.append({"role": "system", "content": system_content})

            # Add user query
            messages.append({"role": "user", "content": query})

            # Call LLM with structured output enabled using OpenAI SDK
            validated_response = self._call_llm_structured(messages, response_model)

            log.info(
                "structured_answer_generated",
                query_length=len(query),
                context_length=len(context),
                model=response_model.__name__,
            )

            return validated_response

        except Exception as e:
            log.error(
                "structured_answer_generation_error",
                query=query[:100],
                model=response_model.__name__,
                error=str(e),
            )
            raise

    def iter_structured_content(
        self, query: str, context: str, response_model: Type[T], system_prompt: str = None
    ):
        """Yield content tokens for a structured response, same schema as generate_structured_answer."""
        system_content = (
            system_prompt if system_prompt else self._get_structured_incident_system_prompt()
        )
        system_content += f"\n\n---\n\nContext:\n{context}"
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": query},
        ]
        schema = response_model.model_json_schema()
        stream = self.openai_client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            stream=True,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": response_model.__name__, "schema": schema},
            },
            extra_body={"keep_alive": self.keep_alive},
        )
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            text = getattr(delta, "content", None) if delta else None
            if text:
                yield text

    def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """
        Call the OpenAI-compatible LLM API (/v1/chat/completions endpoint).

        Args:
            messages: List of message dictionaries with role and content

        Returns:
            Generated response content
        """
        # OpenAI-compatible payload format
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "seed": self.seed,
            "stream": self.stream,
            "keep_alive": self.keep_alive,
        }

        log.debug("llm_request", payload=json.dumps(payload, indent=2))

        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=60)

            if response.status_code == 200:
                data = response.json()

                # OpenAI-compatible response format
                # Expected structure: {"choices": [{"message": {"content": "..."}}]}
                choices = data.get("choices", [])
                if choices and len(choices) > 0:
                    message = choices[0].get("message", {})
                    content = message.get("content", "No response content")
                else:
                    content = "No response content in API response"

                log.debug("llm_response", response=data)

                return content
            else:
                error_msg = f"LLM API Error: {response.status_code}\n{response.text}"
                log.error("llm_api_error", status_code=response.status_code, response=response.text)
                return error_msg

        except requests.exceptions.Timeout:
            error_msg = "LLM API request timed out"
            log.error("llm_timeout")
            return error_msg

        except Exception as e:
            error_msg = f"An error occurred calling LLM: {str(e)}"
            log.error("llm_call_error", error=str(e))
            return error_msg

    def _call_llm_structured(self, messages: List[Dict[str, str]], response_model: Type[T]) -> T:
        """
        Call the LLM API with structured output using OpenAI SDK's beta.chat.completions.parse.

        Args:
            messages: List of message dictionaries with role and content
            response_model: Pydantic model class to structure the response

        Returns:
            Instance of the provided Pydantic model with validated data

        Raises:
            Exception: For errors during generation
        """
        try:
            log.debug(
                "llm_structured_request",
                model=self.model,
                messages=messages,
                response_model=response_model.__name__,
            )

            # Use OpenAI SDK's structured output feature
            completion = self.openai_client.beta.chat.completions.parse(
                model=self.model,
                messages=messages,
                response_format=response_model,
                temperature=self.temperature,
                extra_body={"keep_alive": self.keep_alive},
            )

            message = completion.choices[0].message

            if message.parsed:
                log.debug("llm_structured_response_success", model=response_model.__name__)
                return message.parsed
            elif message.refusal:
                error_msg = f"LLM refused to generate response: {message.refusal}"
                log.error("llm_structured_refusal", refusal=message.refusal)
                raise Exception(error_msg)
            else:
                error_msg = "LLM returned empty response"
                log.error("llm_structured_empty_response")
                raise Exception(error_msg)

        except Exception as e:
            error_msg = f"An error occurred calling LLM with structured output: {str(e)}"
            log.error("llm_structured_call_error", error=str(e))
            raise

    def _get_structured_incident_system_prompt(self) -> str:
        """
        Get system prompt specifically for structured scenario generation.

        Returns:
            System prompt for structured scenario output
        """
        return """You are the Scenario Generator Agent, an AI specialized in creating structured, realistic training scenarios for cybersecurity and crisis exercises.

**Your Task:**
Analyze the provided context from previous scenarios or incident reports and generate a complete, structured scenario with multiple incidents that follows the structured response format.

**Response Structure:**
Your output will be automatically validated against a strict schema. You must provide:

• title: A concise, descriptive scenario title (5-15 words) summarizing the overall incident or crisis
  Example: "Data Integrity Attack on Financial Institution"

• incidents: A list of 8-12 incident objects, each containing:

  - title: Brief descriptive title of this specific incident (5-10 words)
    Example: "SIEM Alert: Unusual Database Activity Detected"

  - message_timestamp: Time notation in "T+X (HH:MM)" format showing progression
    Example: "T+0 (09:00)", "T+15 (09:15)", "T+30 (09:30)"

  - description: Clear explanation of what is happening at this moment (2-4 sentences) covering:
    • What happened
    • Why it's significant
    • What indicators are present

  - inject: The actual artifact/stimulus presented to trainees - must be realistic and actionable
    Examples: Complete email body, specific log entries, alert notifications, ticket excerpts, media inquiries

  - expected_actions: List of 3-5 concrete, measurable actions using imperative verbs
    Examples: "Verify the SIEM alert against known false positives", "Isolate affected systems from the network", "Notify the incident response team lead"

**Scenario Progression Requirements:**
Your scenario must:
- Contain roughly 8-12 injects, covering 90-120 minutes of simulated time
- Escalate in severity and complexity as the scenario progresses
- Mix technical, communication, and external pressure injects
- Be internally consistent (later injects build naturally on earlier ones)
- Follow a realistic timeline with appropriate intervals (typically 5-15 minutes between incidents)

**Key Principles:**

1. Be Professional: Use terminology appropriate for cybersecurity and crisis management professionals

2. Be Realistic: Base all content on actual incident response procedures and real-world scenarios

3. Be Specific: Each inject must contain actual content trainees would see, not just a description of it

4. Be Actionable: Expected actions must be specific enough to be measurable during training evaluation

5. Create Escalation: Start with initial detection/alerts, progress through investigation, escalate to broader impact, include external pressures (media, regulators, customers)

6. Use Context Wisely: Draw insights from the provided context to inform your response, but create original content that fits the scenario

7. Maintain Coherence: Ensure all incidents form a logically consistent scenario where each event naturally follows from previous ones"""

    def _get_default_system_prompt(self) -> str:
        """
        Get default system prompt for the LLM.

        Returns:
            Default system prompt
        """
        return """### **Role & Identity**

You are the **Scenario Generator Agent**, an advanced AI simulation designer that creates **structured, realistic training scenarios** for crisis and cyber exercises.  
You operate as part of a **Retrieval-Augmented Generation (RAG)** pipeline, which provides you with **chunks** of relevant text — extracted from previous scenarios, reports, or reference documents.

Your task is to **analyse**, **synthesise**, and **expand** upon those fragments to produce a **complete, coherent, and novel scenario** that adheres to a fixed structure and realistic tone.

---

### **Core Objective**

Given:

1. Several **RAG context chunks** (short fragments of related scenarios or documentation), and
    
2. Optional **metadata or user parameters** (sector, exercise duration, focus area, etc.),
    

generate **one new scenario** that:

- Matches the _tone, structure, and level of operational realism_ seen in the retrieved fragments,
    
- Adheres to the required **Scenario Template**, and
    
- Introduces _original_ content that remains _consistent_ with the retrieved context.
    

---

### **Scenario Template**

You must follow this template structure EXACTLY. The template consists of three main sections:

#### **1. Scenario Title**

A concise, descriptive title summarising the incident or crisis.

Example format:
```
Scenario Title
Data Integrity Attack on FinCorp Bank
```

---

#### **2. Timeline of Injects & Events**

This section must start with the heading "Timeline of Injects & Events" followed by chronologically ordered injects.

Each inject must follow this exact structure:

**Format:**
```
T+<offset> (<time>) – <Event Summary Label>

<Event narrative describing what is happening at this moment>

Inject: <The actual artefact or stimulus shown to trainees>
```

**Example:**
```
T+15 (09:15) – Customer Complaints: "Unusual transfer to unknown account"

The customer service team begins receiving multiple calls from retail banking customers reporting unexpected fund transfers. The affected accounts show wire transfers to unrecognized external accounts, with amounts ranging from €2,000 to €15,000. Initial checks suggest the transactions passed standard fraud detection rules.

Inject: Support ticket excerpt: "Customer ID: 4472819. Reports unauthorized wire transfer of €8,500 to account ending in 7392. Customer claims they never initiated this transaction. Transaction timestamp: 08:47 UTC. No MFA challenges were triggered."
```

The timeline should:

- Contain roughly **8–12 injects**, covering **90–120 minutes** of simulated time.
- Escalate in severity and complexity.
- Mix technical, communication, and external pressure injects.
- Be internally consistent (later injects build naturally on earlier ones).

---

#### **3. Expected Actions & Decision Points**

This section must start with the heading "Expected Actions & Decision Points" followed by phases corresponding 1-1 with each inject in the Timeline.

**CRITICAL:** There must be exactly one phase per inject/event, in the same order as the Timeline.

Each phase must follow this exact structure:

**Format:**
```
Phase <number> – <Title matching the inject event>
Expected Actions: <Description of what trainees should be doing>
```

**Example:**
```
Phase 2 – Customer Complaints
Expected Actions: Review the ticket details, isolate the affected accounts, and flag the transactions for audit. Begin preliminary investigation to determine if this is an isolated incident or part of a larger pattern. Notify the fraud investigation team and prepare to escalate if additional cases emerge.
```

**Another example:**
```
Phase 5 – External Media Inquiry
Expected Actions: Coordinate with the communications team to prepare a holding statement. Avoid confirming or denying specific details until the investigation progresses. Ensure internal stakeholders are aligned on messaging before any public response is issued.
```  

---

### **How to Use RAG Context Chunks**

You will receive multiple RAG text chunks, which may include:

- Partial scenario descriptions (single injects or event sequences)
    
- Segments of “Expected Actions” sections
    
- Contextual notes about threats, sectors, or procedures
    
- Fragments from incident reports, news articles, or other reference texts
    

You must:

1. **Read and infer structure:** Identify what kind of fragment each chunk represents (inject description, expected action, narrative background, etc.).
    
2. **Extract key ideas:** Note key patterns (sector, incident type, inject pacing, communication styles, technical realism).
    
3. **Generalise, not copy:**
    
    - Do **not** reuse specific entity names or sentences verbatim.
        
    - Instead, extract _underlying structures_ (e.g. “early alert inject”, “escalation event”, “leadership communication challenge”).
        
4. **Synthesize new content:** Use the extracted patterns to build a _new_, _fully fleshed-out_ scenario that fits the structure and tone of professional exercises.
    
5. **Integrate naturally:** References from different chunks should be merged into a single coherent storyline. Resolve inconsistencies and fill in logical gaps.
    

---

### **Stylistic & Structural Rules**

1. **Tone:** Use concise, factual, and operational language suitable for professional crisis training.
    
2. **Coherence:** Each inject must logically follow the previous ones; causal continuity is required.
    
3. **Pacing:** Escalate gradually; early injects are diagnostic, later ones force decisions.
    
4. **Clarity:** No markdown symbols or formatting codes — use only clear section headings and spacing. **Do not use markdown tables in your response.**

5. **Originality:** The final scenario must be _new_ while _structurally familiar_. Never reuse full sentences from RAG context chunks.
    
6. **Realism:** Injects should feel grounded (logs, tickets, calls, emails, briefings, press inquiries, etc.).
    
7. **Evaluation readiness:** Ensure _Expected Actions & Decision Points_ are written so evaluators can assess both operational and communication decisions.
    

---

### **Operational Process**

When generating, follow these steps internally:

1. **Ingest RAG chunks.** Identify recurring scenario elements and tone.
    
2. **Infer domain and scale.** Determine likely sector, incident type, and time scope.
    
3. **Outline structure.** Decide on 8–12 injects and a coherent escalation path.
    
4. **Draft timeline.** Write each inject as a cause-effect step with a matching artefact (inject).
    
5. **Design decision phases.** Ensure a 1-1 mapping: one phase per inject/event, in the same order, with realistic expected actions for each.
    
6. **Validate coherence.** Check that timestamps, events, and responses flow logically.
    
7. **Output full scenario** using the exact template."""
