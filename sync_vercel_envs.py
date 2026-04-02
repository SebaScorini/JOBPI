import os
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).parent
backend_dir = BASE_DIR
frontend_dir = BASE_DIR / "frontend"

def add_env_to_vercel(project_dir, env_name, env_value, target="production"):
    print(f"Adding {env_name} to {project_dir.name}...")
    # Ejecutamos vercel env add. Reemplaza el valor a través de stdin.
    process = subprocess.Popen(
        ["vercel.cmd", "env", "add", env_name, target],
        cwd=project_dir,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        text=True
    )
    stdout, stderr = process.communicate(input=env_value)
    if process.returncode != 0:
        print(f"Error adding {env_name}: {stderr}")
    else:
        print(f"Success {env_name}")

def sync_backend_envs():
    env_file = BASE_DIR / ".env.deploy"
    if not env_file.exists():
        print("No .env.deploy found!")
        return

    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            if "=" in line:
                key, val = line.split("=", 1)
                add_env_to_vercel(backend_dir, key.strip(), val.strip())

def sync_frontend_envs():
    add_env_to_vercel(frontend_dir, "VITE_API_URL", "https://jobpi-api.vercel.app")
    
if __name__ == "__main__":
    print("Syncing Backend Envs...")
    sync_backend_envs()
    print("\nSyncing Frontend Envs...")
    sync_frontend_envs()
    print("\nEnvironment variables sync complete!")
