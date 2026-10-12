from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import get_settings
from supabase_client import get_admin_client, get_auth_client

bearer_scheme = HTTPBearer(auto_error=False)


def _user_from_token(token: str) -> Any:
    try:
        response = get_auth_client().auth.get_user(token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        ) from exc

    if not response.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )
    return response.user


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> Any:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required",
        )
    return _user_from_token(credentials.credentials)


def is_verification_user(user: Any) -> bool:
    email = getattr(user, "email", None)
    if not isinstance(email, str) or not email.strip():
        return False
    normalized_email = email.strip().casefold()
    settings = get_settings()
    if (
        normalized_email in settings.admin_email_set
        or normalized_email in settings.verification_queue_email_set
    ):
        return True
    response = (
        get_admin_client()
        .table("report_reviewers")
        .select("email")
        .eq("email", normalized_email)
        .limit(1)
        .execute()
    )
    return bool(response.data)


def is_admin_user(user: Any) -> bool:
    email = getattr(user, "email", None)
    return (
        isinstance(email, str)
        and email.strip().casefold() in get_settings().admin_email_set
    )


def get_verification_user(user: Any = Depends(get_current_user)) -> Any:
    if not is_verification_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access the verification queue",
        )
    return user


def get_admin_user(user: Any = Depends(get_current_user)) -> Any:
    if not is_admin_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access is required",
        )
    return user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> Any | None:
    if not credentials:
        return None
    return _user_from_token(credentials.credentials)
