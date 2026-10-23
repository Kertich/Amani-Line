import enum
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, Float, String, Text, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# 1. Base Class for Models
class Base(DeclarativeBase):
    pass

# 2. Native Python Enums for PostgreSQL Enum Mapping
class ReportStatus(str, enum.Enum):
    PENDING = "pending"
    REVIEWING = "reviewing"
    NEEDS_INFO = "needs_info"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"

class UpdateStatus(str, enum.Enum):
    CONFIRMED = "confirmed"
    PENDING = "pending"
    FALSE = "false"

# 3. Community Updates Model
class CommunityUpdate(Base):
    __tablename__ = "community_updates"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=text("gen_random_uuid()")
    )
    status: Mapped[UpdateStatus] = mapped_column(
        ENUM(UpdateStatus, name="update_status", schema="public"),
        nullable=False,
        server_default=UpdateStatus.PENDING.value
    )
    workflow_status: Mapped[str] = mapped_column(
        String, nullable=False, server_default=text("'draft'")
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    author_email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    approved_by_email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    publisher_label: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    evidence_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verification_method: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source_report_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.reports.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        server_default=text("now()")
    )

# 4. Reports Model
class Report(Base):
    __tablename__ = "reports"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=text("gen_random_uuid()")
    )
    # The default computes the AMN-XXXXXX pattern exactly like your SQL schema
    reference: Mapped[str] = mapped_column(
        String, 
        nullable=False, 
        unique=True,
        server_default=text("('AMN-' || upper(substr(replace(gen_random_uuid()::text, '-', ''), 1, 6))))")
    )
    # Links to Supabase's internal auth.users table
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="SET NULL"),
        nullable=True
    )
    report_type: Mapped[str] = mapped_column(String, nullable=False) # 'Rumour to check', 'Local issue', 'Safety concern'
    description: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[ReportStatus] = mapped_column(
        ENUM(ReportStatus, name="report_status", schema="public"),
        nullable=False,
        server_default=ReportStatus.PENDING.value
    )
    assigned_to_email: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_language: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_normalized_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_category: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_dispute_category: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_review_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    ai_review_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_pii_flagged: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    ai_duplicate_of: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.reports.id", ondelete="SET NULL"),
        nullable=True,
    )
    ward: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'normal'"),
    )
    triage_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    first_response_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    possible_duplicate_of: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.reports.id", ondelete="SET NULL"),
        nullable=True,
    )
    channel: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'web'"),
    )
    reporter_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    language: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        server_default=text("now()")
    )

# 5. Dispute Requests Model
class DisputeRequest(Base):
    __tablename__ = "dispute_requests"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False
    )
    concern_type: Mapped[str] = mapped_column(String, nullable=False)
    desired_outcome: Mapped[str] = mapped_column(Text, nullable=False)
    contact_phone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, server_default="received")
    resolution_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assigned_to_email: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    triage_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        server_default=text("now()")
    )
