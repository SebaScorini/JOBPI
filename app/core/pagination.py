from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field, field_validator


T = TypeVar("T")


class PaginationParams(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0)

    @field_validator("offset", mode="before")
    @classmethod
    def validate_offset(cls, value) -> int:
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0


class PaginationMeta(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    pagination: PaginationMeta


def build_paginated_response(items: list[T], total: int, limit: int, offset: int) -> PaginatedResponse[T]:
    return PaginatedResponse[T](
        items=items,
        pagination=PaginationMeta(
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total,
        ),
    )
