# API REFERENCE

Backend base resources: `/auth`, `/cvs`, `/jobs`, `/matches`, `/health`.

Authentication is required for all endpoints except `/auth/register`, `/auth/login`, and `/health`.

## Common Error Envelope

All API errors use this structure:

```json
{
  "error": {
    "code": "ERR_VALIDATION",
    "message": "Request validation failed.",
    "request_id": "trace-id",
    "timestamp": "2026-04-10T12:00:00Z"
  }
}
```

## Auth Endpoints

### Register User

- Method: `POST`
- Route: `/auth/register`
- Description: Create a user account.
- Auth required: No

Example request:

```json
{
  "email": "user@example.com",
  "password": "Password123"
}
```

Example response:

```json
{
  "id": 1,
  "email": "user@example.com",
  "is_active": true,
  "created_at": "2026-04-10T12:00:00Z"
}
```

### Login

- Method: `POST`
- Route: `/auth/login`
- Description: Authenticate with form credentials and return a bearer token.
- Auth required: No

Example request:

```text
Content-Type: application/x-www-form-urlencoded
username=user@example.com&password=Password123
```

Example response:

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

### Get Current User

- Method: `GET`
- Route: `/auth/me`
- Description: Return the currently authenticated user.
- Auth required: Yes

Example request:

```text
Authorization: Bearer <token>
```

Example response:

```json
{
  "id": 1,
  "email": "user@example.com",
  "is_active": true,
  "created_at": "2026-04-10T12:00:00Z"
}
```

## CV Endpoints

### Upload Single CV

- Method: `POST`
- Route: `/cvs/upload`
- Description: Upload one PDF CV with a display name.
- Auth required: Yes

Example request:

```text
Content-Type: multipart/form-data
display_name=Backend Resume
file=<resume.pdf>
```

Example response:

```json
{
  "id": 10,
  "filename": "resume.pdf",
  "display_name": "Backend Resume",
  "summary": "Experienced software engineer...",
  "library_summary": "Backend-focused engineer with Python and API experience.",
  "is_favorite": false,
  "tags": ["backend"],
  "created_at": "2026-04-10T12:00:00Z"
}
```

### Upload Multiple CVs

- Method: `POST`
- Route: `/cvs/batch-upload`
- Description: Upload multiple PDF CVs in one request.
- Auth required: Yes

Example request:

```text
Content-Type: multipart/form-data
files=<resume-a.pdf>
files=<resume-b.pdf>
```

Example response:

```json
{
  "results": [
    {
      "filename": "resume-a.pdf",
      "success": true,
      "cv": {
        "id": 10,
        "filename": "resume-a.pdf",
        "display_name": "resume-a",
        "summary": "...",
        "library_summary": "...",
        "is_favorite": false,
        "tags": [],
        "created_at": "2026-04-10T12:00:00Z"
      },
      "error": null
    }
  ],
  "summary": {
    "succeeded": 1,
    "failed": 0
  }
}
```

### List CVs

- Method: `GET`
- Route: `/cvs`
- Description: List CVs owned by the authenticated user.
- Auth required: Yes

Example request:

```text
GET /cvs?limit=20&offset=0&search=backend&tags=python&tags=fastapi
Authorization: Bearer <token>
```

Example response:

```json
{
  "items": [
    {
      "id": 10,
      "filename": "resume.pdf",
      "display_name": "Backend Resume",
      "summary": "...",
      "library_summary": "...",
      "is_favorite": false,
      "tags": ["python", "fastapi"],
      "created_at": "2026-04-10T12:00:00Z"
    }
  ],
  "pagination": {
    "total": 1,
    "limit": 20,
    "offset": 0,
    "has_more": false
  }
}
```

### Get CV Detail

- Method: `GET`
- Route: `/cvs/{cv_id}`
- Description: Fetch one CV including `raw_text` and `clean_text`.
- Auth required: Yes

Example request:

```text
GET /cvs/10
Authorization: Bearer <token>
```

Example response:

```json
{
  "id": 10,
  "filename": "resume.pdf",
  "display_name": "Backend Resume",
  "summary": "...",
  "library_summary": "...",
  "is_favorite": false,
  "tags": ["python"],
  "created_at": "2026-04-10T12:00:00Z",
  "raw_text": "Original extracted text...",
  "clean_text": "Normalized text..."
}
```

### Replace CV Tags

- Method: `PATCH`
- Route: `/cvs/{cv_id}/tags`
- Description: Replace all tags for a CV.
- Auth required: Yes

Example request:

