from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.jobs import router as jobs_router
from app.api.routes.cv import router as cv_router


app = FastAPI(
    title="Job Description Analyzer API",
    version="0.1.0",
    description="Analyze job descriptions with DSPy and OpenRouter.",
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


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
