from datetime import datetime
import re
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator, model_validator


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

    @field_validator("description")
    @classmethod
    def require_non_whitespace_description(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Report description cannot be blank")
        return value


class PiiReportRedaction(BaseModel):
    description: str = Field(min_length=1, max_length=5000)

    @field_validator("description")
    @classmethod
    def require_non_whitespace_description(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Report description cannot be blank")
        return value


class ReportReviewCreate(BaseModel):
    status: Literal["confirmed", "false"]
    title: str = Field(min_length=1, max_length=500)
    detail: str = Field(min_length=1, max_length=5000)
    source: str | None = Field(default=None, max_length=2000)
    verification_method: Literal[
        "official_notice", "first_hand_witness", "multiple_community_sources"
    ]
    evidence_url: str | None = Field(default=None, max_length=2000)
    evidence_note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_source_for_findings(self):
        if self.evidence_url:
            parsed_url = urlsplit(self.evidence_url)
            if parsed_url.scheme not in {"http", "https"} or not parsed_url.hostname:
                raise ValueError("Evidence URL must use HTTP or HTTPS")
        if self.status in {"confirmed", "false"} and not (self.source and self.source.strip()):
            raise ValueError("A source is required for confirmed or false findings")
        if not (self.evidence_url and self.evidence_url.strip()) and not (
            self.evidence_note and self.evidence_note.strip()
        ):
            raise ValueError("Provide an evidence URL or evidence note")
        return self


class UpdateReasonCreate(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)

    @field_validator("reason")
    @classmethod
    def require_non_whitespace_reason(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("A reason is required")
        return value


class CommunityUpdateCorrection(BaseModel):
    action: Literal["correct", "retract"]
    reason: str = Field(min_length=1, max_length=2000)

    @field_validator("reason")
    @classmethod
    def require_non_whitespace_reason(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("A reason is required")
        return value


class ReviewerCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    display_name: str | None = Field(default=None, max_length=120)
    ward: str | None = Field(default=None, max_length=120)

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
    display_name: str | None = None
    ward: str | None = None
    role: Literal["reviewer", "ward_admin"] | None = None
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
    ai_language: str | None = None
    ai_normalized_text: str | None = None
    ai_category: str | None = None
    ai_confidence: float | None = None
    ai_dispute_category: str | None = None
    ai_summary: str | None = None
    ai_review_required: bool = False
    ai_review_reason: str | None = None
    duplicate_count: int = 0
    ward: str | None = None
    priority: str = "normal"
    triage_notes: str | None = None
    channel: str = "web"
    first_response_at: datetime | None = None
    sla_age_hours: float = 0
    sla_overdue: bool = False
    possible_duplicates: list[dict] = Field(default_factory=list)


class ReportTriageUpdate(BaseModel):
    action: Literal["triage", "request_more_info", "dismiss"]
    priority: Literal["low", "normal", "urgent"] | None = None
    ward: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=2000)
    reason: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_dismiss_reason(self):
        if self.action == "dismiss" and not (self.reason and self.reason.strip()):
            raise ValueError("A reason is required to dismiss a report")
        return self


class DisputeUpdate(BaseModel):
    resolution_path: Literal["elder_baraza", "chief_office", "landlord_association"] | None = None
    status: Literal["scheduled", "closed"] | None = None
    assigned_to_email: str | None = Field(default=None, max_length=320)
    note: str | None = Field(default=None, max_length=2000)


class QueueResponse(BaseModel):
    items: list[ReportQueueResponse]
    total: int
    page: int
    page_size: int
    counts: dict[str, int]
    urgent_or_overdue: list[ReportQueueResponse]


class ReportReviewResponse(BaseModel):
    id: str
    status: str
    community_update_id: str
    workflow_status: str


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
    workflow_status: str
    title: str
    detail: str
    source: str | None = None
    published_at: datetime
    publisher_label: str
    verification_method: str
    correction_reason: str | None = None
    correction_history: list[dict] = Field(default_factory=list)