```json
{
  "tags": ["backend", "python"]
}
```

Example response:

```json
{
  "id": 10,
  "filename": "resume.pdf",
  "display_name": "Backend Resume",
  "summary": "...",
  "library_summary": "...",
  "is_favorite": false,
  "tags": ["backend", "python"],
  "created_at": "2026-04-10T12:00:00Z"
}
```

### Toggle CV Favorite

- Method: `PATCH`
- Route: `/cvs/{cv_id}/toggle-favorite`
- Description: Toggle `is_favorite` for a CV.
- Auth required: Yes

Example request:

```text
PATCH /cvs/10/toggle-favorite
Authorization: Bearer <token>
```

Example response:

```json
{
  "id": 10,
  "filename": "resume.pdf",
  "display_name": "Backend Resume",
  "summary": "...",
  "library_summary": "...",
  "is_favorite": true,
  "tags": ["backend", "python"],
  "created_at": "2026-04-10T12:00:00Z"
}
```

### Bulk Delete CVs

- Method: `POST`
- Route: `/cvs/bulk-delete`
- Description: Delete multiple CVs owned by the user.
- Auth required: Yes

Example request:

```json
{
  "cv_ids": [10, 11, 12]
}
```

Example response:

```json
{
  "updated": 0,
  "deleted": 3,
  "failed": 0
}
```

### Bulk Tag CVs

- Method: `POST`
- Route: `/cvs/bulk-tag`
- Description: Add tags to multiple CVs.
- Auth required: Yes

Example request:

```json
{
  "cv_ids": [10, 11],
  "tags": ["backend", "python"]
}
```

Example response:

```json
{
  "updated": 2,
  "deleted": 0,
  "failed": 0
}
```

### Delete CV

- Method: `DELETE`
- Route: `/cvs/{cv_id}`
- Description: Delete a CV and related references.
- Auth required: Yes

Example request:

```text
DELETE /cvs/10
Authorization: Bearer <token>
```

Example response:

```json
{
  "ok": true
}
```

## Job Endpoints

### Analyze Job Description

- Method: `POST`
- Route: `/jobs/analyze`
- Description: Analyze a job description and persist structured output.
- Auth required: Yes

Example request:

```json
{
  "title": "Backend Engineer",
  "company": "Acme",
  "description": "We are looking for a backend engineer with Python and FastAPI experience...",
  "language": "english",
  "regenerate": false
}
```

Example response:

```json
{
  "id": 20,
  "title": "Backend Engineer",
  "company": "Acme",
  "description": "We are looking for...",
  "clean_description": "backend engineer python fastapi...",
  "analysis_result": {
    "summary": "...",
    "seniority": "mid",
    "role_type": "backend",
    "required_skills": ["python", "fastapi"],
    "nice_to_have_skills": ["aws"],
    "responsibilities": ["build APIs"],
    "how_to_prepare": ["review async Python"],
    "learning_path": ["improve SQL"],
    "missing_skills": ["kubernetes"],
    "resume_tips": ["highlight API scaling"],
    "interview_tips": ["prepare architecture trade-offs"],
    "portfolio_project_ideas": ["build a rate-limited API"]
  },
  "is_saved": false,
  "status": "saved",
  "applied_date": null,
  "notes": null,
  "created_at": "2026-04-10T12:00:00Z"
}
```

### List Jobs

- Method: `GET`
- Route: `/jobs`
- Description: List analyzed jobs for the current user.
- Auth required: Yes

Example request:

```text
GET /jobs?limit=20&offset=0&saved=true
Authorization: Bearer <token>
```

Example response:

```json
{
  "items": [
    {
      "id": 20,
      "title": "Backend Engineer",
      "company": "Acme",
      "description": "...",
      "clean_description": "...",
      "analysis_result": {
        "summary": "...",
        "seniority": "mid",
        "role_type": "backend",
        "required_skills": ["python"],
        "nice_to_have_skills": [],
        "responsibilities": [],
        "how_to_prepare": [],
        "learning_path": [],
        "missing_skills": [],
        "resume_tips": [],
        "interview_tips": [],
        "portfolio_project_ideas": []
      },
      "is_saved": true,
      "status": "saved",
      "applied_date": null,
      "notes": null,
      "created_at": "2026-04-10T12:00:00Z"
    }
  ],
  "pagination": {
    "total": 1,
    "limit": 20,
    "offset": 0,
    "has_more": false
  }
}
```

### Get Job

- Method: `GET`
- Route: `/jobs/{job_id}`
- Description: Fetch one analyzed job.
- Auth required: Yes

