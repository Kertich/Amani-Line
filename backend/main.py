from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import hmac
import ipaddress
import logging
import re
from pathlib import PurePosixPath
from uuid import uuid4

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import PlainTextResponse

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from fastapi.middleware.cors import CORSMiddleware
from supabase import Client

try:
    from .auth import (
        get_current_user,
        get_optional_user,
        get_admin_user,
        get_verification_user,
        get_reviewer_profile,
        is_admin_user,
        is_verification_user,
    )
    from .config import get_settings
    from .database import engine, get_db
    from .model import Base
    from .schemas import (
        AuthCredentials,
        DisputeCreate,
        PiiReportRedaction,
        ReportCreate,
        ReportAssignmentUpdate,
        ReportQueueResponse,
        ReportReviewCreate,
        ReportReviewResponse,
        ReportTriageUpdate,
        DisputeUpdate,
        UpdateReasonCreate,
        CommunityUpdateCorrection,
        QueueResponse,
        ReviewerCreate,
        ReviewerResponse,
        UpdateResponse,
        UploadUrlCreate,
        HealthCheckResponse,
    )
    from .sms import decrypt_phone, encrypt_phone, reporter_hash, send_sms
    from .supabase_client import get_admin_client, get_auth_client
    from .triage import (
        AIProviderError,
        TriageResult,
        analyze_report,
        contains_targeted_pii,
        detect_language,
        find_duplicate,
        normalize_message,
        transcribe_audio,
    )
    from .ussd import COPY, format_sms_status, handle_ussd
except ImportError:  # pragma: no cover
    from auth import (
        get_current_user,
        get_optional_user,
        get_admin_user,
        get_verification_user,
        get_reviewer_profile,
        is_admin_user,
        is_verification_user,
    )
    from config import get_settings
    from database import engine, get_db
    from model import Base
    from schemas import (
        AuthCredentials,
        DisputeCreate,
        PiiReportRedaction,
        ReportCreate,
        ReportAssignmentUpdate,
        ReportQueueResponse,
        ReportReviewCreate,
        ReportReviewResponse,
        ReportTriageUpdate,
        DisputeUpdate,
        UpdateReasonCreate,
        CommunityUpdateCorrection,
        QueueResponse,
        ReviewerCreate,
        ReviewerResponse,
        UpdateResponse,
        UploadUrlCreate,
        HealthCheckResponse,
    )
    from sms import decrypt_phone, encrypt_phone, reporter_hash, send_sms
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
    from ussd import COPY, format_sms_status, handle_ussd

settings = get_settings()
logger = logging.getLogger(__name__)


def _public_safe_text(value):
    if not isinstance(value, str):
        return value
    value = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[redacted]", value)
    return re.sub(r"\b[a-fA-F0-9]{32,64}\b", "[redacted]", value)


def _public_safe_history(history):
    if not isinstance(history, list):
        return []
    return [
        {
            key: _public_safe_text(value) if key in {"reason", "actor_label"} else value
            for key, value in event.items()
        }
        for event in history
        if isinstance(event, dict)
    ]

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
            .in_("status", ["pending", "reviewing", "needs_info"])
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


def _save_report(
    payload: ReportCreate,
    user,
    *,
    channel: str,
    reporter: str | None = None,
    language: str | None = None,
) -> dict:
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
        "channel": channel,
        "reporter_hash": reporter,
        "language": language,
        **_triage_metadata(triage, duplicate_of),
    }
    try:
        response = get_admin_client().table("reports").insert(row).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to save report") from exc
    report = _first(response.data)
    result = {
        "id": report["id"],
        "reference": report["reference"],
        "status": report["status"],
    }
    if reporter:
        message = COPY[language or "en"]["report_saved"].format(
            reference=result["reference"]
        )
        _send_reporter_sms(reporter, message)
    return result


def _send_reporter_sms(reporter: str, message: str) -> None:
    try:
        contact = (
            get_admin_client()
            .table("reporter_contacts")
            .select("encrypted_phone")
            .eq("reporter_hash", reporter)
            .limit(1)
            .execute()
        )
        if contact.data:
            phone = decrypt_phone(contact.data[0]["encrypted_phone"], get_settings())
            send_sms(phone, message, get_settings())
    except Exception:
        logger.error("Unable to send reporter SMS")


