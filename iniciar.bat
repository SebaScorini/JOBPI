@echo off
echo Iniciando Backend y Frontend de JOBPI...

:: Detectar si hay un entorno virtual (venv, .venv o env)
set PYTHON_CMD=uvicorn
if exist "venv\Scripts\activate.bat" (
    set PYTHON_CMD=call venv\Scripts\activate.bat ^& uvicorn
) else if exist ".venv\Scripts\activate.bat" (
    set PYTHON_CMD=call .venv\Scripts\activate.bat ^& uvicorn
) else if exist "env\Scripts\activate.bat" (
    set PYTHON_CMD=call env\Scripts\activate.bat ^& uvicorn
)

:: Iniciar el backend en una nueva ventana (mantenemos /k para que no se cierre si hay error)
start "Backend FastAPI" cmd /k "%PYTHON_CMD% app.main:app --reload --host 0.0.0.0 --port 8000"

:: Esperar a que el backend levante antes de iniciar el frontend
echo Esperando al backend (4s)...
timeout /t 4 /nobreak >nul

:: Iniciar el frontend en otra nueva ventana
start "Frontend Vite" cmd /k "cd frontend && npm run dev"

echo Ambos servicios han sido iniciados en ventanas separadas.
