from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.review import ReviewStatus, ReviewTone


class ReviewCreate(BaseModel):
    parent_id: int | None = None
    name: str | None = Field(default=None, max_length=255)
    text: str = Field(min_length=1, max_length=5000)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("text")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Review text cannot be empty.")
        return value


class ReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    parent_id: int | None
    name: str | None
    text: str
    status: ReviewStatus
    response: str | None
    tone: str | None
    created_at: datetime


class ReviewUpdate(BaseModel):
    status: ReviewStatus | None = None
    response: str | None = None
    tone: ReviewTone | None = None
