from pydantic import BaseModel


class CvAnalysisResponse(BaseModel):
    fit_summary: str
    strengths: list[str]
    missing_skills: list[str]
    likely_fit_level: str
    resume_improvements: list[str]
    interview_focus: list[str]
    next_steps: list[str]