Example request:

```text
GET /jobs/20
Authorization: Bearer <token>
```

Example response:

```json
{
  "id": 20,
  "title": "Backend Engineer",
  "company": "Acme",
  "description": "...",
  "clean_description": "...",
  "analysis_result": {
    "summary": "...",
    "seniority": "mid",
    "role_type": "backend",
    "required_skills": ["python"],
    "nice_to_have_skills": [],
    "responsibilities": [],
    "how_to_prepare": [],
    "learning_path": [],
    "missing_skills": [],
    "resume_tips": [],
    "interview_tips": [],
    "portfolio_project_ideas": []
  },
  "is_saved": false,
  "status": "saved",
  "applied_date": null,
  "notes": null,
  "created_at": "2026-04-10T12:00:00Z"
}
```

### Delete Job

- Method: `DELETE`
- Route: `/jobs/{job_id}`
- Description: Delete a job owned by the authenticated user.
- Auth required: Yes

Example request:

```text
DELETE /jobs/20
Authorization: Bearer <token>
```

Example response:

```json
{
  "success": true
}
```

### Update Job Status

- Method: `PATCH`
- Route: `/jobs/{job_id}/status`
- Description: Update job status and optional `applied_date`.
- Auth required: Yes

Example request:

```json
{
  "status": "applied",
  "applied_date": "2026-04-10T12:00:00Z"
}
```

Example response:

```json
{
  "id": 20,
  "title": "Backend Engineer",
  "company": "Acme",
  "description": "...",
  "clean_description": "...",
  "analysis_result": {
    "summary": "...",
    "seniority": "mid",
    "role_type": "backend",
    "required_skills": ["python"],
    "nice_to_have_skills": [],
    "responsibilities": [],
    "how_to_prepare": [],
    "learning_path": [],
    "missing_skills": [],
    "resume_tips": [],
    "interview_tips": [],
    "portfolio_project_ideas": []
  },
  "is_saved": false,
  "status": "applied",
  "applied_date": "2026-04-10T12:00:00Z",
  "notes": null,
  "created_at": "2026-04-10T12:00:00Z"
}
```

### Update Job Notes

- Method: `PATCH`
- Route: `/jobs/{job_id}/notes`
- Description: Update free-text notes for a job.
- Auth required: Yes

Example request:

```json
{
  "notes": "Follow up after onsite interview."
}
```

Example response:

```json
{
  "id": 20,
  "title": "Backend Engineer",
  "company": "Acme",
  "description": "...",
  "clean_description": "...",
  "analysis_result": {
    "summary": "...",
    "seniority": "mid",
    "role_type": "backend",
    "required_skills": ["python"],
    "nice_to_have_skills": [],
    "responsibilities": [],
    "how_to_prepare": [],
    "learning_path": [],
    "missing_skills": [],
    "resume_tips": [],
    "interview_tips": [],
    "portfolio_project_ideas": []
  },
  "is_saved": false,
  "status": "saved",
  "applied_date": null,
  "notes": "Follow up after onsite interview.",
  "created_at": "2026-04-10T12:00:00Z"
}
```

### Toggle Job Saved State

- Method: `PATCH`
- Route: `/jobs/{job_id}/toggle-saved`
- Description: Toggle bookmark state for a job.
- Auth required: Yes

Example request:

```text
PATCH /jobs/20/toggle-saved
Authorization: Bearer <token>
```

Example response:

```json
{
  "id": 20,
  "title": "Backend Engineer",
  "company": "Acme",
  "description": "...",
  "clean_description": "...",
  "analysis_result": {
    "summary": "...",
    "seniority": "mid",
    "role_type": "backend",
    "required_skills": ["python"],
    "nice_to_have_skills": [],
    "responsibilities": [],
    "how_to_prepare": [],
    "learning_path": [],
    "missing_skills": [],
    "resume_tips": [],
    "interview_tips": [],
    "portfolio_project_ideas": []
  },
  "is_saved": true,
  "status": "saved",
  "applied_date": null,
  "notes": null,
  "created_at": "2026-04-10T12:00:00Z"
}
```

### Match Job to CV

- Method: `POST`
- Route: `/jobs/{job_id}/match-cvs`
- Description: Analyze one CV against one job and persist the match.
- Auth required: Yes

Example request:

```json
{
  "cv_id": 10,
  "language": "english",
  "regenerate": false
}
```

Example response:

