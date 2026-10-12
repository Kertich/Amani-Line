from datetime import datetime
import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class AuthCredentials(BaseModel):
    email: str
    password: str = Field(min_length=8)
    
    
# 1. Define the structure of your response data
class HealthCheckResponse(BaseModel):
    status: str
    data: int | None


class ReportCreate(BaseModel):
    report_type: Literal["Rumour to check", "Local issue", "Safety concern"]
    description: str = Field(min_length=1, max_length=5000)
    attachment_path: str | None = None


class ReportReviewCreate(BaseModel):
    status: Literal["confirmed", "false"]
    title: str = Field(min_length=1, max_length=500)
    detail: str = Field(min_length=1, max_length=5000)
    source: str | None = Field(default=None, max_length=2000)


class ReviewerCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        email = value.strip().casefold()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise ValueError("Enter a valid email address")
        return email


class ReviewerResponse(BaseModel):
    email: str
    created_at: datetime | None
    is_bootstrap: bool = False


class ReportAssignmentUpdate(BaseModel):
    assigned_to_email: str | None = Field(default=None, max_length=320)


class ReportQueueResponse(BaseModel):
    id: str
    reference: str
    report_type: str
    description: str
    status: str
    created_at: datetime
    assigned_to_email: str | None = None


class ReportReviewResponse(BaseModel):
    id: str
    status: str
    community_update_id: str


class DisputeCreate(BaseModel):
    concern_type: Literal["Land or boundary", "Home or tenancy", "Noise or neighbour concern", "Something else"]
    desired_outcome: str = Field(min_length=1, max_length=5000)
    contact_phone: str | None = Field(default=None, max_length=40)


class UploadUrlCreate(BaseModel):
    filename: str = Field(min_length=1, max_length=200)
    content_type: str = Field(min_length=1, max_length=100)


class UpdateResponse(BaseModel):
    id: str
    status: str
    title: str
    detail: str
    source: str | None = None
    created_at: datetime
