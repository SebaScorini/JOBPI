# Docker Quick Start (5 minutes)

Get JOBPI running with Docker in just a few steps.

## Prerequisites

- Docker Desktop installed and running
- (Optional) Make, git, or curl

## Quick Setup

### 1. Clone or navigate to project

```bash
cd JOBPI
```

### 2. Copy environment file

```bash
cp .config/.env.docker .env
```

Edit `.env` if needed (optional - defaults are good for local development).

### 3. Start all services

Using **Make** (fastest):
```bash
make up
```

Or using **Python helper**:
```bash
python .scripts/docker_helper.py up
```

Or using **Docker directly**:
```bash
docker compose -f .config/docker/docker-compose.yml up -d
```

### 4. Wait for services to start

```bash
# Check status (using make)
make ps

# Or check with Docker
docker ps
```

All three services should show `healthy` or `up`:
- `jobpi-postgres` (Database)
- `jobpi-backend` (FastAPI)
- `jobpi-frontend` (React)

### 5. Open the app

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### 6. Stop services

```bash
make down
```

---

## Useful Commands

| Task | Command |
|------|---------|
| Start | `make up` |
| Stop | `make down` |
| View logs | `make logs` or `make logs-backend` or `make logs-frontend` |
| Shell into backend | `make bash` |
| Delete all data | `make clean` |
| Rebuild images | `make rebuild` |
| View status | `make ps` |

## Helpful Scripts

### Python Helper

```bash
# View all available commands
python .scripts/docker_helper.py help

# Start services
python .scripts/docker_helper.py up

# View backend logs
python .scripts/docker_helper.py logs-backend

# Shell into backend container
python .scripts/docker_helper.py bash
```

### Windows Batch Helper

```powershell
# From PowerShell
& .scripts\docker-up.bat up
& .scripts\docker-up.bat logs
```

## Troubleshooting

### Docker Desktop not running
**Error**: `Cannot connect to Docker daemon`
**Solution**: Start Docker Desktop

### Port already in use
**Error**: `bind: address already in use`
**Solution**:
```bash
# Find process on port 3000 or 8000
netstat -ano | findstr :3000

# Or change ports in .config/docker/docker-compose.yml
```

### Can't connect to database
**Error**: Backend logs show connection refused
**Solution**:
```bash
# Check postgres is healthy
docker ps

# Check logs
docker compose -f .config/docker/docker-compose.yml logs postgres

# Reset database
make clean
make up
```

### Frontend shows Cannot reach server
**Error**: Network error in browser console
**Solution**:
1. Ensure backend is running: `docker ps` shows `jobpi-backend`
2. Check backend logs: `make logs-backend`
3. Restart: `make down && make up`

---

## What's Running?

When you run `make up`, these containers start:

1. **PostgreSQL 15** (port 5432)
   - Database persistence
   - Automatic schema initialization
   - Data stored in Docker volume

2. **FastAPI Backend** (port 8000)
   - REST API
   - Hot reload enabled in development
   - Docs at http://localhost:8000/docs

3. **React Frontend** (port 3000)
   - Vite dev server
   - Hot reload enabled
   - Nginx reverse proxy

All communicate over internal Docker network. No services exposed to your machine except ports 3000 and 8000.

---

## Next Steps

- Read the full [DOCKER.md](DOCKER.md) for advanced commands (40+ options)
- Review [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) to understand the project layout
- Check [ENVIRONMENT.md](ENVIRONMENT.md) for all configuration options
- See [API_REFERENCE.md](API_REFERENCE.md) for API endpoints

---

## Quick Deployment Checklist

Once you've confirmed everything works locally:

- [ ] Created `.env` file from `.config/.env.docker`
- [ ] All 3 services running (`make ps` shows all as "up")
- [ ] Frontend loads on http://localhost:3000
- [ ] Backend API docs at http://localhost:8000/docs
- [ ] Can register and login through UI
- [ ] Logs show no critical errors
