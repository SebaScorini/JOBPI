@echo off
REM Docker helper batch script for Windows
REM Location: .scripts\docker-up.bat
REM Usage: .scripts\docker-up.bat <command>
REM
REM Note: Run from project root directory

setlocal enabledelayedexpansion
set COMPOSE_FILE=.config\docker\docker-compose.yml

if "%1"=="" (
    echo.
    echo 🐳 JOBPI Docker Commands
    echo ===============================
    echo.
    echo Usage: 
    echo   .scripts\docker-up up         - Start all services
    echo   .scripts\docker-up down       - Stop all services
    echo   .scripts\docker-up logs       - View all logs
    echo   .scripts\docker-up build      - Build images
    echo   .scripts\docker-up bash       - Shell into backend
    echo.
    exit /b 0
)

if "%1"=="up" (
    echo Starting Docker services from %COMPOSE_FILE%...
    docker compose -f %COMPOSE_FILE% up -d
    timeout /t 3 /nobreak
    cls
    echo.
    echo ✅ Services started!
    echo.
    docker compose -f %COMPOSE_FILE% ps
    echo.
    echo Frontend: http://localhost:3000
    echo Backend:  http://localhost:8000
    echo API Docs: http://localhost:8000/docs
    echo.
    exit /b 0
)

if "%1"=="down" (
    echo Stopping Docker services...
    docker compose -f %COMPOSE_FILE% down
    exit /b 0
)

if "%1"=="logs" (
    docker compose -f %COMPOSE_FILE% logs -f
    exit /b 0
)

if "%1"=="build" (
    echo Building Docker images...
    docker compose -f %COMPOSE_FILE% build --progress=plain
    exit /b 0
)

if "%1"=="bash" (
    docker compose -f %COMPOSE_FILE% exec backend bash
    exit /b 0
)

if "%1"=="ps" (
    docker compose -f %COMPOSE_FILE% ps
    exit /b 0
)

if "%1"=="clean" (
    echo WARNING: This will remove all containers, images, and volumes!
    set /p confirm="Continue? (y/N): "
    if /i "!confirm!"=="y" (
        docker compose -f %COMPOSE_FILE% down -v --rmi all
        echo Cleaned!
    )
    exit /b 0
)

if "%1"=="test" (
    docker compose -f %COMPOSE_FILE% exec backend pytest %2 %3 %4
    exit /b 0
)

echo Unknown command: %1
echo Run '.scripts\docker-up.bat' without arguments for help
exit /b 1
