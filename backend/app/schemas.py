from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AuthCredentials(BaseModel):
    email: str
    password: str = Field(min_length=8)


class ReportCreate(BaseModel):
    report_type: Literal["Rumour to check", "Local issue", "Safety concern"]
    description: str = Field(min_length=1, max_length=5000)
    attachment_path: str | None = None


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
