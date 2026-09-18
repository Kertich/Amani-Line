from datetime import datetime, timezone
from pathlib import PurePosixPath
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from supabase import Client

from .auth import get_current_user, get_optional_user
from .config import get_settings
from .schemas import (
    AuthCredentials,
    DisputeCreate,
    ReportCreate,
    UpdateResponse,
    UploadUrlCreate,
)
from .supabase import get_admin_client, get_auth_client

settings = get_settings()
app = FastAPI(title="Amani Line API", version="1.0.0")
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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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
    return {"user": user}


@app.post("/api/reports", status_code=status.HTTP_201_CREATED)
def create_report(payload: ReportCreate, user=Depends(get_optional_user)):
    row = {
        "report_type": payload.report_type,
        "description": payload.description,
        "attachment_path": payload.attachment_path,
        "status": "pending",
        "user_id": str(user.id) if user else None,
    }
    try:
        response = get_admin_client().table("reports").insert(row).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to save report") from exc
    report = _first(response.data)
    return {"id": report["id"], "reference": report["reference"], "status": report["status"]}


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
