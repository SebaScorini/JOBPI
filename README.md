# JOBPI

AI-powered job application assistant for CV optimization, role matching, and application tracking.

## 1. Overview

JOBPI helps users run a structured job application workflow in one place. It analyzes job descriptions, compares them with a personal CV library, recommends the best CV for each role, explains the match, suggests CV improvements, generates cover letters, and tracks application progress over time.

The goal is to reduce manual effort and make application decisions more consistent and data-driven.

## 2. Features

- Authentication (JWT)
- Multi CV upload
- AI-generated CV summaries
- CV Library per user
- Job analysis
- Best CV recommendation
- Match explanation
- CV improvement suggestions
- Cover letter generator
- CV comparison
- Job application tracker
- Dashboard
- Language selection (EN/ES)
- Dark mode UI

## 3. Tech Stack

### Backend

- FastAPI
- SQLModel
- SQLite
- DSPy
- OpenRouter (Minimax)

### Frontend

- React
- TypeScript
- Tailwind CSS
- Vite

## 4. Architecture

JOBPI uses a React frontend and a FastAPI backend connected through a REST API. The backend handles business logic, authentication, persistence, and AI-powered analysis. Data is stored in SQLite, and AI tasks (analysis, summaries, suggestions, generation) are routed through DSPy with OpenRouter-backed models.

## 5. Installation

### Backend

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run API server:

```bash
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## 6. Environment Variables

### Backend (.env in project root)

```env
OPENROUTER_API_KEY=your_openrouter_api_key
```

### Frontend (.env in frontend/)

```env
VITE_API_URL=http://localhost:8000
```

## 7. Running Locally

1. Open a terminal at the project root.
2. Create and activate the backend virtual environment.
3. Install backend dependencies.
4. Start the backend server.

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

5. Open a second terminal.
6. Start the frontend dev server.

```bash
cd frontend
npm install
npm run dev
```

7. Open the frontend URL shown by Vite (typically http://localhost:5173).