def _authorized_at_callback(request: Request) -> None:
    configured_secret = get_settings().at_callback_secret
    supplied_secret = (
        request.headers.get("x-at-secret")
        or request.query_params.get("secret")
        or ""
    )
    if not configured_secret or not hmac.compare_digest(supplied_secret, configured_secret):
        raise HTTPException(status_code=403, detail="Forbidden")

    allowed_ips = get_settings().at_allowed_ip_set
    if not allowed_ips:
        return
    client_host = request.client.host if request.client else ""
    try:
        client_ip = ipaddress.ip_address(client_host)
        if not any(
            client_ip in ipaddress.ip_network(value, strict=False)
            for value in allowed_ips
        ):
            raise HTTPException(status_code=403, detail="Forbidden")
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="Invalid callback IP configuration") from exc


def _remember_reporter(phone: str, language: str) -> str:
    settings = get_settings()
    reporter = reporter_hash(phone, settings)
    row = {
        "reporter_hash": reporter,
        "encrypted_phone": encrypt_phone(phone, settings),
        "language": language,
    }
    try:
        get_admin_client().table("reporter_contacts").upsert(
            row, on_conflict="reporter_hash"
        ).execute()
    except Exception as exc:
        raise RuntimeError("Unable to save reporter preferences") from exc
    return reporter