```json
{
  "id": 55,
  "user_id": 1,
  "cv_id": 10,
  "job_id": 20,
  "fit_level": "strong",
  "fit_summary": "Strong technical overlap with the role.",
  "why_this_cv": "Demonstrates backend API ownership and deployment experience.",
  "strengths": ["FastAPI", "PostgreSQL"],
  "missing_skills": ["Kubernetes"],
  "improvement_suggestions": ["Highlight distributed systems projects."],
  "suggested_improvements": ["Add metrics and observability achievements."],
  "missing_keywords": ["kubernetes", "kafka"],
  "reorder_suggestions": ["Move API scaling projects above older roles."],
  "match_level": "strong",
  "recommended": true,
  "created_at": "2026-04-10T12:00:00Z",
  "heuristic_score": 0.89,
  "result": {
    "fit_summary": "Strong technical overlap with the role.",
    "strengths": ["FastAPI", "PostgreSQL"],
    "missing_skills": ["Kubernetes"],
    "likely_fit_level": "strong",
    "resume_improvements": ["Add distributed systems outcomes."],
    "interview_focus": ["System design trade-offs"],
    "next_steps": ["Tailor achievements to job requirements"]
  }
}
```

### Compare CVs for a Job

- Method: `POST`
- Route: `/jobs/{job_id}/compare-cvs`
- Description: Compare two CVs against one job.
- Auth required: Yes

Example request:

```json
{
  "cv_id_a": 10,
  "cv_id_b": 11,
  "language": "english"
}
```

Example response:

```json
{
  "winner": {
    "cv_id": 10,
    "label": "CV A"
  },
  "overall_reason": "CV A is better aligned with required backend skills.",
  "comparative_strengths": ["More relevant API architecture experience"],
  "comparative_weaknesses": ["Less recent frontend work"],
  "job_alignment_breakdown": ["CV A directly maps to core role requirements."]
}
```

### Generate Cover Letter

- Method: `POST`
- Route: `/jobs/{job_id}/cover-letter`
- Description: Generate or reuse a tailored cover letter for one job and CV.
- Auth required: Yes

Example request:

```json
{
  "selected_cv_id": 10,
  "language": "english",
  "regenerate": false
}
```

Example response:

```json
{
  "generated_cover_letter": "Dear Hiring Team, ..."
}
```

## Match Endpoints

### List Matches

- Method: `GET`
- Route: `/matches`
- Description: List saved CV-job match results for the user.
- Auth required: Yes

Example request:

```text
GET /matches?limit=20&offset=0
Authorization: Bearer <token>
```

Example response:

```json
{
  "items": [
    {
      "id": 55,
      "user_id": 1,
      "cv_id": 10,
      "job_id": 20,
      "fit_level": "strong",
      "fit_summary": "Strong technical overlap with the role.",
      "why_this_cv": "Demonstrates backend API ownership and deployment experience.",
      "strengths": ["FastAPI", "PostgreSQL"],
      "missing_skills": ["Kubernetes"],
      "improvement_suggestions": ["Add distributed systems examples."],
      "suggested_improvements": ["Quantify impact in recent projects."],
      "missing_keywords": ["kubernetes"],
      "reorder_suggestions": ["Move strongest projects to top section."],
      "match_level": "strong",
      "recommended": true,
      "created_at": "2026-04-10T12:00:00Z"
    }
  ],
  "pagination": {
    "total": 1,
    "limit": 20,
    "offset": 0,
    "has_more": false
  }
}
```

### Get Match Detail

- Method: `GET`
- Route: `/matches/{match_id}`
- Description: Return one saved match.
- Auth required: Yes

Example request:

```text
GET /matches/55
Authorization: Bearer <token>
```

Example response:

```json
{
  "id": 55,
  "user_id": 1,
  "cv_id": 10,
  "job_id": 20,
  "fit_level": "strong",
  "fit_summary": "Strong technical overlap with the role.",
  "why_this_cv": "Demonstrates backend API ownership and deployment experience.",
  "strengths": ["FastAPI", "PostgreSQL"],
  "missing_skills": ["Kubernetes"],
  "improvement_suggestions": ["Add distributed systems examples."],
  "suggested_improvements": ["Quantify impact in recent projects."],
  "missing_keywords": ["kubernetes"],
  "reorder_suggestions": ["Move strongest projects to top section."],
  "match_level": "strong",
  "recommended": true,
  "created_at": "2026-04-10T12:00:00Z"
}
```

## System Endpoint

### Health Check

- Method: `GET`
- Route: `/health`
- Description: Service health probe endpoint.
- Auth required: No

Example request:

```text
GET /health
```

Example response:

```json
{
  "status": "ok"
}
```
