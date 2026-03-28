# JOBPI

## Description
JOBPI is an AI-powered job analysis and resume matching platform. It evaluates job descriptions against a user's CV library to identify the best match, providing structured explanations and career insights using DSPy-optimized evaluation pipelines.

## Features
- Authentication (JWT)
- Multi CV upload
- CV library per user
- Job analysis
- Best CV recommendation
- Match explanation
- Saved jobs history
- Dashboard
- Dark mode UI

## Tech Stack
- FastAPI
- SQLModel
- SQLite
- DSPy
- React
- TypeScript
- Tailwind
- JWT Auth

## Architecture Overview
The application follows a decoupled client-server architecture:
- Backend: FastAPI service handling authentication, database operations with SQLModel, and AI-driven analysis using DSPy.
- Frontend: React-based single-page application built with Vite, styled with Tailwind CSS, and using JWT for session management.
- Database: SQLite for persistence of users, CVs, and analysis history.

## Setup Instructions

### Backend Setup
1. Create a Python virtual environment:
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # On Windows: venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure environment variables in a `.env` file in the root directory:
   ```env
   OPENROUTER_API_KEY=your_api_key
   JWT_SECRET_KEY=your_secret_key
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   ```

### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Create a `.env` file in the `frontend` directory:
   ```env
   VITE_API_URL=http://localhost:8000
   ```

## How to Run Locally

### Automated (Windows)
Run the provided batch file to start both services:
```cmd
iniciar.bat
```

### Manual
1. Start the backend:
   ```bash
   uvicorn app.main:app --reload
   ```
2. Start the frontend:
   ```bash
   cd frontend
   npm run dev
   ```

## Environment Variables
The following variables are required:
- `OPENROUTER_API_KEY`: API key for DSPy model inference.
- `JWT_SECRET_KEY`: Secret key for signing authentication tokens.
- `VITE_API_URL`: Backend API endpoint for the frontend application.

## Screenshots Placeholder
[Insert screenshots here]
