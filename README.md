# AI Job Analyzer

## Description
This project is an AI-powered job analysis application that intelligently evaluates job descriptions and compares them against uploaded candidate CVs. It solves the problem of manual resume screening by automating the comparison process and providing targeted, structured career advisory. AI is used to accurately extract context, perform semantic matching, and generate reliable insights using an optimized token pipeline.

## Features
- Job description analysis
- CV PDF upload
- CV-to-job fit comparison
- Structured career advice
- Token-optimized inference
- FastAPI backend
- React frontend
- DSPy integration
- OpenRouter free model support

## Tech Stack
### Backend
- FastAPI
- DSPy
- Python
- OpenRouter
- PDF parsing
- REST API

### Frontend
- React
- TypeScript
- Tailwind

## Project Structure
```text
.
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── models/
│   ├── routers/
│   └── services/
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── main.tsx
│   └── tailwind.config.js
└── README.md
```

## How It Works
1. User uploads CV: A candidate submits their resume in PDF format alongside a job description.
2. System extracts text: The backend parses the PDF document into raw text.
3. Preprocessing: Extracted text is cleaned and condensed to optimize token usage.
4. DSPy analysis: The system routes the context through DSPy to interact intelligently with models.
5. Structured output: The analysis generates a standardized JSON response comparing the CV against the job requirements.

## Getting Started

1. Clone the repository:
```bash
git clone <repository_url>
cd <repository_directory>
```

2. Install backend dependencies:
```bash
cd backend
pip install -r requirements.txt
```

3. Install frontend dependencies:
```bash
cd frontend
npm install
```

4. Set environment variables:
Configure the appropriate `.env` files for both the backend and frontend based on the requirements below.

5. Run the backend:
```bash
cd backend
uvicorn main:app --reload
```

6. Run the frontend:
```bash
cd frontend
npm run dev
```

## Environment Variables

### Backend (backend/.env)
- `OPENROUTER_API_KEY`: API key for accessing OpenRouter models
- `DSPY_MODEL`: Identifier for the specific OpenRouter model to employ

### Frontend (frontend/.env)
- `VITE_API_URL`: The base URL for the FastAPI backend

## API Endpoints
- `POST /analyze-job`: Analyzes a provided job description and returns core requirements.
- `POST /analyze-fit`: Accepts a PDF upload and a job description to return a fit comparison.

## Example Request

```http
POST /analyze-fit HTTP/1.1
Host: localhost:8000
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary

------WebKitFormBoundary
Content-Disposition: form-data; name="cv_file"; filename="resume.pdf"
Content-Type: application/pdf

<Binary PDF Data>
------WebKitFormBoundary
Content-Disposition: form-data; name="job_description"

We are looking for a software engineer experienced with React and Python.
------WebKitFormBoundary--
```

## Example Response

```json
{
  "fit_score": 85,
  "analysis": "The candidate shows strong alignment with the core requirements.",
  "strengths": [
    "Python development",
    "React component architecture"
  ],
  "areas_for_improvement": [
    "Missing explicit AI model experience"
  ],
  "career_advice": "Highlight any self-directed AI projects to demonstrate capability."
}
```

## Performance Notes
- Optimized for free models
- Token reduction implemented for context windows
- Preprocessing executed to strip unnecessary formatting

## Future Improvements
- Better scoring
- Caching
- Streaming responses
- OCR support

## License
MIT License
