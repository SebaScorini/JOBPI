from datetime import datetime

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str | None = None
    timestamp: datetime


class ErrorResponse(BaseModel):
    error: ErrorDetail
