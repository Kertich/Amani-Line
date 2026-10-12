from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath
from uuid import uuid4

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile, status

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database import engine, get_db
from model import Base 

from fastapi.middleware.cors import CORSMiddleware
from supabase import Client

from auth import (
    get_current_user,
    get_optional_user,
    get_admin_user,
    get_verification_user,
    is_admin_user,
    is_verification_user,
)
from config import get_settings
from schemas import (
    AuthCredentials,
    DisputeCreate,
    PiiReportRedaction,
    ReportCreate,
    ReportAssignmentUpdate,
    ReportQueueResponse,
    ReportReviewCreate,
    ReportReviewResponse,
    ReviewerCreate,
    ReviewerResponse,
    UpdateResponse,
    UploadUrlCreate,
    HealthCheckResponse,
)
from supabase_client import get_admin_client, get_auth_client
from triage import (
    AIProviderError,
    TriageResult,
    analyze_report,
    contains_targeted_pii,
    detect_language,
    find_duplicate,
    normalize_message,
    transcribe_audio,
)

settings = get_settings()

# 1. Define the Lifespan Setup
#@asynccontextmanager
#async def lifespan(app: FastAPI):
    # Everything inside this block runs BEFORE the API starts accepting traffic
   # print("⏳ Synchronizing database tables with Supabase...")
    #async with engine.begin() as conn:
        # This line executes your Python code into actual SQL tables
       #commented# await conn.run_sync(Base.metadata.create_all)
    #print("✅ Database synchronization complete!")
    
    #yield
    # Everything down here runs when you shut down the server (Ctrl + C)
    #await engine.dispose()
    
# 2. Initialize FastAPI with the lifespan hook
#lifespan=lifespan
app = FastAPI(title="Amani Line API", version="1.0.0" )
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _first(data):
    if not data:
        raise HTTPException(status_code=404, detail="Resource not found")
    return data[0] if isinstance(data, list) else data


def _triage_metadata(result: TriageResult, duplicate_of: str | None = None) -> dict:
    return {
        "ai_language": result.language,
        "ai_normalized_text": result.normalized_text,
        "ai_category": result.category,
        "ai_confidence": result.confidence,
        "ai_dispute_category": result.dispute_category,
        "ai_summary": result.summary,
        "ai_review_required": result.needs_human_review,
        "ai_review_reason": result.review_reason,
        "ai_pii_flagged": result.pii_flagged,
        "ai_duplicate_of": duplicate_of,
    }


def _manual_review_result(description: str, reason: str) -> TriageResult:
    return TriageResult(
        language=detect_language(description),
        normalized_text=normalize_message(description),
        category=None,
        confidence=None,
        dispute_category=None,
        summary="",
        needs_human_review=True,
        review_reason=reason,
        pii_flagged=False,
    )


def _find_recent_duplicate(result: TriageResult) -> str | None:
    if result.pii_flagged or not result.category:
        return None
    cutoff = datetime.now(timezone.utc).replace(microsecond=0)
    cutoff -= timedelta(days=14)
    try:
        response = (
            get_admin_client()
            .table("reports")
            .select("id,ai_normalized_text,ai_duplicate_of")
            .eq("ai_pii_flagged", False)
            .in_("status", ["pending", "reviewing"])
            .gte("created_at", cutoff.isoformat())
            .order("created_at", desc=True)
            .limit(100)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Unable to check for similar reports; the report was not saved",
        ) from exc
    return find_duplicate(result.normalized_text, response.data)


# 2. Add it directly as the response model and return type hint
@app.get("/healthcheck", response_model=HealthCheckResponse)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthCheckResponse:
    result = await db.execute(text("SELECT 1"))
    return HealthCheckResponse(status="connected", data=result.scalar())


