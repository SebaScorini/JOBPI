# API REFERENCE

Base routes: `/auth`, `/cvs`, `/jobs`, `/matches`, `/health`.

Auth is required for all routes except registration, login, and health.

## Auth

### POST /auth/register

Description: Create a new user account.
Auth required: No

Example request:

```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

Example response:

```json
{
  "id": 1,
  "email": "user@example.com",
  "is_active": true,
  "created_at": "2026-04-02T12:00:00Z"
}
```

### POST /auth/login

Description: Authenticate and return a bearer token.
Auth required: No

Example request: form data with `username` and `password`.

Example response:

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

### GET /auth/me

Description: Return the current authenticated user.
Auth required: Yes

Example response:

```json
{
  "id": 1,
  "email": "user@example.com",
  "is_active": true,
  "created_at": "2026-04-02T12:00:00Z"
}
```

## CVs

### POST /cvs/upload

Description: Upload a single PDF CV with a display name.
Auth required: Yes

Example request: multipart form data with `display_name` and `file`.

Example response:

```json
{
  "id": 10,
  "filename": "resume.pdf",
  "display_name": "Resume",
  "summary": "Experienced software engineer...",
  "library_summary": "Software engineer with backend and frontend experience.",
  "tags": [],
  "created_at": "2026-04-02T12:00:00Z"
}
```

### POST /cvs/batch-upload

Description: Upload multiple PDF CVs in one request.
Auth required: Yes

Example request: multipart form data with `files`.

Example response:

```json
{
  "results": [
    {
      "filename": "resume.pdf",
      "success": true,
      "cv": {
        "id": 10,
        "filename": "resume.pdf",
        "display_name": "Resume",
        "summary": "Experienced software engineer...",
        "library_summary": "Software engineer with backend and frontend experience.",
        "tags": [],
        "created_at": "2026-04-02T12:00:00Z"
      },
      "error": null
    }
  ],
  "summary": {"succeeded": 1, "failed": 0}
}
```

### GET /cvs

Description: List the authenticated user's CVs.
Auth required: Yes

Example response: array of CV summary objects.

### GET /cvs/{cv_id}

Description: Fetch one CV, including raw and cleaned text.
Auth required: Yes

Example response: CV detail object with `raw_text` and `clean_text`.

### PATCH /cvs/{cv_id}/tags

Description: Replace the tag list for a CV.
Auth required: Yes

Example request:

```json
{
  "tags": ["backend", "python"]
}
```

Example response: updated CV summary object.

### DELETE /cvs/{cv_id}

Description: Delete a CV and related references.
Auth required: Yes

Example response:

```json
{"ok": true}
```

## Jobs

### POST /jobs/analyze

Description: Analyze a job description and persist the result.
Auth required: Yes

Example request:

```json
{
  "title": "Backend Engineer",
  "company": "Acme",
  "description": "We are looking for...",
  "language": "english",
  "regenerate": false
}
```

Example response: analyzed job object with structured analysis.

### GET /jobs

Description: List the authenticated user's analyzed jobs.
Auth required: Yes

Example response: array of job objects.

### GET /jobs/{job_id}

Description: Fetch one analyzed job.
Auth required: Yes

Example response: job object.

### DELETE /jobs/{job_id}

Description: Delete a job owned by the authenticated user.
Auth required: Yes

Example response:

```json
{ "success": true }
```

### PATCH /jobs/{job_id}/status

Description: Update job status and optional applied date.
Auth required: Yes

Example request:

```json
{
  "status": "applied",
  "applied_date": "2026-04-02T12:00:00Z"
}
```

Example response: updated job object.

### PATCH /jobs/{job_id}/notes

Description: Update job notes.
Auth required: Yes

Example request:

```json
{
  "notes": "Follow up next week."
}
```

Example response: updated job object.

### POST /jobs/{job_id}/match-cvs

Description: Analyze one CV against one job and persist the match.
Auth required: Yes

Example request:

```json
{
  "cv_id": 10,
  "language": "english",
  "regenerate": false
}
```

Example response: saved match detail object.

### POST /jobs/{job_id}/compare-cvs

Description: Compare two CVs for the same job.
Auth required: Yes

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
  "winner": {"cv_id": 10, "label": "CV A"},
  "overall_reason": "CV A matches the role more closely.",
  "comparative_strengths": ["Stronger backend experience"],
  "comparative_weaknesses": ["Fewer cloud projects"],
  "job_alignment_breakdown": ["CV A covers the core stack better."]
}
```

### POST /jobs/{job_id}/cover-letter

Description: Generate or reuse a cover letter for one job and selected CV.
Auth required: Yes

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
  "generated_cover_letter": "Dear hiring team,..."
}
```

## Matches

### GET /matches

Description: List all saved matches for the authenticated user.
Auth required: Yes

Example response: array of match summary objects.

### GET /matches/{match_id}

Description: Fetch one saved match.
Auth required: Yes

Example response: match detail object.

## System

### GET /health

Description: Health check endpoint.
Auth required: No

Example response:

```json
{ "status": "ok" }
```