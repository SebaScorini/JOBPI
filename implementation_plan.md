# CV Library + Persistent Storage — Implementation Plan

Add SQLModel+SQLite persistence and a CV Library sidebar to the existing JOBPI AI Job Analyzer.

---

## 1. Feature Overview

**What it does:**
- Users upload CVs once; they are stored in SQLite and reused for all future analyses.
- A sidebar shows all saved CVs. Selecting a stored CV against a job offer returns a fit analysis without re-uploading.
- The system compares all stored CVs against a job and recommends the best match.

**User problem it solves:**
- Eliminates repeated PDF uploads for every analysis session.
- Makes it easy to compare multiple CV versions against the same job.

**MVP scope:**
- Upload & persist CV (name, cleaned text, SHA-256 hash for deduplication).
- List, retrieve, and delete stored CVs.
- Analyze a job description → persist the result.
- Match one stored CV against a stored job analysis → persist the match.
- Recommend the best stored CV for a given job (heuristic score, no extra model call).

---

## 2. Data Model Design

### `StoredCV`
**Purpose:** Persists a user's CV so PDF extraction never runs twice.

| Field | Type | Notes |
|---|---|---|
| [id](file:///c:/Users/cepita/Desktop/JOBPI/app/services/pdf_extractor.py#63-66) | `int` (PK, auto) | |
| `name` | `str` | User-provided label (e.g., "Senior Backend CV") |
| `file_hash` | `str` | SHA-256 of raw PDF bytes → deduplication key |
| `cleaned_text` | `str` | Output of [extract_cv_text()](file:///c:/Users/cepita/Desktop/JOBPI/app/services/pdf_extractor.py#31-61) → reused for model calls |
| `created_at` | `datetime` | |

**What to store:** Only the cleaned/trimmed text (≤800 chars, same as current `MAX_CV_CHARS`). No raw PDF bytes — saves storage, avoids re-extraction.

---

### [JobAnalysis](file:///c:/Users/cepita/Desktop/JOBPI/app/services/job_analyzer.py#17-35)
**Purpose:** Caches a completed job analysis so the same job is never re-analyzed.

| Field | Type | Notes |
|---|---|---|
| [id](file:///c:/Users/cepita/Desktop/JOBPI/app/services/pdf_extractor.py#63-66) | `int` (PK, auto) | |
| `job_hash` | `str` | SHA-256 of `title+company+cleaned_description` (reuse existing [_build_cache_key](file:///c:/Users/cepita/Desktop/JOBPI/app/services/job_analyzer.py#143-146)) |
| `title` | `str` | |
| `company` | `str` | |
| `cleaned_description` | `str` | Output of `clean_description()` |
| `result_json` | `str` | JSON-serialized `JobAnalysisResponse` |
| `created_at` | `datetime` | |

**Relationship:** One-to-many with `CVJobMatch`.

---

### `CVJobMatch`
**Purpose:** Stores the fit analysis between one stored CV and one job analysis.

| Field | Type | Notes |
|---|---|---|
| [id](file:///c:/Users/cepita/Desktop/JOBPI/app/services/pdf_extractor.py#63-66) | `int` (PK, auto) | |
| `cv_id` | `int` (FK → StoredCV) | |
| `job_id` | `int` (FK → JobAnalysis) | |
| `result_json` | `str` | JSON-serialized [CvAnalysisResponse](file:///c:/Users/cepita/Desktop/JOBPI/app/schemas/cv.py#4-12) |
| `heuristic_score` | `float` | 0.0–1.0 local keyword overlap score (no model call) |
| `created_at` | `datetime` | |

**Unique constraint:** [(cv_id, job_id)](file:///c:/Users/cepita/Desktop/JOBPI/app/services/cv_analyzer.py#39-45) — one match per pair.

---

## 3. Persistence Strategy

| Event | Action |
|---|---|
| CV uploaded | Extract text → compute hash → check for duplicate → insert `StoredCV` |
| Job analyzed | Clean description → compute hash → check [JobAnalysis](file:///c:/Users/cepita/Desktop/JOBPI/app/services/job_analyzer.py#17-35) → reuse or run model → upsert |
| CV matched to job | Check `CVJobMatch` for [(cv_id, job_id)](file:///c:/Users/cepita/Desktop/JOBPI/app/services/cv_analyzer.py#39-45) pair → reuse or run model → insert |
| Best CV recommendation | Query all `CVJobMatch` for `job_id` → rank by `heuristic_score` (local, no model) |

**Deduplication:**
- CVs: SHA-256 of raw PDF bytes. Same file = same hash = reject duplicate.
- Jobs: existing [_build_cache_key()](file:///c:/Users/cepita/Desktop/JOBPI/app/services/job_analyzer.py#143-146) hash → now persisted to DB instead of just in-memory dict.

**What is NOT stored:**
- Raw PDF bytes.
- The in-memory [_cache](file:///c:/Users/cepita/Desktop/JOBPI/app/services/job_analyzer.py#143-146) dict in [JobAnalyzerService](file:///c:/Users/cepita/Desktop/JOBPI/app/services/job_analyzer.py#46-98) remains as a hot first-level cache; DB is the persistent second level.

---

## 4. Backend Architecture Changes

### New files

| File | Purpose |
|---|---|
| `app/db/database.py` | SQLite engine + `create_db_and_tables()` startup routine |
| `app/db/models.py` | SQLModel table definitions (`StoredCV`, [JobAnalysis](file:///c:/Users/cepita/Desktop/JOBPI/app/services/job_analyzer.py#17-35), `CVJobMatch`) |
| `app/db/crud.py` | All DB read/write functions (no business logic) |
| `app/api/routes/library.py` | New router for CV library endpoints |
| `app/services/cv_library_service.py` | Orchestration: PDF → DB, CV-job matching, recommendation logic |

### Modified files

| File | Change |
|---|---|
| [app/main.py](file:///c:/Users/cepita/Desktop/JOBPI/app/main.py) | Call `create_db_and_tables()` on startup; include `library_router` |
| [app/core/config.py](file:///c:/Users/cepita/Desktop/JOBPI/app/core/config.py) | Add `database_url: str` setting (default `sqlite:///./jobpi.db`) |
| [app/services/job_analyzer.py](file:///c:/Users/cepita/Desktop/JOBPI/app/services/job_analyzer.py) | After model call, persist [JobAnalysis](file:///c:/Users/cepita/Desktop/JOBPI/app/services/job_analyzer.py#17-35) to DB (via `crud`); on request, check DB before in-memory cache |
| [app/api/routes/cv.py](file:///c:/Users/cepita/Desktop/JOBPI/app/api/routes/cv.py) | Keep existing ad-hoc analyze endpoint; it stays stateless (no DB) for direct upload+analyze use case |

### Layering rule
`routes` → [service](file:///c:/Users/cepita/Desktop/JOBPI/app/services/cv_analyzer.py#122-127) → `crud` → DB. Services never import `crud` directly from routes; routes call services only.

---

## 5. API Design Changes

### CV Library Endpoints (`/library`)

| Method | Route | Request | Response | Purpose |
|---|---|---|---|---|
| `POST` | `/library/cvs` | `multipart/form-data` (file + `name: str`) | `StoredCVRead` | Upload & persist a CV |
| `GET` | `/library/cvs` | — | `list[StoredCVRead]` | List all stored CVs |
| `GET` | `/library/cvs/{cv_id}` | — | `StoredCVRead` | Get one CV metadata |
| `DELETE` | `/library/cvs/{cv_id}` | — | `{"ok": true}` | Delete a stored CV |
| `POST` | `/library/match` | `{"cv_id": int, "job_id": int}` | `CVJobMatchRead` | Analyze fit between stored CV + job |
| `GET` | `/library/recommend/{job_id}` | — | `RecommendationRead` | Return best CV for a job |

### `StoredCVRead` response shape
```json
{ "id": 1, "name": "Senior Backend CV", "created_at": "2026-03-25T..." }
```
*Never return `cleaned_text` in list endpoints — keep payloads small.*

### `CVJobMatchRead` response shape
```json
{
  "id": 5,
  "cv_id": 1,
  "job_id": 3,
  "heuristic_score": 0.74,
  "result": { ...CvAnalysisResponse fields... },
  "created_at": "..."
}
```

### `RecommendationRead` response shape
```json
{
  "best_cv": { "id": 1, "name": "Senior Backend CV" },
  "score": 0.74,
  "matches": [ { "cv_id": 1, "score": 0.74 }, { "cv_id": 2, "score": 0.51 } ]
}
```

### Existing endpoints (unchanged)
- `POST /jobs/analyze` — stateless job analysis (still works standalone; now also persists [JobAnalysis](file:///c:/Users/cepita/Desktop/JOBPI/app/services/job_analyzer.py#17-35) as side-effect).
- `POST /cv/analyze` — stateless CV fit (no DB, for quick one-off uploads).

---

## 6. Frontend Changes

### Layout
Split the current single-column layout into a **two-panel layout**:
- **Left sidebar (CV Library):** ~250 px, lists stored CVs, upload button at the top.
- **Right main area:** existing job analysis + CV fit result panels.

### CV Sidebar component (`CVSidebar.tsx`)
- Fetch `GET /library/cvs` on mount.
- Show each CV as a card: name + upload date + delete icon.
- "Upload New CV" button → file picker → `POST /library/cvs` with a name input.
- Clicking a CV card sets it as the "active CV" in global state (React context or simple `useState` lifted to [App.tsx](file:///c:/Users/cepita/Desktop/JOBPI/frontend/src/App.tsx)).

### Job analysis flow (updated)
1. User submits job description → `POST /jobs/analyze` → result displayed as now.
2. If an active CV is selected in the sidebar → automatically trigger `POST /library/match` with `{cv_id, job_id}` → display fit analysis.
3. "Find best CV" button → `GET /library/recommend/{job_id}` → highlight recommended CV in sidebar.

### New component: `CVMatchResult.tsx`
- Reuses existing display logic from the current CV fit panel.
- Adds a "recommended" badge when this CV is the top pick.

### No routing changes needed — single-page layout is sufficient for MVP.

---

## 7. Data Flow

### CV Upload → Persist
```
User uploads PDF + name
  → POST /library/cvs
    → cv_library_service.upload_cv()
      → pdf_extractor.extract_cv_text(bytes)   [validates, cleans, truncates]
      → compute SHA-256 of raw bytes
      → crud.get_cv_by_hash()                  [duplicate check]
      → crud.create_cv(name, hash, cleaned_text)
    → return StoredCVRead
```

### Job Analysis → Persist
```
POST /jobs/analyze
  → job_analyzer_service.analyze()
    → check in-memory cache (hit → return)
    → check crud.get_job_by_hash() (hit → deserialize → return)
    → run DSPy model
    → crud.create_job_analysis(hash, title, company, desc, result_json)
    → store in in-memory cache
  → return JobAnalysisResponse
```

### CV-Job Match → Persist
```
POST /library/match { cv_id, job_id }
  → cv_library_service.match()
    → crud.get_cv(cv_id), crud.get_job(job_id)
    → crud.get_match(cv_id, job_id) (hit → return cached)
    → cv_analyzer_service.analyze(job_title, job_desc, cv_cleaned_text)
    → compute heuristic_score (local keyword overlap, see §8)
    → crud.create_match(cv_id, job_id, result_json, heuristic_score)
  → return CVJobMatchRead
```

### Best CV Recommendation
```
GET /library/recommend/{job_id}
  → crud.get_all_matches_for_job(job_id)
    → if no matches yet: 400 "Run at least one match first"
  → sort by heuristic_score desc
  → return top cv + full ranked list
```

---

## 8. Performance Strategy

### Reduce repeated inference
- **DB-level job cache:** [JobAnalysis](file:///c:/Users/cepita/Desktop/JOBPI/app/services/job_analyzer.py#17-35) persists across restarts (the current in-memory dict resets on every restart). DB check runs before model call.
- **CV-job match cache:** `CVJobMatch` with unique [(cv_id, job_id)](file:///c:/Users/cepita/Desktop/JOBPI/app/services/cv_analyzer.py#39-45) constraint. Re-requesting the same pair returns instantly from DB.

### Reuse stored summaries
- `cleaned_text` in `StoredCV` is already the trimmed 800-char excerpt — no PDF re-extraction ever needed.
- `result_json` in [JobAnalysis](file:///c:/Users/cepita/Desktop/JOBPI/app/services/job_analyzer.py#17-35) and `CVJobMatch` are cached structured results — deserialization is O(μs).

### Minimize token usage during CV-job matching
- CV text is already capped at 800 chars by `pdf_extractor._truncate_cv()`.
- Job description sent to the match model uses the already-cleaned `cleaned_description` stored in [JobAnalysis](file:///c:/Users/cepita/Desktop/JOBPI/app/services/job_analyzer.py#17-35), not the original raw input.
- The [CvFitSignature](file:///c:/Users/cepita/Desktop/JOBPI/app/services/cv_analyzer.py#18-32) already uses minimal output fields (≤4 items per list, ≤180 char summary).

### Heuristic vs. model
| Task | Approach |
|---|---|
| Best CV ranking | **Heuristic only** — keyword overlap between `cleaned_text` and `cleaned_description`; no model call |
| CV-job fit analysis | **Model** — [CvAnalyzerService](file:///c:/Users/cepita/Desktop/JOBPI/app/services/cv_analyzer.py#47-91) (cached per pair) |
| Job analysis | **Model** — [JobAnalyzerService](file:///c:/Users/cepita/Desktop/JOBPI/app/services/job_analyzer.py#46-98) (cached per hash) |

**Heuristic score formula (local):** tokenize both cleaned texts → compute Jaccard similarity on word sets → normalize to 0.0–1.0. Runs in microseconds, no network call.

---

## 9. Step-by-Step Implementation Plan

1. **Add `sqlmodel` to [requirements.txt](file:///c:/Users/cepita/Desktop/JOBPI/requirements.txt).**
2. **Create `app/db/models.py`** — define `StoredCV`, [JobAnalysis](file:///c:/Users/cepita/Desktop/JOBPI/app/services/job_analyzer.py#17-35), `CVJobMatch` as SQLModel tables.
3. **Create `app/db/database.py`** — engine setup using `DATABASE_URL` from config; `create_db_and_tables()` function; `get_session()` dependency.
4. **Add `database_url` to [Settings](file:///c:/Users/cepita/Desktop/JOBPI/app/core/config.py#13-22) in [app/core/config.py](file:///c:/Users/cepita/Desktop/JOBPI/app/core/config.py).**
5. **Create `app/db/crud.py`** — thin CRUD functions: `create_cv`, `get_cv_by_hash`, `get_all_cvs`, [get_cv](file:///c:/Users/cepita/Desktop/JOBPI/app/services/cv_analyzer.py#122-127), `delete_cv`, `create_job_analysis`, `get_job_by_hash`, [get_job](file:///c:/Users/cepita/Desktop/JOBPI/app/services/job_analyzer.py#151-156), `create_match`, `get_match`, `get_all_matches_for_job`.
6. **Create Pydantic read schemas** in `app/schemas/library.py` — `StoredCVRead`, `CVJobMatchRead`, `RecommendationRead`.
7. **Create `app/services/cv_library_service.py`** — `upload_cv()`, `match_cv_to_job()`, `recommend_best_cv()`, `compute_heuristic_score()`.
8. **Modify [app/services/job_analyzer.py](file:///c:/Users/cepita/Desktop/JOBPI/app/services/job_analyzer.py)** — after model call, persist to [JobAnalysis](file:///c:/Users/cepita/Desktop/JOBPI/app/services/job_analyzer.py#17-35); check DB before in-memory cache on incoming requests.
9. **Create `app/api/routes/library.py`** — wire all 6 new endpoints; inject `get_session`.
10. **Modify [app/main.py](file:///c:/Users/cepita/Desktop/JOBPI/app/main.py)** — call `create_db_and_tables()` in a `lifespan` handler; include `library_router`.
11. **Frontend — `CVSidebar.tsx`** — CV list, upload modal, delete action.
12. **Frontend — update [App.tsx](file:///c:/Users/cepita/Desktop/JOBPI/frontend/src/App.tsx)** — two-panel layout, active CV state, auto-trigger match after job analysis.
13. **Frontend — `CVMatchResult.tsx`** — reuse existing fit display, add recommendation badge.
14. **Frontend — `api.ts` service updates** — add library API calls.
15. **Manual smoke test** (see §Validation below).

---

## 10. Validation and Error Handling

| Scenario | Handling |
|---|---|
| Uploaded file is not a PDF | `pdf_extractor._validate_magic_bytes()` raises `ValueError` → return `422 Unprocessable Entity` |
| PDF is scanned/image-only | [extract_cv_text](file:///c:/Users/cepita/Desktop/JOBPI/app/services/pdf_extractor.py#31-61) raises `ValueError("Could not extract text...")` → `422` |
| Duplicate CV (same hash) | `crud.get_cv_by_hash()` finds existing → return `409 Conflict` with existing CV id |
| Very long CV | Existing [_truncate_cv()](file:///c:/Users/cepita/Desktop/JOBPI/app/services/pdf_extractor.py#160-170) caps at 800 chars — no change needed |
| Very long job description | Existing `clean_description()` in [job_preprocessing.py](file:///c:/Users/cepita/Desktop/JOBPI/app/services/job_preprocessing.py) already handles this |
| CV [id](file:///c:/Users/cepita/Desktop/JOBPI/app/services/pdf_extractor.py#63-66) not found | `crud.get_cv()` returns `None` → route raises `404` |
| Job [id](file:///c:/Users/cepita/Desktop/JOBPI/app/services/pdf_extractor.py#63-66) not found | Same pattern — `404` |
| Match already exists | `crud.get_match()` hit → return cached result (not an error) |
| No matches for recommendation | Return `400` with message: "No CV matches found for this job. Run /library/match first." |
| DB write failure | Let SQLAlchemy exception bubble up → FastAPI returns `500` with logged traceback |

---

## 11. Portfolio Quality Considerations

- **Clean layering:** routes → services → crud → DB. No cross-layer imports. Easy to explain in an interview.
- **Single responsibility:** `crud.py` is pure DB I/O; services own orchestration; routes own HTTP concerns only.
- **Minimal surface area:** only 6 new endpoints, 3 new models, 3 new files. Easy to navigate.
- **No magic:** SQLModel is intuitive for anyone knowing SQLAlchemy + Pydantic. Good talking point.
- **Demo-friendly:** The sidebar + "find best CV" button tells a compelling story in a 2-minute demo.
- **No auth complexity:** keeps the demo flow fast and focused on the AI features.
- **`jobpi.db` in [.gitignore](file:///c:/Users/cepita/Desktop/JOBPI/.gitignore)** — keep the repo clean; reviewers clone and get a fresh DB on first run.

---

## 12. Future Improvements (Post-MVP, Optional)

- Full-text search over stored CVs (SQLite FTS5).
- CV versioning (same name, multiple uploads, diff view).
- Export match report as PDF.
- Pagination for CV list and match history.
- JWT-based user isolation (each user sees only their CVs).
- Background re-analysis when model or prompt changes (Celery/ARQ worker).
- Vector embedding similarity for smarter CV-job matching (SQLite + sqlite-vss or pgvector).
