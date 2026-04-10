# Project Migration - File Organization

## Summary

JOBPI has been reorganized for better maintainability and clarity. All Docker-related configuration files and helper scripts have been consolidated into dedicated directories.

## Migration Details

### Files Moved or Deprecated

| Old Location | New Location | Status | Notes |
|---|---|---|---|
| `docker-compose.yml` | `.config/docker/docker-compose.yml` | ✅ Moved | Primary orchestration file |
| `docker-compose.override.yml` | `.config/docker/` | ✅ Moved | Development overrides |
| `Dockerfile` | `.config/docker/Dockerfile` | ✅ Moved | Backend image |
| `Dockerfile.frontend` | `.config/docker/Dockerfile.frontend` | ✅ Moved | Frontend image |
| `.dockerignore` | `.config/.dockerignore` | ✅ Moved | Build exclusions |
| `docker_helper.py` | `.scripts/docker_helper.py` | ✅ Moved | Python helper script |
| `docker-up.bat` | `.scripts/docker-up.bat` | ✅ Moved | Windows batch helper |
| `DOCKER.md` | `docs/DOCKER.md` | ✅ Moved | Docker documentation (updated with new paths) |
| `DOCKER_QUICKSTART.md` | `docs/DOCKER_QUICKSTART.md` | ✅ Created | Quick Docker setup guide |

### Backward Compatibility

Root-level files may still exist for backward compatibility with existing scripts or CI/CD pipelines. However, **new usage should reference the files in `.config/docker/` and `.scripts/`**.

## Using the New Structure

### Quick Reference

```bash
# All commands now use this path
docker compose -f .config/docker/docker-compose.yml [command]

# Or use helpers
make [command]                              # Fastest
python .scripts/docker_helper.py [command]
.scripts/docker-up.bat [command]            # Windows
```

### Helper Scripts Location

- **Python helper**: `.scripts/docker_helper.py`
- **Windows batch**: `.scripts/docker-up.bat`
- **Make**: `Makefile` (at root, references `.config/docker/`)

### Configuration Files

- **Main compose**: `.config/docker/docker-compose.yml`
- **Development overrides**: `.config/docker/docker-compose.override.yml`
- **Environment template**: `.config/.env.docker`
- **Docker ignores**: `.config/.dockerignore`

## Documentation References

All documentation has been updated to use the new file structure:

- [docs/DOCKER.md](DOCKER.md) - Complete Docker reference (40+ commands)
- [docs/DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md) - 5-minute setup
- [docs/PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - Full directory guide
- [README.md](../README.md) - Main project README

## Working Directory Structure

```
JOBPI/
├── .config/docker/
│   ├── docker-compose.yml        (PRIMARY)
│   ├── docker-compose.override.yml
│   ├── Dockerfile
│   ├── Dockerfile.frontend
│   └── nginx.conf
├── .scripts/
│   ├── docker_helper.py          (PRIMARY)
│   └── docker-up.bat
├── .github/workflows/            (For CI/CD)
├── docs/
│   ├── DOCKER.md                 (UPDATED)
│   ├── DOCKER_QUICKSTART.md      (NEW)
│   └── PROJECT_STRUCTURE.md      (NEW)
├── Makefile                       (UPDATED to use .config/docker/)
└── README.md                      (UPDATED with new structure)
```

## Environment Setup

The new organization includes a template for Docker development:

```bash
# Copy environment template
cp .config/.env.docker .env

# Then start
make up
```

## Updating Old Commands

If you have scripts or documentation referencing old file locations, update to:

| Old | New |
|---|---|
| `docker compose up` | `docker compose -f .config/docker/docker-compose.yml up` |
| `python docker_helper.py` | `python .scripts/docker_helper.py` |
| `./docker-up.bat` | `.scripts/docker-up.bat` |

Or use `make up` for the quickest approach.

## No Breaking Changes

This reorganization does not affect:
- Source code in `app/` or `frontend/`
- Database schema or migrations
- API contracts or functionality
- Deployment process (if using Vercel)

All functionality remains identical; the project is just better organized.

## Questions?

See the updated documentation:
- Quick setup: [docs/DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md)
- Full reference: [docs/DOCKER.md](DOCKER.md)
- File organization: [docs/PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)