@app.post("/api/auth/signup", status_code=status.HTTP_201_CREATED)
def signup(credentials: AuthCredentials):
    try:
        response = get_auth_client().auth.sign_up(
            {"email": credentials.email, "password": credentials.password}
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Unable to create account") from exc
    return {"user": response.user, "session": response.session}


@app.post("/api/auth/login")
def login(credentials: AuthCredentials):
    try:
        response = get_auth_client().auth.sign_in_with_password(
            {"email": credentials.email, "password": credentials.password}
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid email or password") from exc
    return {"user": response.user, "session": response.session}


@app.get("/api/auth/me")
def me(user=Depends(get_current_user)):
    return {
        "user": user,
        "can_verify": is_verification_user(user),
        "can_admin": is_admin_user(user),
    }


@app.post("/api/reports", status_code=status.HTTP_201_CREATED)
def create_report(payload: ReportCreate, user=Depends(get_optional_user)):
    try:
        triage = analyze_report(payload.description, get_settings())
    except AIProviderError:
        triage = _manual_review_result(payload.description, "provider_unavailable")
    duplicate_of = _find_recent_duplicate(triage)
    row = {
        "report_type": payload.report_type,
        "description": payload.description,
        "attachment_path": payload.attachment_path,
        "status": "pending",
        "user_id": str(user.id) if user else None,
        **_triage_metadata(triage, duplicate_of),
    }
    try:
        response = get_admin_client().table("reports").insert(row).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to save report") from exc
    report = _first(response.data)
    return {"id": report["id"], "reference": report["reference"], "status": report["status"]}


@app.get("/api/reports/queue", response_model=list[ReportQueueResponse])
def list_report_queue(
    limit: int = Query(default=50, ge=1, le=100),
    user=Depends(get_verification_user),
):
    email = user.email.strip().casefold()
    query = (
        get_admin_client()
        .table("reports")
        .select(
            "id,reference,report_type,description,status,created_at,assigned_to_email,"
            "ai_language,ai_normalized_text,ai_category,ai_confidence,"
            "ai_dispute_category,ai_summary,ai_review_required,ai_review_reason"
        )
        .in_("status", ["pending", "reviewing"])
        .eq("ai_pii_flagged", False)
        .is_("ai_duplicate_of", "null")
        .order("created_at")
        .limit(limit)
    )
    if not is_admin_user(user):
        query = query.eq("assigned_to_email", email)
    try:
        response = query.execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to load report queue") from exc
    reports = response.data
    report_ids = [item["id"] for item in reports]
    duplicate_counts: dict[str, int] = {}
    if report_ids:
        try:
            duplicates = (
                get_admin_client()
                .table("reports")
                .select("ai_duplicate_of")
                .in_("ai_duplicate_of", report_ids)
                .execute()
            )
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail="Unable to load grouped duplicate reports",
            ) from exc
        for duplicate in duplicates.data:
            root_id = duplicate["ai_duplicate_of"]
            duplicate_counts[root_id] = duplicate_counts.get(root_id, 0) + 1
    return [
        {**item, "duplicate_count": duplicate_counts.get(item["id"], 0)}
        for item in reports
    ]


@app.get(
    "/api/admin/reports/pii-escalations",
    response_model=list[ReportQueueResponse],
)
def list_pii_escalations(user=Depends(get_admin_user)):
    try:
        response = (
            get_admin_client()
            .table("reports")
            .select(
                "id,reference,report_type,description,status,created_at,assigned_to_email,"
                "ai_language,ai_normalized_text,ai_category,ai_confidence,"
                "ai_dispute_category,ai_summary,ai_review_required,ai_review_reason"
            )
            .eq("ai_pii_flagged", True)
            .in_("status", ["pending", "reviewing"])
            .order("created_at")
            .limit(100)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to load private PII escalations",
        ) from exc
    return response.data


@app.post(
    "/api/admin/reports/{report_id}/pii-clear",
    response_model=ReportQueueResponse,
)
def clear_report_pii(
    report_id: str,
    payload: PiiReportRedaction,
    user=Depends(get_admin_user),
):
    if contains_targeted_pii(payload.description):
        raise HTTPException(
            status_code=422,
            detail="Remove personal names and contact details before returning this report to review",
        )
    try:
        existing = (
            get_admin_client()
            .table("reports")
            .select("id")
            .eq("id", report_id)
            .eq("ai_pii_flagged", True)
            .in_("status", ["pending", "reviewing"])
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to verify private escalation") from exc
    if not existing.data:
        raise HTTPException(status_code=404, detail="Private escalation not found")
    try:
        triage = analyze_report(payload.description, get_settings())
    except AIProviderError:
        triage = _manual_review_result(payload.description, "provider_unavailable")
    duplicate_of = _find_recent_duplicate(triage)
    try:
        response = (
            get_admin_client()
            .table("reports")
            .update(
                {
                    "description": payload.description,
                    **_triage_metadata(triage, duplicate_of),
                }
            )
            .eq("id", report_id)
            .eq("ai_pii_flagged", True)
            .select(
                "id,reference,report_type,description,status,created_at,assigned_to_email,"
                "ai_language,ai_normalized_text,ai_category,ai_confidence,"
                "ai_dispute_category,ai_summary,ai_review_required,ai_review_reason"
            )
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to save the human-redacted report",
        ) from exc
    return _first(response.data)


@app.post("/api/voice-notes/transcribe")
async def transcribe_voice_note(
    file: UploadFile = File(...),
    user=Depends(get_verification_user),
):
    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=415, detail="Upload an audio file")
    audio = await file.read(20 * 1024 * 1024 + 1)
    if len(audio) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio file exceeds the 20 MB limit")
    if not audio:
        raise HTTPException(status_code=422, detail="Audio file is empty")
    filename = (file.filename or "voice-note").replace('"', "").replace("\r", "").replace("\n", "")
    try:
        transcript = transcribe_audio(audio, filename, file.content_type, get_settings())
    except AIProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"transcript": transcript, "language": detect_language(transcript)}


