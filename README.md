# AI Job Analyzer (JobPi)

## Description
This project is an AI-powered job analysis application that intelligently evaluates job descriptions and compares them against uploaded candidate CVs. It solves the problem of manual resume screening by automating the comparison process and providing targeted, structured career advisory. AI is used to accurately extract context, perform semantic matching, and generate reliable insights using an optimized DSPy token pipeline.

## New Updates & Features
- **User Authentication:** Secure login and registration flows with JWT.
- **Premium SaaS UX:** Includes buttery smooth dark/light mode transitions, an expansive glass-morphism design system, responsive tabbed navigation, and loading states.
- **CV Library System:** Save and manage multiple CVs in a persistent SQLite database.
- **Advanced Match Analysis:** Comprehensive, full-screen side-by-side viewport for comparing candidate strengths, finding missing skills, and extracting actionable interview tips simultaneously. 
- **Intelligent Job Analysis:** Parses job descriptions with DSPy to extract core skills, responsibilities, and success metrics.
- **Token-Optimized Inference:** Preprocessing techniques to reduce context window load with OpenRouter integrations.

## Tech Stack
### Backend
- **FastAPI** (Async Python framework)
- **SQLite** (Persistent local database)
- **DSPy & OpenRouter** (AI Model routing & prompt optimization)
- **PyPDF2** (PDF parsing)
- **python-dotenv** (Environment variables handling)

### Frontend
- **React 18**
- **TypeScript**
- **Tailwind CSS 3** (Dark Mode & Glassmorphism)
- **Vite**

## Project Structure
```text
.
├── app/                  # FastAPI Backend 
│   ├── main.py           # Entry point and FastAPI routers
│   ├── core/             # Auth, Security, Config logic
│   ├── models/           # SQLAlchemy DB Models
│   ├── schemas/          # Pydantic Schemas for type safety
│   └── services/         # DSPy logic and CV parsing services
├── frontend/             # React Vite Frontend
│   ├── src/
│   │   ├── components/   # Reusable UI (Modals, Cards, Forms)
│   │   ├── pages/        # Dashboard, Jobs, CV Library
│   │   └── context/      # Client-side AuthContext
│   └── tailwind.config.js
├── iniciar.bat           # Quickstart script for Windows developers
├── .env                  # Backend Secrets (ignored by git)
├── .gitignore            # Git configuration rules
└── README.md
```

## Getting Started

### 1. Clone the repository:
```bash
git clone <repository_url>
cd <repository_directory>
```

### 2. Environment Variables Configuration:
- Create a `.env` file in the root directory (for backend API keys):
```ini
OPENROUTER_API_KEY=your_key_here
DSPY_MODEL=openrouter/nvidia/nemotron-3-super-120b-a12b:free
JWT_SECRET_KEY=your_secure_secret_here
```
- Create a `.env` inside the `frontend/` folder:
```ini
VITE_API_URL=http://localhost:8000
```

### 3. Install backend dependencies:
Using a virtual environment is highly recommended.
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Install frontend dependencies:
```bash
cd frontend
npm install
cd ..
```

### 5. Run the Application:

**Windows (Automated):**
You can use the provided batch file to automatically run both the frontend and backend simultaneously in separate terminal windows:
```cmd
iniciar.bat
```

**Manual Start:**
Terminal 1 (Backend):
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

## .gitignore Configuration
The project is set up to automatically ignore:
- **Virtual environments** (`venv/`, `.venv`)
- **OS caching files** (`.DS_Store`, `Thumbs.db`)
- **Secret files** (`.env` files in both root and frontend)
- **Build artifacts** (`node_modules/`, `dist/`, `__pycache__/`)
- **Local Database variants** (`jobpi.db`, SQLite journal files, and `uploads/`)

## Security Considerations
- **Environment Variables**: API keys and JWT secrets must always be kept in `.env` and never committed to version control. The `.gitignore` is precisely configured to handle this.
- **Input Validation:** Extensive Pydantic models validate all incoming data across API boundaries.

## License
MIT License
