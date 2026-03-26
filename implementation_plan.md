# Job Description Analyzer — Implementation Plan

A simple API that accepts a job posting and returns structured AI-extracted information using DSPy + OpenRouter.

---

## 1. High-Level Architecture

```
Client
  │
  ▼
FastAPI (main.py)
  │
  ▼
Router (router/job_router.py)
  │
  ▼
Service (services/job_service.py)
  │
  ▼
DSPy Module (dspy_modules/job_analyzer.py)
  │
  ▼
OpenRouter LLM (minimax/minimax-m2.5:free)
```

---

## 2. Folder Structure

```
jobpi/
├── main.py                        # FastAPI app entrypoint
├── config.py                      # DSPy + LLM setup
├── .env                           # API key (OPENROUTER_API_KEY)
├── requirements.txt
│
├── router/
│   └── job_router.py              # POST /analyze-job endpoint
│
├── services/
│   └── job_service.py             # Business logic, calls DSPy module
│
├── dspy_modules/
│   └── job_analyzer.py            # DSPy Signature + Module
│
└── schemas/
    ├── request.py                 # JobRequest model
    └── response.py                # JobAnalysis model
```

---

## 3. File-by-File Responsibilities

| File | Responsibility |
|------|---------------|
| `main.py` | Creates FastAPI app, includes router, sets up lifespan/startup |
| `config.py` | Loads env vars, configures `dspy.LM` with OpenRouter, calls `dspy.configure()` |
| `router/job_router.py` | Defines `POST /analyze-job`, validates input, calls service, returns response |
| `services/job_service.py` | Instantiates DSPy module, invokes it, maps output to `JobAnalysis` schema |
| `dspy_modules/job_analyzer.py` | Defines `JobAnalyzerSignature` and `JobAnalyzerModule` (a `dspy.Module`) |
| `schemas/request.py` | Pydantic `JobRequest` with `title`, `company`, `description` fields |
| `schemas/response.py` | Pydantic `JobAnalysis` with all output fields |
| `.env` | `OPENROUTER_API_KEY=...` |

---

## 4. DSPy Signature Design

```
Signature: JobAnalyzerSignature

Inputs:
  - title: str       → job title
  - company: str     → company name
  - description: str → full job description text

Outputs:
  - summary: str                → 2-3 sentence summary of the role
  - seniority: str              → "Junior" | "Mid" | "Senior" | "Lead" | "Executive"
  - role_type: str              → "Engineering" | "Design" | "Product" | "Sales" | etc.
  - skills: list[str]           → extracted technical/soft skills
  - responsibilities: list[str] → key responsibilities listed

Module: JobAnalyzerModule(dspy.Module)
  - Uses dspy.Predict(JobAnalyzerSignature)
  - Single forward() call, no chain-of-thought needed for MVP
```

---

## 5. Data Flow

```
1. Client sends POST /analyze-job
        { title, company, description }

2. Router validates input via JobRequest schema

3. Router calls job_service.analyze(request)

4. Service instantiates JobAnalyzerModule (or reuses singleton)

5. Module calls dspy.Predict with the three input fields

6. DSPy formats prompt → sends to OpenRouter (minimax-m2.5:free)

7. LLM response is parsed by DSPy into output fields

8. Service maps DSPy result → JobAnalysis Pydantic model

9. Router returns JobAnalysis as JSON response
```

---

## 6. API Schema Definitions

### Request — `schemas/request.py`
```
JobRequest:
  title:       str  (required)
  company:     str  (required)
  description: str  (required, min length ~50 chars)
```

### Response — `schemas/response.py`
```
JobAnalysis:
  summary:          str
  seniority:        str
  role_type:        str
  skills:           list[str]
  responsibilities: list[str]
```

---

## 7. Step-by-Step Build Plan

| Step | Task |
|------|------|
| 1 | Create folder structure and `requirements.txt` |
| 2 | Write `.env` with `OPENROUTER_API_KEY` |
| 3 | Implement `config.py` — load env, configure DSPy LM |
| 4 | Define `schemas/request.py` and `schemas/response.py` |
| 5 | Write `dspy_modules/job_analyzer.py` — Signature + Module |
| 6 | Implement `services/job_service.py` — call module, return schema |
| 7 | Implement `router/job_router.py` — endpoint wiring |
| 8 | Implement `main.py` — app creation, router include |
| 9 | Test with `uvicorn` + manual `curl`/Postman request |

---

## 8. Minimal MVP Scope

- Single endpoint: `POST /analyze-job`
- No auth, no DB, no caching
- No streaming
- Synchronous DSPy call (no async DSPy)
- No retries or fallback logic
- No tests (can be added post-MVP)

---

## 9. Future Improvements

- Add `async` support to service layer
- Cache results by description hash (Redis or in-memory)
- Add `/health` and `/docs` polish
- Add retry logic for LLM failures
- Add input sanitization / length limits
- Swap `dspy.Predict` for `dspy.ChainOfThought` for better accuracy
- Add unit tests with mocked DSPy module
- Add structured logging

---

## 10. Assumptions

- `OPENROUTER_API_KEY` is available in `.env`
- OpenRouter supports the `minimax/minimax-m2.5:free` model via OpenAI-compatible API
- DSPy is configured to use the OpenRouter base URL (`https://openrouter.ai/api/v1`)
- `skills` and `responsibilities` are returned as comma-separated strings by the LLM and parsed into lists (DSPy handles this via output field typing)
- No authentication is required on the API for MVP
- Python 3.11+ is the target runtime