@app.get("/api/admin/reviewers", response_model=list[ReviewerResponse])
def list_reviewers(user=Depends(get_admin_user)):
    try:
        response = (
            get_admin_client()
            .table("report_reviewers")
            .select("email,created_at")
            .order("email")
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to load reviewers") from exc
    configured_emails = get_settings().verification_queue_email_set
    reviewers_by_email = {
        item["email"]: {**item, "is_bootstrap": False}
        for item in response.data
    }
    for email in configured_emails:
        reviewers_by_email[email] = {
            "email": email,
            "created_at": None,
            "is_bootstrap": True,
        }
    return list(reviewers_by_email.values())


@app.post(
    "/api/admin/reviewers",
    response_model=ReviewerResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_reviewer(payload: ReviewerCreate, user=Depends(get_admin_user)):
    email = payload.email.strip().casefold()
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise HTTPException(status_code=422, detail="Enter a valid email address")
    try:
        response = (
            get_admin_client()
            .table("report_reviewers")
            .upsert({"email": email}, on_conflict="email")
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to authorize reviewer") from exc
    return _first(response.data)


@app.delete("/api/admin/reviewers/{email}", status_code=status.HTTP_204_NO_CONTENT)
def remove_reviewer(email: str, user=Depends(get_admin_user)):
    normalized_email = email.strip().casefold()
    if normalized_email in (
        get_settings().admin_email_set | get_settings().verification_queue_email_set
    ):
        raise HTTPException(status_code=400, detail="Bootstrap access cannot be removed here")
    try:
        get_admin_client().table("reports").update(
            {"assigned_to_email": None, "status": "pending"}
        ).eq("assigned_to_email", normalized_email).in_(
            "status", ["pending", "reviewing"]
        ).execute()
        get_admin_client().table("report_reviewers").delete().eq(
            "email", normalized_email
        ).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to remove reviewer") from exc
    return None


@app.patch("/api/admin/reports/{report_id}/assignment")
def assign_report(
    report_id: str,
    payload: ReportAssignmentUpdate,
    user=Depends(get_admin_user),
):
    email = payload.assigned_to_email.strip().casefold() if payload.assigned_to_email else None
    if email and email not in get_settings().verification_queue_email_set:
        try:
            reviewer = (
                get_admin_client()
                .table("report_reviewers")
                .select("email")
                .eq("email", email)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail="Unable to validate reviewer") from exc
        if not reviewer.data:
            raise HTTPException(status_code=422, detail="Choose an authorized reviewer")
    try:
        response = (
            get_admin_client()
            .table("reports")
            .update(
                {
                    "assigned_to_email": email,
                    "status": "reviewing" if email else "pending",
                }
            )
            .eq("id", report_id)
            .in_("status", ["pending", "reviewing"])
            .select(
                "id,reference,report_type,description,status,created_at,assigned_to_email"
            )
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to assign report") from exc
    return _first(response.data)


@app.post(
    "/api/reports/{report_id}/publish",
    response_model=ReportReviewResponse,
)
def publish_report(
    report_id: str,
    payload: ReportReviewCreate,
    user=Depends(get_verification_user),
):
    try:
        report_state = (
            get_admin_client()
            .table("reports")
            .select("ai_pii_flagged")
            .eq("id", report_id)
            .in_("status", ["pending", "reviewing"])
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to verify report safety status") from exc
    if not report_state.data:
        raise HTTPException(status_code=404, detail="Report not found or already reviewed")
    if report_state.data[0]["ai_pii_flagged"]:
        raise HTTPException(
            status_code=409,
            detail="This report is privately escalated and must be redacted by an administrator before publication",
        )
    if not is_admin_user(user):
        email = user.email.strip().casefold()
        try:
            assigned_report = (
                get_admin_client()
                .table("reports")
                .select("id,ai_pii_flagged")
                .eq("id", report_id)
                .eq("assigned_to_email", email)
                .in_("status", ["pending", "reviewing"])
                .limit(1)
                .execute()
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail="Unable to verify report assignment") from exc
        if not assigned_report.data:
            raise HTTPException(
                status_code=403,
                detail="You are not assigned to review this report",
            )
        if assigned_report.data[0]["ai_pii_flagged"]:
            raise HTTPException(
                status_code=409,
                detail="This report is privately escalated and must be redacted by an administrator before publication",
            )
    try:
        response = get_admin_client().rpc(
            "review_report",
            {
                "p_report_id": report_id,
                "p_update_status": payload.status,
                "p_title": payload.title,
                "p_detail": payload.detail,
                "p_source": payload.source,
            },
        ).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to publish report") from exc
    result = _first(response.data)
    return {
        "id": report_id,
        "status": payload.status,
        "community_update_id": result["community_update_id"],
    }


@app.get("/api/updates", response_model=list[UpdateResponse])
def list_updates(
    update_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
):
    query = (
        get_admin_client()
        .table("community_updates")
        .select("id,status,title,detail,source,created_at")
        .order("created_at", desc=True)
        .limit(limit)
    )
    if update_status:
        query = query.eq("status", update_status)
    try:
        response = query.execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to load updates") from exc
    return response.data


@app.post("/api/disputes", status_code=status.HTTP_201_CREATED)
def create_dispute(payload: DisputeCreate, user=Depends(get_current_user)):
    row = {
        "user_id": str(user.id),
        "concern_type": payload.concern_type,
        "desired_outcome": payload.desired_outcome,
        "contact_phone": payload.contact_phone,
        "status": "received",
    }
    try:
        response = get_admin_client().table("dispute_requests").insert(row).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to save resolution request") from exc
    dispute = _first(response.data)
    return {"id": dispute["id"], "status": dispute["status"]}


@app.post("/api/storage/upload-url")
def create_upload_url(payload: UploadUrlCreate, user=Depends(get_current_user)):
    safe_name = PurePosixPath(payload.filename).name
    path = f"{user.id}/{uuid4()}-{safe_name}"
    try:
        response = get_admin_client().storage.from_(settings.storage_bucket).create_signed_upload_url(path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to create upload URL") from exc
    data = response if isinstance(response, dict) else response.data
    return {"path": path, "token": data.get("token"), "signed_url": data.get("signedUrl") or data.get("signed_url")}
