# Docker Complete Guide

Comprehensive Docker reference for JOBPI with 40+ commands and troubleshooting.

## Table of Contents

1. [Files Location](#files-location)
2. [Basic Commands](#basic-commands)
3. [Service Management](#service-management)
4. [Viewing Logs](#viewing-logs)
5. [Container Access](#container-access)
6. [Database Operations](#database-operations)
7. [Development Workflow](#development-workflow)
8. [Troubleshooting](#troubleshooting)
9. [Environment Variables](#environment-variables)
10. [Advanced Usage](#advanced-usage)

---

## Files Location

All Docker-related files are organized in `.config/docker/`:

```
.config/
├── docker/
│   ├── docker-compose.yml      # Main orchestration file
│   ├── Dockerfile              # Backend image definition
│   ├── Dockerfile.frontend     # Frontend image definition
│   └── nginx.conf              # Nginx web server config
├── .env.docker                 # Environment template
└── .dockerignore               # Build exclusions
```

**Key Path**: All `docker compose` commands use:
```bash
docker compose -f .config/docker/docker-compose.yml [command]
```

Or use a helper:
```bash
make [command]                  # Uses Makefile
python .scripts/docker_helper.py [command]
```

---

## Basic Commands

### Start services

```bash
# Using Make (recommended)
make up

# Using helper script
python .scripts/docker_helper.py up

# Using Docker directly (Windows)
docker compose -f .config/docker/docker-compose.yml up -d
```

### Stop services

```bash
make down
```

### Restart services

```bash
make restart
```

### View status

```bash
make ps
docker ps
docker ps --format "table {{.Names}}\t{{.Status}}"
```

### Remove everything

```bash
make clean          # Containers + volumes (data deleted)
docker volume prune # Remove unused volumes
```

---

## Service Management

### Build images

```bash
# Build all images
docker compose -f .config/docker/docker-compose.yml build

# Build specific service
docker compose -f .config/docker/docker-compose.yml build backend

# Rebuild without cache
docker compose -f .config/docker/docker-compose.yml build --no-cache
```

### View running services

```bash
# Detailed view
docker compose -f .config/docker/docker-compose.yml ps

# List only names
docker compose -f .config/docker/docker-compose.yml ps --services

# View with specific format
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
```

### Start/stop individual services

```bash
# Start only backend
docker compose -f .config/docker/docker-compose.yml up -d backend

# Stop only frontend
docker compose -f .config/docker/docker-compose.yml stop frontend

# Pause a service
docker compose -f .config/docker/docker-compose.yml pause postgres

# Unpause
docker compose -f .config/docker/docker-compose.yml unpause postgres
```

### Remove services

```bash
# Remove stopped containers
docker compose -f .config/docker/docker-compose.yml rm

# Remove with confirmation skip
docker compose -f .config/docker/docker-compose.yml rm -f
```

---

## Viewing Logs

### All logs (stream)

```bash
# All services
make logs

# Last 50 lines, then stream
docker compose -f .config/docker/docker-compose.yml logs -f --tail 50

# Without following
docker compose -f .config/docker/docker-compose.yml logs --tail 200
```

### Service-specific logs

```bash
# Backend logs
make logs-backend
docker compose -f .config/docker/docker-compose.yml logs -f backend

# Frontend logs
make logs-frontend
docker compose -f .config/docker/docker-compose.yml logs -f frontend

# Database logs
docker compose -f .config/docker/docker-compose.yml logs -f postgres

# Last 100 lines only
docker compose -f .config/docker/docker-compose.yml logs --tail 100 backend
```

### Search logs for errors

```bash
# Show only errors
docker compose -f .config/docker/docker-compose.yml logs | grep -i error

# Show lines containing "500" (server errors)
docker compose -f .config/docker/docker-compose.yml logs | grep 500

# Show lines containing "connection"
docker compose -f .config/docker/docker-compose.yml logs | grep -i connection
```

### View logs since specific time

```bash
# Logs from last 10 minutes
docker compose -f .config/docker/docker-compose.yml logs --since 10m

# Logs up to specific time
docker compose -f .config/docker/docker-compose.yml logs --until 2024-01-15
```

---

## Container Access

### Shell/bash into containers

```bash
# Backend shell
make bash

# Frontend shell
docker compose -f .config/docker/docker-compose.yml exec frontend sh

# Database shell (psql)
docker compose -f .config/docker/docker-compose.yml exec postgres bash
```

### Run commands in containers

```bash
# Run Python command in backend
docker compose -f .config/docker/docker-compose.yml exec backend python -c "import sys; print(sys.version)"

# List files in backend
docker compose -f .config/docker/docker-compose.yml exec backend ls -la

# Check database connection
make bash  # Then run: python -c "import psycopg; print(psycopg.__version__)"
```

### Copy files to/from containers

```bash
# Copy from local to container
docker cp ./file.txt jobpi-backend:/app/file.txt

# Copy from container to local
docker cp jobpi-backend:/app/file.txt ./file.txt

# Copy entire directory
docker cp ./local-dir jobpi-backend:/app/
```

---

## Database Operations

### Connect to PostgreSQL

```bash
# Via psql in container
docker compose -f .config/docker/docker-compose.yml exec postgres psql -U jobpi_user -d jobpi_db

# View tables
\dt

# View schema
\d CV

# Exit psql
\q
```

### Backup database

```bash
# Create backup
docker compose -f .config/docker/docker-compose.yml exec postgres pg_dump -U jobpi_user jobpi_db > backup.sql

# With format
docker compose -f .config/docker/docker-compose.yml exec postgres pg_dump -U jobpi_user -F c jobpi_db > backup.dump
```

### Restore database

```bash
# From SQL backup
docker compose -f .config/docker/docker-compose.yml exec -T postgres psql -U jobpi_user jobpi_db < backup.sql

# From dump format
docker compose -f .config/docker/docker-compose.yml exec postgres pg_restore -U jobpi_user -d jobpi_db backup.dump
```

### Reset database (delete all data)

```bash
# Delete volumes (triggers database recreation)
docker compose -f .config/docker/docker-compose.yml down -v

# Start fresh
make up
```

### Check database health

```bash
# Connect and run query
docker compose -f .config/docker/docker-compose.yml exec postgres psql -U jobpi_user -d jobpi_db -c "SELECT 1;"

# From backend container
make bash
python -c "import psycopg; conn = psycopg.connect('postgresql://...'); print('Connected!')"
```

---

## Development Workflow

### Hot reload configuration

Both frontend and backend support hot reload by default:

- **Backend**: Changes to Python files auto-reload (Uvicorn hot reload)
- **Frontend**: Changes to React/TypeScript auto-reload (Vite HMR)

No need to restart containers - just save files.

### Develop with local code

The docker-compose mounts volumes for live code editing:

```yaml
services:
  backend:
    volumes:
      - ../../app:/app/app  # App code
      - ../../app/main.py:/app/main.py
```

Changes in `app/` folder reflect immediately.

### Test requirements changes

```bash
# Add new requirement
echo "new-package==1.0.0" >> requirements.txt

# Rebuild backend image
docker compose -f .config/docker/docker-compose.yml build backend

# Restart service
docker compose -f .config/docker/docker-compose.yml up -d backend

# Verify
make bash
python -c "import new_package; print('OK')"
```

### Run migrations

```bash
# If using alembic
make bash
alembic upgrade head

# Or manually
make bash
python app/db/init_db.py
```

---

## Troubleshooting

### Services won't start

```bash
# Check logs
make logs

# Check specific service
make logs-backend

# Check Docker daemon is running
docker ps

# Restart Docker Desktop
# (Close Docker and reopen it)
```

### Port already in use

```bash
# Find process on port 8000
netstat -ano | findstr :8000

# Kill process (by PID)
taskkill /PID 12345 /F

# Or change port in .config/docker/docker-compose.yml
# Then restart
make down && make up
```

### Database connection refused

```bash
# Check postgres container is running
docker ps | grep postgres

# Check postgres logs
make logs postgres

# Verify DATABASE_URL format (.env file)
# Should be: postgresql+psycopg://user:pass@postgres:5432/dbname

# Test connection from backend
make bash
python -c "from app.db.database import engine; print(engine)"
```

### Frontend shows blank page

```bash
# Check frontend is running
make logs-frontend

# Check backend is accessible
make logs-backend | tail -20

# Try hard refresh in browser (Ctrl+Shift+R)

# Check browser console for errors (F12)

# Verify VITE_API_URL in .env points to backend
```

### Backend API returns 500

```bash
# Check logs
make logs-backend

# Look for specific errors
docker compose -f .config/docker/docker-compose.yml logs backend | grep -i error

# Restart backend
docker compose -f .config/docker/docker-compose.yml restart backend

# Or rebuild if code updated
docker compose -f .config/docker/docker-compose.yml build backend
make up -d backend
```

### Containers keep restarting

```bash
# Check logs
docker compose -f .config/docker/docker-compose.yml logs [service-name]

# Common causes:
# 1. Database not ready - check postgres logs
# 2. Dependency issue - check requirements.txt
# 3. Invalid environment variables - check .env file
# 4. Port conflict - check netstat

# Debug by running without -d flag
docker compose -f .config/docker/docker-compose.yml up backend
# (Press Ctrl+C to stop, read the error)
```

### Memory/disk issues

```bash
# Check Docker disk usage
docker system df

# Clean up unused images
docker image prune

# Clean up unused volumes
docker volume prune

# Remove everything and rebuild
docker system prune -a
make build
make up
```

---

## Environment Variables

All configurable via `.env` file:

```bash
# Database
DATABASE_URL=postgresql+psycopg://jobpi_user:jobpi_pass@postgres:5432/jobpi_db

# Backend
APP_ENV=development
SECRET_KEY=your-secret-key-here
OPENROUTER_API_KEY=your-key
DSPY_MODEL=model-name

# Frontend
VITE_API_URL=http://localhost:8000
VITE_SITE_URL=http://localhost:3000

# Docker ports
BACKEND_PORT=8000
FRONTEND_PORT=3000
POSTGRES_PORT=5432
```

Modify `.env` and restart:
```bash
make down && make up
```

---

## Advanced Usage

### Custom Make commands

All available commands in `Makefile`:

```bash
make help            # Show all commands
make build           # Rebuild images
make rebuild         # Full rebuild with no cache
make test            # Run test suite
make lint            # Run linters
make format          # Format code
```

### Debug containers

```bash
# Inspect container details
docker inspect jobpi-backend

# Monitor resource usage
docker stats

# See what's using disk
docker system df -v
```

### Networking

```bash
# View network
docker network ls
docker network inspect jobpi_default

# Services communicate via:
# - Backend: http://backend:8000 (from frontend)
# - Database: postgres://postgres:5432 (from backend)
```

### Persist data after containers removal

Data persists in Docker volumes:

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect jobpi_postgres_data

# To keep data but reset containers
make down         # Stops and removes containers
make up           # Recreates containers with same volume
```

### Production deployment

For production, use:
```bash
docker compose -f .config/docker/docker-compose.yml -f docker-compose.prod.yml up -d
```

(Requires additional `docker-compose.prod.yml` with production overrides)

---

## Quick Reference

| Task | Command |
|------|---------|
| Start | `make up` |
| Stop | `make down` |
| Restart | `make restart` |
| Status | `make ps` |
| Logs | `make logs` |
| Logs (backend) | `make logs-backend` |
| Shell | `make bash` |
| Build | `make build` |
| Clean | `make clean` |
| Rebuild | `make rebuild` |

---

## Support

For issues not covered here, see:
- [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md) - Quick setup
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - File organization
- [ENVIRONMENT.md](ENVIRONMENT.md) - All config options
