from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.jobs import router as jobs_router
from app.api.routes.cv import router as cv_router
from app.api.routes.library import router as library_router
from app.db.database import create_db_and_tables


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="Job Description Analyzer API",
    version="0.1.0",
    description="Analyze job descriptions with DSPy and OpenRouter.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_router)
app.include_router(cv_router)
app.include_router(library_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
