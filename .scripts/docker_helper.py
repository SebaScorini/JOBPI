#!/usr/bin/env python
"""
Docker-compose helper for JOBPI
Run from project root: python .scripts/docker_helper.py <command>
"""

import subprocess
import sys
from pathlib import Path

# Docker compose file location
COMPOSE_FILE = ".config/docker/docker-compose.yml"

def run_cmd(cmd: list[str], verbose: bool = True) -> int:
    """Run command and return exit code."""
    if verbose:
        print(f"▶ {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode

def main():
    """Main CLI interface."""
    if len(sys.argv) < 2:
        print_help()
        return 0

    cmd = sys.argv[1]
    args = sys.argv[2:] if len(sys.argv) > 2 else []

    # Map commands
    commands = {
        "up": lambda: run_cmd(["docker", "compose", "-f", COMPOSE_FILE, "up", "-d"] + args) == 0,
        "down": lambda: run_cmd(["docker", "compose", "-f", COMPOSE_FILE, "down"] + args) == 0,
        "restart": lambda: run_cmd(["docker", "compose", "-f", COMPOSE_FILE, "restart"] + args) == 0,
        "logs": lambda: run_cmd(["docker", "compose", "-f", COMPOSE_FILE, "logs", "-f"] + args) == 0,
        "ps": lambda: run_cmd(["docker", "compose", "-f", COMPOSE_FILE, "ps"] + args) == 0,
        "build": lambda: run_cmd(["docker", "compose", "-f", COMPOSE_FILE, "build", "--progress=plain"] + args) == 0,
        "clean": lambda: run_cmd(["docker", "compose", "-f", COMPOSE_FILE, "down", "-v", "--rmi", "all"] + args) == 0,
        "bash": lambda: run_cmd(["docker", "compose", "-f", COMPOSE_FILE, "exec", "backend", "bash"] + args) == 0,
        "shell": lambda: run_cmd(["docker", "compose", "-f", COMPOSE_FILE, "exec", "backend", "bash"] + args) == 0,
        "logs-backend": lambda: run_cmd(["docker", "compose", "-f", COMPOSE_FILE, "logs", "-f", "backend"] + args) == 0,
        "logs-frontend": lambda: run_cmd(["docker", "compose", "-f", COMPOSE_FILE, "logs", "-f", "frontend"] + args) == 0,
        "logs-db": lambda: run_cmd(["docker", "compose", "-f", COMPOSE_FILE, "logs", "-f", "postgres"] + args) == 0,
        "test": lambda: run_cmd(["docker", "compose", "-f", COMPOSE_FILE, "exec", "backend", "pytest"] + args) == 0,
        "help": print_help,
    }

    if cmd not in commands:
        print(f"❌ Unknown command: {cmd}")
        print_help()
        return 1

    result = commands[cmd]()
    if isinstance(result, bool):
        return 0 if result else 1
    return result

def print_help():
    """Print help message."""
    print(f"""
🐳 JOBPI Docker Helper
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

USAGE:
    python .scripts/docker_helper.py <command> [args]

DOCKER COMPOSE FILE:
    {COMPOSE_FILE}

COMMANDS:
    up              Start all services (backend, frontend, postgres)
    down            Stop all services
    restart         Restart services
    build           Build Docker images
    ps              Show running services
    clean           Remove everything (containers, images, volumes)

LOGS:
    logs            Show logs from all services (follow)
    logs-backend    Show backend logs
    logs-frontend   Show frontend logs
    logs-db         Show database logs

SHELL:
    bash            Open bash shell in backend container
    shell           Alias for bash

TESTING:
    test            Run pytest in backend

EXAMPLES:
    python .scripts/docker_helper.py up                    # Start all
    python .scripts/docker_helper.py logs-backend          # View backend logs
    python .scripts/docker_helper.py bash                  # Shell into backend
    python .scripts/docker_helper.py test -v               # Run tests verbosely
    python .scripts/docker_helper.py down                  # Stop all services

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TROUBLESHOOTING:
    • Check .config/.env.docker exists and is configured
    • Docker Desktop must be running
    • Ports 8000, 3000, 5432 must be available
    • Run 'python .scripts/docker_helper.py ps' to check service status

LOCATION: .config/docker/
    - docker-compose.yml
    - Dockerfile
    - Dockerfile.frontend
    - nginx.conf
    """)

if __name__ == "__main__":
    sys.exit(main())
