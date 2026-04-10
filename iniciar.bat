@echo off
setlocal

echo Iniciando Backend y Frontend de JOBPI...

set "BACKEND_CMD=uvicorn"
set "BACKEND_LABEL=global"

if exist ".venv\Scripts\uvicorn.exe" (
    set "BACKEND_CMD=.venv\Scripts\uvicorn.exe"
    set "BACKEND_LABEL=.venv"
) else if exist "venv\Scripts\uvicorn.exe" (
    set "BACKEND_CMD=venv\Scripts\uvicorn.exe"
    set "BACKEND_LABEL=venv"
) else if exist "env\Scripts\uvicorn.exe" (
    set "BACKEND_CMD=env\Scripts\uvicorn.exe"
    set "BACKEND_LABEL=env"
) else (
    where uvicorn >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] No se encontro uvicorn.
        echo [ERROR] Activa tu entorno virtual o instala las dependencias del backend.
        echo [ERROR] Ejemplo: .\.venv\Scripts\pip install -r requirements.txt
        exit /b 1
    )
)

if not exist "frontend\package.json" (
    echo [ERROR] No se encontro frontend\package.json.
    echo [ERROR] Ejecuta este script desde la raiz del proyecto.
    exit /b 1
)

if not exist "frontend\node_modules\.bin\vite.cmd" (
    echo [ERROR] Faltan dependencias del frontend.
    echo [ERROR] Ejecuta: cd frontend ^&^& npm install
    exit /b 1
)

echo [OK] Backend listo para usar con %BACKEND_LABEL%.
echo [OK] Dependencias del frontend detectadas.

start "Backend FastAPI" cmd /k "%BACKEND_CMD% app.main:app --reload --host 0.0.0.0 --port 8000"

echo Esperando al backend (4s)...
timeout /t 4 /nobreak >nul

start "Frontend Vite" cmd /k "cd /d frontend && npm run dev"

echo Ambos servicios han sido iniciados en ventanas separadas.
endlocal
