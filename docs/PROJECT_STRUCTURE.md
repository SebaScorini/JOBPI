# 📁 Project Structure

JOBPI is organized into clear, logical directories for better maintainability.

```
JOBPI/
├── .config/                    # Configuration & Docker setup
│   ├── docker/                 # Docker resources
│   │   ├── docker-compose.yml  # Main container orchestration
│   │   ├── Dockerfile          # Backend image
│   │   ├── Dockerfile.frontend # Frontend image
│   │   └── nginx.conf          # Nginx configuration
│   ├── .env.docker             # Docker environment template
│   └── .dockerignore           # Files to exclude from Docker build
│
├── .scripts/                   # Helper scripts
│   ├── docker-up.bat           # Windows Docker helper
│   └── docker_helper.py        # Cross-platform Docker helper
│
├── .github/                    # GitHub workflows (CI/CD)
│   └── workflows/
│
├── app/                        # Backend source code
│   ├── api/                    # REST endpoints
│   │   ├── routes/
│   │   │   ├── auth.py
│   │   │   ├── cvs.py
│   │   │   ├── jobs.py
│   │   │   └── matches.py
│   ├── core/                   # Core functionality
│   │   ├── ai.py              # AI service integration
│   │   ├── config.py          # Configuration
│   │   ├── rate_limit.py      # Rate limiting
│   │   ├── security.py        # Auth/security
│   │   ├── settings.py        # App settings
│   │   └── validation.py      # Input validation
│   ├── db/                     # Database layer
│   │   ├── crud.py            # CRUD operations
│   │   ├── database.py        # DB connection
│   │   └── init_db.py         # Schema bootstrap
│   ├── dependencies/           # Request dependencies
│   │   └── auth.py            # Auth dependency
│   ├── models/                 # Data models
│   │   └── entities.py        # SQLModel entities
│   ├── schemas/                # Pydantic schemas
│   │   ├── auth.py
│   │   ├── cv.py
│   │   ├── job.py
│   │   ├── match.py
│   ├── services/               # Business logic
│   │   ├── cv_analyzer.py
│   │   ├── cv_library_service.py
│   │   ├── cv_library_summary_service.py
│   │   ├── job_analyzer.py
│   │   ├── job_preprocessing.py
│   │   ├── pdf_extractor.py
│   │   ├── cover_letter_service.py
│   │   └── response_language.py
│   └── main.py                # FastAPI app entry point
│
├── frontend/                   # Frontend source code (React + Vite)
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── context/           # React context
│   │   ├── pages/             # Page components
│   │   ├── services/          # API client
│   │   ├── types/             # TypeScript types
│   │   ├── i18n/              # Internationalization
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── public/                # Static assets
│   ├── Vite config and package.json
│   └── nginx.conf             # Nginx server config (see .config/docker/)
│
├── docs/                       # Documentation
│   ├── API_REFERENCE.md       # API endpoint docs
│   ├── ARCHITECTURE.md        # System architecture
│   ├── DEPLOYMENT.md          # Production deployment
│   ├── ENVIRONMENT.md         # Environment variables
│   ├── PROJECT_CONTEXT.md     # Project overview
│   ├── DOCKER.md              # Docker detailed guide
│   └── DOCKER_QUICKSTART.md   # Quick Docker setup
│
├── tests/                      # Test suite
│   ├── __init__.py             # Test package init
│   ├── conftest.py             # Pytest configuration
│   ├── README.md               # Test documentation
│   ├── test_cv_summary_isolation.py
│   ├── test_dspy_configure.py
│   ├── test_job_delete.py
│   └── test_improvements.py    # Integration tests for improvements
│
├── design-system/              # Design assets & guidelines
├── api/                        # Vercel serverless API (if deployed)
├── .env.example                # Environment template (root)
├── .gitignore                  # Git ignore patterns
├── .dockerignore               # Docker ignore patterns (root - backward compat)
├── requirements.txt            # Python dependencies
├── pytest.ini                  # Pytest configuration
├── README.md                   # Main project README
├── Makefile                    # Top-level make commands
├── [old docker files]          # Removed (now in .config/docker/)
└── [other files]
```

---

## 📂 Directory Purposes

### Core Directories

| Directory | Purpose |
|-----------|---------|
| **.config/** | All configuration files (Docker, environment, etc.) |
| **.scripts/** | Helper scripts for development and deployment |
| **.github/** | GitHub-specific workflows and CI/CD |
| **app/** | Backend FastAPI application |
| **frontend/** | Frontend React/Vite application |
| **docs/** | Project documentation |
| **tests/** | Test suite |

### Backend Structure (app/)

- **api/routes/** - HTTP endpoint definitions
- **core/** - Core services (AI, config, security, rate limiting)
- **db/** - Database layer (CRUD, schema, connection)
- **dependencies/** - FastAPI request dependencies
- **models/** - SQLModel ORM entities
- **schemas/** - Pydantic request/response models
- **services/** - Business logic (CV analysis, job matching, cover letters)

### Frontend Structure (frontend/)

- **src/components/** - Reusable React components
- **src/context/** - React Context for state management
- **src/pages/** - Page-level components
- **src/services/** - API client and utilities
- **src/types/** - TypeScript type definitions
- **src/i18n/** - Multi-language support

### Configuration Structure (.config/)

- **docker/** - All Docker-related files
- **.env.docker** - Docker environment template
- **.dockerignore** - Files excluded from Docker builds

---

## 🚀 Quick Commands

### Using Make

```bash
make up              # Start services
make down            # Stop services
make logs-be         # View backend logs
make bash            # Shell into backend
```

### Using Python Helper

```bash
python .scripts/docker_helper.py up
python .scripts/docker_helper.py logs-backend
python .scripts/docker_helper.py bash
```

### Using Windows Batch

```powershell
.scripts\docker-up.bat up
.scripts\docker-up.bat logs
.scripts\docker-up.bat bash
```

### Using Docker Directly

```bash
docker compose -f .config/docker/docker-compose.yml up
docker compose -f .config/docker/docker-compose.yml logs -f
```

---

## 📖 Documentation Map

- **README.md** - Start here for overview
- **DOCKER_QUICKSTART.md** - 5-minute Docker setup
- **DOCKER.md** - Complete Docker guide (40+ commands)
- **ARCHITECTURE.md** - System design and flows
- **API_REFERENCE.md** - REST API endpoints
- **DEPLOYMENT.md** - Production deployment
- **ENVIRONMENT.md** - All configuration variables
- **PROJECT_CONTEXT.md** - Project details

---

## 🔄 Backward Compatibility

The root directory maintains copies of Docker files for backward compatibility:
- `docker-compose.yml` (root) → references `.config/docker/docker-compose.yml`
- `Dockerfile` (root)  → copy in `.config/docker/`
- `Dockerfile.frontend` (root) → copy in `.config/docker/`

This allows existing scripts and workflows to continue working while the organized structure is available for new setups.

---

## 💡 Best Practices

1. **Development**: Use `make up` or `.scripts/docker_helper.py up`
2. **Configuration**: All Docker config is in `.config/docker/`
3. **Environment**: Copy `.config/.env.docker` to `.env` and configure
4. **Scripts**: Use helpers in `.scripts/` instead of running raw docker commands
5. **Documentation**: Check `docs/` for guides and references

