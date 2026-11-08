from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class ReviewStatus(StrEnum):
    NEW = "new"
    PROCESSED = "processed"


class ReviewTone(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class RemoteReview(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    parent_id: int | None = None
    name: str | None
    text: str
    status: ReviewStatus
    response: str | None = None
    tone: str | None = None
    created_at: datetime


class ReviewCreatePayload(BaseModel):
    parent_id: int | None = None
    name: str | None = None
    text: str


class ReviewUpdatePayload(BaseModel):
    status: ReviewStatus | None = None
    response: str | None = None
    tone: ReviewTone | None = None
