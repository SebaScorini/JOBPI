# JOBPI - AI Job Application Assistant

JOBPI is a full-stack application that helps job seekers evaluate opportunities, choose the right CV, and manage applications with AI-assisted insights.

## Overview

JOBPI was built to make job applications more strategic and less manual. It analyzes job descriptions, compares them against a user's CV library, recommends the best CV for each role, suggests concrete improvements, generates tailored cover letters, and tracks application progress in one workflow.

## Features

- Authentication with JWT
- Multi CV upload
- CV Library per user
- Job analysis
- Best CV recommendation
- Match explanation
- CV improvement suggestions
- Cover letter generator
- CV comparison
- Job application tracker
- CV tags
- Saved jobs history
- Dashboard
- Dark mode UI

## Tech Stack

### Backend

- FastAPI
- SQLModel
- SQLite
- DSPy

### Frontend

- React
- TypeScript
- Tailwind CSS
- Vite

## Architecture

The system follows a client-server architecture with a React frontend communicating with a FastAPI backend through a REST API. Business logic and AI-driven analysis run in the backend, while SQLite stores users, CVs, jobs, and match results. DSPy powers the analysis and content generation layer for recommendations and cover letters.

## Installation

### Backend

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the FastAPI server:

```bash
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

Create a `.env` file in the project root for backend settings:

```env
OPENROUTER_API_KEY=your_openrouter_api_key
JWT_SECRET_KEY=your_jwt_secret
```

Notes:

- `OPENROUTER_API_KEY` is required for AI-powered analysis and cover letter generation.
- `VITE_API_URL` configures the frontend API target.

Create a `.env` file in `frontend/`:

```env
VITE_API_URL=http://localhost:8000
```

## Running Locally

1. Open terminal 1 at the project root.
2. Activate the Python virtual environment.
3. Start backend:

```bash
uvicorn app.main:app --reload
```

4. Open terminal 2.
5. Start frontend:

```bash
cd frontend
npm run dev
```

6. Open the Vite URL shown in terminal (typically `http://localhost:5173`).

