# Backlog — Dynamic Next Step: Full Simulation Run

## Context

`POST /api/v1/next_step` τρέχει ήδη και υποστηρίζει:
- **`use_llm: false`** → γραμμικό default
- **`use_llm: true`** → LLM επιλέγει index από allowlist
- **`adapt_inject: true`** → δεύτερο LLM call που rewrite-άρει `description` + `inject`
  ώστε να αναγνωρίζει την πράξη του εκπαιδευόμενου

Αυτό που **λείπει** για πλήρη end-to-end simulation run με αξία:

---

## Τι θέλουμε να φτιάξουμε

### 1. End-to-End Simulation Runner (smoke test / dev tool)

**Τι είναι:**  
Script ή endpoint που δέχεται ένα `scenario` + λίστα `user_actions` (μία ανά incident)
και τρέχει ολόκληρο το σενάριο αυτόματα, τυπώνοντας κάθε βήμα.

**Ήδη υπάρχει** ως manual `python3 << 'PY'` script στο staging — χρειάζεται να γίνει
επίσημο αρχείο στο repo.

**Αρχείο:** `tests/dev/e2e_simulation_run.py`

**Input (hardcoded ή από αρχείο):**
```python
SCENARIO_FILE = "staging/sb_scenario_only.json"
USER_ACTIONS  = [
    "I called the CEO and issued a press statement...",
    "I blocked the entire subnet...",
    ...
]
```

**Output (stdout):**
- Κάθε βήμα: trainee action, chosen index, default index, match, adapted, rationale
- Adapted description + inject (truncated)
- Τελικά: visited indices, unseen indices

---

### 2. Σωστό state management για visited

**Πρόβλημα τώρα:**  
Το `visited_incident_indices` το κρατά ο client. Αν ο client ξεχάσει να προσθέσει
το `next_incident_index` που επέστρεψε το API, η ροή χαλάει.

**Κανόνας που πρέπει να τεκμηριωθεί σε docs (και να ελεγχθεί στο client):**
```
visited = visited + [next_incident_index]   # ΟΧΙ current+1
current = next_incident_index
```

**Αρχεία που αγγίζει:**
- `docs/BACKLOG.md` (αυτό το αρχείο) — τεκμηρίωση
- Frontend / BackEnd client που θα καλεί το endpoint

---

### 3. Grading / Rubric endpoint

**Τι είναι:**  
Μετά το τέλος του σεναρίου (ή ανά βήμα), να βαθμολογεί την απάντηση του εκπαιδευόμενου
με βάση τα `expected_actions` του incident (που ήταν κρυμμένα).

**Τι αλλάζει και πού:**

| Αρχείο | Τι προστίθεται |
|--------|---------------|
| `src/config/models.py` | `GradeRequest`, `GradeResult` (score, feedback, matched_actions, missed_actions) |
| `src/scenario/grader.py` | `grade_action(user_action, expected_actions, scenario_title)` — LLM structured call |
| `src/api/api.py` | `POST /api/v1/grade_step` |
| `tests/test_grader.py` | Unit tests χωρίς LLM (mock) |

**`GradeRequest`:**
```python
class GradeRequest(BaseModel):
    scenario_title: str
    incident_title: str
    expected_actions: List[str]   # από το predefined (κρυμμένα μέχρι τώρα)
    user_action: str
```

**`GradeResult`:**
```python
class GradeResult(BaseModel):
    score: float          # 0.0 - 1.0
    level: str            # "missing" | "partial" | "good" | "excellent"
    feedback: str         # εξήγηση για τον εκπαιδευόμενο
    matched_actions: List[str]   # expected actions που καλύφθηκαν
    missed_actions: List[str]    # expected actions που έλειψαν
```

**Grading logic (v1):**
- LLM structured call με σαφές system prompt: "βαθμολόγησε σύμφωνα με τα objectives,
  ΟΧΙ literal string matching — διαφορετική σειρά ή διαφορετική διατύπωση είναι OK"
- cosine similarity fallback αν LLM αποτύχει

---

### 4. History summary για adapt

**Πρόβλημα τώρα:**  
Το `build_adapt_user_message` δέχεται `history_summary=""` αλλά **δεν το χρησιμοποιεί**
πάντα — ο client δεν το στέλνει.

**Τι αλλάζει:**

| Αρχείο | Τι προστίθεται |
|--------|---------------|
| `src/config/models.py` | `history_summary: Optional[str]` στο `NextStepRequest` |
| `src/api/api.py` | Περνά `request.history_summary` στο `build_adapt_user_message` |

**Μορφή history_summary (client ευθύνη):**
```
Step 0: [isolated workstation, opened SOC ticket]
Step 1: [blocked outbound traffic]
```

---

### 5. "Scenario complete" debrief endpoint

**Τι είναι:**  
Όταν `is_scenario_complete: true`, να επιστρέφει **συνολική αξιολόγηση**:
ποια objectives καλύφθηκαν, ποια έλειψαν, τι θα μπορούσε να γίνει καλύτερα.

**Αρχείο:** `POST /api/v1/debrief`

**Input:** `scenario` + `history` (λίστα `{incident_index, user_action}`)

**Output:** `DebriefResult` (overall_score, strengths, gaps, recommendations)

---

## Σειρά υλοποίησης (priority)

| # | Task | Effort | Impact |
|---|------|--------|--------|
| 1 | `tests/dev/e2e_simulation_run.py` | Μικρό | Άμεσο testing |
| 2 | `history_summary` στο `NextStepRequest` | Πολύ μικρό | Καλύτερο adapt |
| 3 | `POST /api/v1/grade_step` | Μέτριο | Core grading |
| 4 | `POST /api/v1/debrief` | Μέτριο | End-of-run feedback |
| 5 | Client state management (visited rule) | Μικρό (docs) | Σταθερότητα |

---

## Σημείωση για το scoring

- **ΟΧΙ** Euclidean distance για embeddings — χρήση **cosine similarity**
- Grading βάσει **learning objectives** (ελεύθερο κείμενο), ΟΧΙ literal matching
- Διαφορετική σειρά ή συνώνυμη διατύπωση → **full credit**

---

## Αρχεία που δεν αγγίζουμε (out of scope αυτής της φάσης)

- Frontend (Scenario-Builder-FrontEnd-SB)
- Feedback loop / re-generation (αποφασίστηκε να αφεθεί για αργότερα)
- Branching graph (μόνο αν το προϊόν το απαιτήσει ρητά)