def _find_report(reference: str) -> dict | None:
    if not re.fullmatch(r"AMN-[A-F0-9]{6}", reference, flags=re.IGNORECASE):
        return None
    response = (
        get_admin_client()
        .table("reports")
        .select("reference,status,language,reporter_hash")
        .eq("reference", reference.upper())
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


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
    profile = None if is_admin_user(user) else get_reviewer_profile(user)
    return {
        "user": user,
        "can_verify": is_verification_user(user),
        "can_admin": is_admin_user(user),
        "can_manage_queue": is_admin_user(user) or bool(profile and profile.get("role") == "ward_admin"),
        "ward": profile.get("ward") if profile else None,
        "display_name": profile.get("display_name") if profile else None,
        "role": "admin" if is_admin_user(user) else (profile.get("role") if profile else None),
    }


@app.post("/api/ussd", response_class=PlainTextResponse)
async def ussd_callback(request: Request):
    try:
        _authorized_at_callback(request)
    except HTTPException:
        raise
    except Exception:
        logger.exception("USSD auth check failed")
        raise HTTPException(status_code=500, detail="Service unavailable")
    try:
        form = await request.form()
        phone_number = str(form.get("phoneNumber", "") or "")
        history = str(form.get("text", "") or "")
        if not phone_number:
            return PlainTextResponse("END Service unavailable. Try again later.")
        settings = get_settings()
        try:
            reporter = reporter_hash(phone_number, settings)
            known = (
                get_admin_client()
                .table("reporter_contacts")
                .select("language")
                .eq("reporter_hash", reporter)
                .limit(1)
                .execute()
            )
            language = known.data[0]["language"] if known.data else "en"
        except Exception:
            language = "en"
            reporter = reporter_hash(phone_number, settings)

        update_list = []
        try:
            response = (
                get_admin_client()
                .table("public_community_updates")
                .select("status,workflow_status,title,detail,source,published_at,activity_at,publisher_label,correction_reason")
                .order("activity_at", desc=True)
                .limit(5)
                .execute()
            )
            update_list = [
                {
                    **item,
                    "title": _public_safe_text(item.get("title")),
                    "source": _public_safe_text(item.get("source")),
                    "publisher_label": _public_safe_text(item.get("publisher_label")),
                    "correction_reason": _public_safe_text(item.get("correction_reason")),
                }
                for item in response.data
            ]
        except Exception:
            logger.exception("Unable to load public updates for USSD")
            return PlainTextResponse(f"END {COPY[language]['unavailable']}")

        result = handle_ussd(history, updates=update_list, report_status=None)
        action = result.action or ""
        if action == "create_report":
            payload = ReportCreate(
                report_type=result.data["report_type"],
                description=result.data["description"],
            )
            report = _save_report(
                payload,
                user=None,
                channel="ussd",
                reporter=reporter,
                language=language,
            )
            return PlainTextResponse(
                f"END {COPY[language]['report_saved'].format(reference=report['reference'])}"
            )
        if action == "status":
            ref = (result.data or {}).get("reference", "")
            lookup = _find_report(ref) or {}
            status_value = lookup.get("status", "unknown")
            text = format_sms_status(ref, status_value, language)
            return PlainTextResponse(f"END {text}")
        return PlainTextResponse(f"{result.response}")
    except Exception:
        logger.exception("USSD callback failed")
        return PlainTextResponse("END Service unavailable. Try again later.")


@app.post("/api/sms/inbound")
async def inbound_sms(request: Request):
    try:
        _authorized_at_callback(request)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Inbound SMS auth check failed")
        raise HTTPException(status_code=500, detail="Service unavailable")
    try:
        form = await request.form()
        from_number = str(form.get("from", "") or "")
        body = str(form.get("text", "") or "").strip()
        if not from_number or not body:
            raise HTTPException(status_code=400, detail="Invalid SMS payload")
        settings = get_settings()
        reporter = reporter_hash(from_number, settings)
        try:
            contact = (
                get_admin_client()
                .table("reporter_contacts")
                .select("language")
                .eq("reporter_hash", reporter)
                .limit(1)
                .execute()
            )
            language = contact.data[0]["language"] if contact.data else "en"
        except Exception:
            language = "en"
        if body.upper().startswith("STATUS "):
            reference = body.split(None, 1)[1].strip().upper()
            report = _find_report(reference)
            if not report:
                return {"status": "not_found"}
            value = format_sms_status(reference, str(report.get("status", "pending")), language)
            send_sms(from_number, value, settings)
            return {"status": "ok", "message": value}
        if body.upper().startswith("VERIFY "):
            text = body.split(None, 1)[1].strip()
            payload = ReportCreate(report_type="Rumour to check", description=text)
            report = _save_report(payload, None, channel="sms", reporter=reporter, language=language)
            send_sms(from_number, f"{report['reference']}: sent", settings)
            return {"status": "ok", "reference": report["reference"]}
        return {"status": "ignored"}
    except Exception as exc:
        logger.exception("Inbound SMS failed")
        raise HTTPException(status_code=500, detail="Service unavailable") from exc


@app.post("/api/reports", status_code=status.HTTP_201_CREATED)
def create_report(payload: ReportCreate, user=Depends(get_optional_user)):
    return _save_report(payload, user, channel="web")


REPORT_FIELDS = (
    "id,reference,report_type,description,status,created_at,assigned_to_email,"
    "ai_language,ai_normalized_text,ai_category,ai_confidence,"
    "ai_dispute_category,ai_summary,ai_review_required,ai_review_reason,"
    "ward,priority,triage_notes,channel,first_response_at,possible_duplicate_of"
)
REPORT_STATUSES = ("pending", "reviewing", "needs_info", "resolved", "dismissed")
OPEN_REPORT_STATUSES = ("pending", "reviewing", "needs_info")


def _queue_access(user) -> dict:
    if is_admin_user(user):
        return {"admin": True, "ward": None, "role": "admin", "email": user.email.strip().casefold()}
    profile = get_reviewer_profile(user)
    email = user.email.strip().casefold()
    return {
        "admin": False,
        "ward": profile.get("ward") if profile else None,
        "role": profile.get("role") if profile else None,
        "email": email,
    }


def _scope_report_query(query, access: dict):
    if access["admin"]:
        return query
    if access["ward"]:
        return query.eq("ward", access["ward"])
    return query.eq("assigned_to_email", access["email"])


def _authorized_report(report_id: str, user, *, manage: bool = False) -> dict:
    access = _queue_access(user)
    query = get_admin_client().table("reports").select(
        "id,reference,status,ward,assigned_to_email,ai_pii_flagged,first_response_at"
    ).eq("id", report_id).limit(1)
    query = _scope_report_query(query, access)
    if not access["admin"] and not access["ward"] and manage:
        raise HTTPException(status_code=403, detail="Report management requires a ward administrator")
    try:
        response = query.execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to verify report access") from exc
    if not response.data:
        raise HTTPException(status_code=404, detail="Report not found")
    if response.data[0]["ai_pii_flagged"] and not access["admin"]:
        raise HTTPException(status_code=404, detail="Report not found")
    return response.data[0]


def _write_report_event(
    report_id: str,
    user,
    *,
    action: str,
    from_status: str | None,
    to_status: str | None,
    note: str | None = None,
) -> None:
    actor_email = getattr(user, "email", None)
    if not actor_email:
        raise HTTPException(status_code=403, detail="A verified account email is required")
    try:
        get_admin_client().table("report_events").insert(
            {
                "report_id": report_id,
                "actor_email": actor_email.strip().casefold(),
                "action": action,
                "from_status": from_status,
                "to_status": to_status,
                "note": note,
            }
        ).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to write report audit event") from exc


def _report_with_sla(item: dict) -> dict:
    now = datetime.now(timezone.utc)
    created = datetime.fromisoformat(str(item["created_at"]).replace("Z", "+00:00"))
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    first_response = item.get("first_response_at")
    completed = (
        datetime.fromisoformat(str(first_response).replace("Z", "+00:00"))
        if first_response
        else now
    )
    if completed.tzinfo is None:
        completed = completed.replace(tzinfo=timezone.utc)
    age_hours = max(0.0, (completed - created).total_seconds() / 3600)
    return {
        **item,
        "sla_age_hours": round(age_hours, 1),
        "sla_overdue": (
            item.get("status") in OPEN_REPORT_STATUSES
            and first_response is None
            and age_hours >= 24
        ),
    }


def _possible_duplicates(records: list[dict], access: dict) -> dict[str, list[dict]]:
    duplicates = {item["id"]: [] for item in records}
    if not records:
        return duplicates
    report_ids = [item["id"] for item in records]
    related = (
        get_admin_client()
        .table("reports")
        .select("id,reference,description,status,ward,possible_duplicate_of")
        .eq("ai_pii_flagged", False)
    )
    related = _scope_report_query(related, access)
    clauses = ["possible_duplicate_of.in.(" + ",".join(report_ids) + ")"]
    possible_parents = [
        item["possible_duplicate_of"]
        for item in records
        if item.get("possible_duplicate_of")
    ]
    if possible_parents:
        clauses.append("id.in.(" + ",".join(possible_parents) + ")")
    candidates = related.or_(",".join(clauses)).execute().data
    by_id = {item["id"]: item for item in candidates}
    for item in records:
        parent = by_id.get(item.get("possible_duplicate_of"))
        if parent:
            duplicates[item["id"]].append(parent)
    for candidate in candidates:
        parent_id = candidate.get("possible_duplicate_of")
        if parent_id in duplicates:
            duplicates[parent_id].append(candidate)
    return duplicates


def _status_counts(
    access: dict,
    *,
    report_type: str | None,
    ward: str | None,
    channel: str | None,
    priority: str | None,
    search: str | None,
) -> dict[str, int]:
    counts = {}
    for report_status in REPORT_STATUSES:
        query = (
            get_admin_client()
            .table("reports")
            .select("id", count="exact")
            .eq("status", report_status)
            .eq("ai_pii_flagged", False)
        )
        query = _scope_report_query(query, access)
        if report_type:
            query = query.eq("report_type", report_type)
        if access["admin"] and ward:
            query = query.eq("ward", ward)
        if channel:
            query = query.eq("channel", channel)
        if priority:
            query = query.eq("priority", priority)
        if search:
            safe_search = re.sub(r"[^\w\s-]", "", search).strip()
            if safe_search:
                pattern = f"%{safe_search}%"
                query = query.or_(
                    f"reference.ilike.{pattern},description.ilike.{pattern}"
                )
        counts[report_status] = query.execute().count or 0
    return counts


@app.get("/api/reports/queue", response_model=QueueResponse)
def list_report_queue(
    status_filter: str | None = Query(default=None, alias="status"),
    report_type: str | None = Query(default=None, alias="type"),
    ward: str | None = Query(default=None, max_length=120),
    channel: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    search: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    user=Depends(get_verification_user),
):
    if status_filter and status_filter not in REPORT_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid report status filter")
    if channel and channel not in {"web", "ussd", "sms"}:
        raise HTTPException(status_code=422, detail="Invalid report channel filter")
    if priority and priority not in {"low", "normal", "urgent"}:
        raise HTTPException(status_code=422, detail="Invalid report priority filter")
    if report_type and report_type not in {
        "Rumour to check", "Local issue", "Safety concern"
    }:
        raise HTTPException(status_code=422, detail="Invalid report type filter")
    access = _queue_access(user)
    if access["ward"] and ward and ward.casefold() != access["ward"].casefold():
        raise HTTPException(status_code=403, detail="Reports are restricted to your ward")

    try:
        base = (
            get_admin_client()
            .table("reports")
            .select(REPORT_FIELDS, count="exact")
            .eq("ai_pii_flagged", False)
            .order("created_at", desc=True)
        )
        base = _scope_report_query(base, access)
        if status_filter:
            base = base.eq("status", status_filter)
        elif not access["admin"] or access["ward"]:
            base = base.in_("status", OPEN_REPORT_STATUSES)
        if report_type:
            base = base.eq("report_type", report_type)
        if access["admin"] and ward:
            base = base.eq("ward", ward)
        if channel:
            base = base.eq("channel", channel)
        if priority:
            base = base.eq("priority", priority)
        if search:
            safe_search = re.sub(r"[^\w\s-]", "", search).strip()
            if safe_search:
                pattern = f"%{safe_search}%"
                base = base.or_(
                    f"reference.ilike.{pattern},description.ilike.{pattern}"
                )
        response = base.range((page - 1) * page_size, page * page_size - 1).execute()

        records = response.data
        duplicates_by_report = _possible_duplicates(records, access)

        items = []
        for item in records:
            related = duplicates_by_report[item["id"]]
            items.append(
                _report_with_sla(
                    {
                        **item,
                        "duplicate_count": len(related),
                        "possible_duplicates": related,
                    }
                )
            )

        urgent_query = (
            get_admin_client()
            .table("reports")
            .select(REPORT_FIELDS, count="exact")
            .eq("ai_pii_flagged", False)
            .in_("status", OPEN_REPORT_STATUSES)
            .eq("priority", "urgent")
            .order("created_at")
            .limit(20)
        )
        urgent_query = _scope_report_query(urgent_query, access)
        urgent = urgent_query.execute().data
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        overdue_query = (
            get_admin_client()
            .table("reports")
            .select(REPORT_FIELDS)
            .eq("ai_pii_flagged", False)
            .in_("status", OPEN_REPORT_STATUSES)
            .is_("first_response_at", "null")
            .lt("created_at", cutoff)
            .order("created_at")
            .limit(20)
        )
        overdue_query = _scope_report_query(overdue_query, access)
        urgent_by_id = {item["id"]: item for item in urgent}
        urgent_by_id.update({item["id"]: item for item in overdue_query.execute().data})
        urgent_records = list(urgent_by_id.values())
        urgent_duplicates = _possible_duplicates(urgent_records, access)
        urgent_items = [
            _report_with_sla(
                {
                    **item,
                    "possible_duplicates": urgent_duplicates[item["id"]],
                    "duplicate_count": len(urgent_duplicates[item["id"]]),
                }
            )
            for item in sorted(
                urgent_records,
                key=lambda value: (
                    value.get("priority") != "urgent",
                    value["created_at"],
                ),
            )
        ]
        counts = _status_counts(
            access,
            report_type=report_type,
            ward=ward,
            channel=channel,
            priority=priority,
            search=search,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to load report queue") from exc
    return {
        "items": items,
        "total": response.count or 0,
        "page": page,
        "page_size": page_size,
        "counts": counts,
        "urgent_or_overdue": urgent_items,
    }


@app.get("/api/reports/reviewers")
def list_queue_reviewers(user=Depends(get_verification_user)):
    access = _queue_access(user)
    if not access["admin"] and not access["ward"]:
        raise HTTPException(status_code=403, detail="Reviewer management requires a ward administrator")
    query = get_admin_client().table("report_reviewers").select(
        "email,display_name,ward"
    ).order("display_name")
    if access["ward"] and not access["admin"]:
        query = query.eq("ward", access["ward"])
    try:
        return query.execute().data
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to load reviewers") from exc


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
            .in_("status", ["pending", "reviewing", "needs_info"])
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
            .in_("status", ["pending", "reviewing", "needs_info"])
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
    updated = _first(response.data)
    _write_report_event(
        report_id,
        user,
        action="pii_redacted",
        from_status=updated["status"],
        to_status=updated["status"],
        note="Administrator redacted identifying details",
    )
    return updated


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
            .select("email,created_at,display_name,ward,role")
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
            "display_name": None,
            "ward": None,
            "role": "reviewer",
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
            .upsert(
                {
                    "email": email,
                    "display_name": (
                        payload.display_name.strip() or None
                        if payload.display_name
                        else None
                    ),
                    "ward": payload.ward.strip() or None if payload.ward else None,
                    "role": "ward_admin" if payload.ward and payload.ward.strip() else "reviewer",
                },
                on_conflict="email",
            )
            .select("email,created_at,display_name,ward,role")
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
        affected = (
            get_admin_client()
            .table("reports")
            .select("id,status")
            .eq("assigned_to_email", normalized_email)
            .in_("status", ["pending", "reviewing", "needs_info"])
            .execute()
        ).data
        for item in affected:
            get_admin_client().rpc(
                "assign_report",
                {
                    "p_report_id": item["id"],
                    "p_actor_email": user.email.strip().casefold(),
                    "p_assigned_to_email": None,
                },
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
    user=Depends(get_verification_user),
):
    access = _queue_access(user)
    if not access["admin"] and not access["ward"]:
        raise HTTPException(status_code=403, detail="Reviewer assignment requires a ward administrator")
    report = _authorized_report(report_id, user, manage=True)
    if report["status"] not in OPEN_REPORT_STATUSES:
        raise HTTPException(status_code=409, detail="This report is no longer open for assignment")
    email = payload.assigned_to_email.strip().casefold() if payload.assigned_to_email else None
    selected_reviewer = None
    if email:
        try:
            reviewer = (
                get_admin_client()
                .table("report_reviewers")
                .select("email,ward")
                .eq("email", email)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail="Unable to validate reviewer") from exc
        if reviewer.data:
            selected_reviewer = reviewer.data[0]
        if not selected_reviewer and email not in get_settings().verification_queue_email_set:
            raise HTTPException(status_code=422, detail="Choose an authorized reviewer")
    if (
        access["ward"]
        and not access["admin"]
        and email
        and (not selected_reviewer or selected_reviewer.get("ward") != access["ward"])
    ):
        raise HTTPException(status_code=403, detail="You can assign only reviewers in your ward")
    if (
        access["ward"]
        and not access["admin"]
        and report.get("ward") != access["ward"]
    ):
        raise HTTPException(status_code=403, detail="Reports are restricted to your ward")
    try:
        response = (
            get_admin_client()
            .rpc(
                "assign_report",
                {
                    "p_report_id": report_id,
                    "p_actor_email": access["email"],
                    "p_assigned_to_email": email,
                },
            )
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to assign report") from exc
    return response.data


@app.patch("/api/reports/{report_id}/triage")
def triage_report(
    report_id: str,
    payload: ReportTriageUpdate,
    user=Depends(get_verification_user),
):
    access = _queue_access(user)
    report = _authorized_report(report_id, user)
    if report["status"] not in OPEN_REPORT_STATUSES:
        raise HTTPException(status_code=409, detail="This report is no longer open for triage")
    if payload.ward and access["ward"] and not access["admin"]:
        if payload.ward.strip().casefold() != access["ward"].casefold():
            raise HTTPException(status_code=403, detail="You can triage only reports in your ward")
    if payload.ward and not access["admin"] and not access["ward"]:
        raise HTTPException(status_code=403, detail="Only administrators can set a report ward")
    requested_ward = payload.ward
    if requested_ward and access["ward"] and not access["admin"]:
        requested_ward = access["ward"]
    try:
        response = get_admin_client().rpc(
            "update_report_triage",
            {
                "p_report_id": report_id,
                "p_actor_email": access["email"],
                "p_action": payload.action,
                "p_priority": payload.priority,
                "p_ward": requested_ward,
                "p_notes": payload.notes,
                "p_reason": payload.reason,
            },
        ).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to update report triage") from exc
    return response.data


@app.get("/api/reports/{report_id}/events")
def report_timeline(
    report_id: str,
    user=Depends(get_verification_user),
):
    _authorized_report(report_id, user)
    try:
        response = (
            get_admin_client()
            .table("report_events")
            .select("actor_email,action,from_status,to_status,note,created_at")
            .eq("report_id", report_id)
            .order("created_at")
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to load report timeline") from exc
    return response.data


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
        report_state = _authorized_report(report_id, user)
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(status_code=500, detail="Unable to verify report safety status") from exc
    if report_state["status"] not in OPEN_REPORT_STATUSES:
        raise HTTPException(status_code=404, detail="Report not found or already reviewed")
    if report_state["ai_pii_flagged"]:
        raise HTTPException(
            status_code=409,
            detail="This report is privately escalated and must be redacted by an administrator before publication",
        )
    access = _queue_access(user)
    if access["ward"] and report_state.get("ward") != access["ward"]:
        raise HTTPException(status_code=403, detail="Reports are restricted to your ward")
    actor_email = access["email"]
    direct_publish = access["admin"]
    publisher_label = _publisher_label(user, direct_publish=direct_publish)
    try:
        response = get_admin_client().rpc(
            "review_report",
            {
                "p_report_id": report_id,
                "p_update_status": payload.status,
                "p_title": payload.title,
                "p_detail": payload.detail,
                "p_source": payload.source,
                "p_actor_email": actor_email,
                "p_action": "publish_directly" if direct_publish else "submit",
                "p_verification_method": payload.verification_method,
                "p_evidence_url": payload.evidence_url,
                "p_evidence_note": payload.evidence_note,
                "p_publisher_label": publisher_label,
            },
        ).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to publish report") from exc
    result = _first(response.data)
    return {
        "id": report_id,
        "status": payload.status,
        "community_update_id": result["community_update_id"],
        "workflow_status": result["workflow_status"],
    }


def _publisher_label(user, *, direct_publish: bool = False) -> str:
    profile = None if is_admin_user(user) else get_reviewer_profile(user)
    display_name = (
        (profile.get("display_name") or "").strip()
        if profile
        else ""
    )
    if (
        re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", display_name)
        or re.search(r"\+?\d[\d\s().-]{7,}\d", display_name)
        or re.fullmatch(r"[a-fA-F0-9]{32,64}", display_name)
    ):
        display_name = ""
    if not display_name:
        display_name = "Amani Line"
    if direct_publish or is_admin_user(user):
        role = "Administrator"
    elif profile and profile.get("role") == "ward_admin":
        role = "Ward administrator"
    else:
        role = "Community reviewer"
    ward = (profile.get("ward") or "").strip() if profile else ""
    label = f"Verified by {display_name}, {role}"
    if ward:
        label = f"{label}, {ward}"
    return label


def _load_community_update(update_id: str) -> dict:
    try:
        response = (
            get_admin_client()
            .table("community_updates")
            .select(
                "id,status,workflow_status,title,detail,source,author_email,"
                "source_report_id,verification_method,evidence_url,evidence_note"
            )
            .eq("id", update_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to load community update") from exc
    if not response.data:
        raise HTTPException(status_code=404, detail="Community update not found")
    return response.data[0]


def _moderator_context(user, update: dict) -> tuple[str, str]:
    if is_admin_user(user):
        return _publisher_label(user, direct_publish=True), user.email.strip().casefold()
    profile = get_reviewer_profile(user)
    if (
        not profile
        or profile.get("role") != "ward_admin"
        or not (profile.get("ward") or "").strip()
    ):
        raise HTTPException(status_code=403, detail="Ward administrator access is required")
    report_id = update.get("source_report_id")
    if not report_id:
        raise HTTPException(status_code=403, detail="This update is outside your ward scope")
    report = _authorized_report(str(report_id), user)
    if report.get("ward") != profile.get("ward"):
        raise HTTPException(status_code=403, detail="This update is outside your ward scope")
    return _publisher_label(user), user.email.strip().casefold()


@app.get("/api/updates/pending")
def list_pending_updates(user=Depends(get_verification_user)):
    try:
        response = (
            get_admin_client()
            .table("community_updates")
            .select(
                "id,status,title,detail,source,author_email,source_report_id,"
                "verification_method,evidence_url,evidence_note"
            )
            .eq("workflow_status", "pending_approval")
            .order("created_at")
            .limit(100)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to load pending updates") from exc
    access = _queue_access(user)
    items = []
    for item in response.data:
        if not access["admin"]:
            if (
                access["role"] != "ward_admin"
                or not access["ward"]
                or not item.get("source_report_id")
            ):
                continue
            try:
                report_response = (
                    get_admin_client()
                    .table("reports")
                    .select("ward")
                    .eq("id", item["source_report_id"])
                    .limit(1)
                    .execute()
                )
            except Exception as exc:
                raise HTTPException(status_code=500, detail="Unable to scope pending updates") from exc
            if not report_response.data or report_response.data[0].get("ward") != access["ward"]:
                continue
        items.append({
            "id": item["id"],
            "status": item["status"],
            "title": item["title"],
            "detail": item["detail"],
            "source": item.get("source"),
            "verification_method": item.get("verification_method"),
            "evidence_url": item.get("evidence_url"),
            "evidence_note": item.get("evidence_note"),
            "author_label": "Reviewer",
            "authored_by_you": (item.get("author_email") or "").casefold()
            == user.email.strip().casefold(),
        })
    return items


@app.post("/api/updates/{update_id}/approve")
def approve_update(update_id: str, user=Depends(get_verification_user)):
    update = _load_community_update(update_id)
    actor_label, actor_email = _moderator_context(user, update)
    if (update.get("author_email") or "").casefold() == actor_email:
        raise HTTPException(status_code=409, detail="You cannot approve your own draft")
    try:
        response = get_admin_client().rpc(
            "moderate_community_update",
            {
                "p_update_id": update_id,
                "p_actor_email": actor_email,
                "p_actor_label": actor_label,
                "p_action": "approve",
                "p_reason": None,
                "p_publisher_label": actor_label,
            },
        ).execute()
    except Exception as exc:
        raise HTTPException(status_code=409, detail="Unable to approve this update") from exc
    return _first(response.data)


@app.post("/api/updates/{update_id}/reject")
def reject_update(
    update_id: str,
    payload: UpdateReasonCreate,
    user=Depends(get_verification_user),
):
    update = _load_community_update(update_id)
    actor_label, actor_email = _moderator_context(user, update)
    try:
        response = get_admin_client().rpc(
            "moderate_community_update",
            {
                "p_update_id": update_id,
                "p_actor_email": actor_email,
                "p_actor_label": actor_label,
                "p_action": "reject",
                "p_reason": payload.reason,
                "p_publisher_label": None,
            },
        ).execute()
    except Exception as exc:
        raise HTTPException(status_code=409, detail="Unable to reject this update") from exc
    return _first(response.data)


@app.post("/api/updates/{update_id}/correction")
def correct_update(
    update_id: str,
    payload: CommunityUpdateCorrection,
    user=Depends(get_verification_user),
):
    update = _load_community_update(update_id)
    actor_label, actor_email = _moderator_context(user, update)
    try:
        response = get_admin_client().rpc(
            "moderate_community_update",
            {
                "p_update_id": update_id,
                "p_actor_email": actor_email,
                "p_actor_label": actor_label,
                "p_action": payload.action,
                "p_reason": payload.reason,
                "p_publisher_label": None,
            },
        ).execute()
    except Exception as exc:
        raise HTTPException(status_code=409, detail="Unable to record this correction") from exc
    return _first(response.data)


@app.get("/api/updates", response_model=list[UpdateResponse])
def list_updates(
    update_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
):
    query = (
        get_admin_client()
        .table("public_community_updates")
        .select(
            "id,status,workflow_status,title,detail,source,published_at,"
            "publisher_label,verification_method,correction_reason,"
            "correction_history,activity_at"
        )
        .order("activity_at", desc=True)
        .limit(limit)
    )
    if update_status:
        if update_status == "corrections":
            query = query.in_("workflow_status", ["corrected", "retracted"])
        else:
            query = query.eq("status", update_status)
    try:
        response = query.execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to load updates") from exc
    public_fields = (
        "id", "status", "workflow_status", "title", "detail", "source",
        "published_at", "publisher_label", "verification_method",
        "correction_reason", "correction_history",
    )
    updates = []
    for item in response.data:
        public_item = {key: item.get(key) for key in public_fields}
        for key in ("title", "detail", "source", "publisher_label", "correction_reason"):
            public_item[key] = _public_safe_text(public_item.get(key))
        public_item["correction_history"] = _public_safe_history(
            public_item.get("correction_history")
        )
        updates.append(public_item)
    return updates


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


@app.get("/api/admin/disputes")
def list_disputes(
    dispute_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    user=Depends(get_admin_user),
):
    if dispute_status and dispute_status not in {"received", "scheduled", "closed"}:
        raise HTTPException(status_code=422, detail="Invalid dispute status")
    query = (
        get_admin_client()
        .table("dispute_requests")
        .select(
            "id,concern_type,desired_outcome,contact_phone,status,created_at,"
            "resolution_path,assigned_to_email,triage_notes"
        )
        .order("created_at", desc=True)
        .limit(limit)
    )
    if dispute_status:
        query = query.eq("status", dispute_status)
    try:
        disputes = query.execute().data
        if not disputes:
            return []
        events = (
            get_admin_client()
            .table("dispute_events")
            .select("dispute_id,actor_email,action,from_status,to_status,note,created_at")
            .in_("dispute_id", [item["id"] for item in disputes])
            .order("created_at")
            .execute()
        ).data
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to load disputes") from exc
    by_dispute: dict[str, list[dict]] = {item["id"]: [] for item in disputes}
    for event in events:
        by_dispute[event["dispute_id"]].append(event)
    return [
        {**item, "timeline": by_dispute[item["id"]]}
        for item in disputes
    ]


@app.patch("/api/admin/disputes/{dispute_id}")
def update_dispute(
    dispute_id: str,
    payload: DisputeUpdate,
    user=Depends(get_admin_user),
):
    if not any(
        value is not None
        for value in (
            payload.resolution_path,
            payload.status,
            payload.assigned_to_email,
            payload.note,
        )
    ):
        raise HTTPException(status_code=422, detail="Provide at least one dispute update")
    assigned_email = (
        payload.assigned_to_email.strip().casefold()
        if payload.assigned_to_email
        else None
    )
    try:
        response = get_admin_client().rpc(
            "update_dispute",
            {
                "p_dispute_id": dispute_id,
                "p_actor_email": user.email.strip().casefold(),
                "p_resolution_path": payload.resolution_path,
                "p_assigned_to_email": assigned_email,
                "p_status": payload.status,
                "p_note": payload.note,
            },
        ).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to update dispute") from exc
    return response.data


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
