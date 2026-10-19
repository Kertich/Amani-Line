import hashlib
import hmac
from functools import lru_cache

import httpx
from cryptography.fernet import Fernet, InvalidToken

try:
    from .config import Settings
except ImportError:  # pragma: no cover
    from config import Settings


def reporter_hash(phone_number: str, settings: Settings) -> str:
    if not settings.reporter_hmac_pepper:
        raise RuntimeError("Reporter HMAC pepper is not configured")
    normalized = "".join(phone_number.split())
    return hmac.new(
        settings.reporter_hmac_pepper.encode(),
        normalized.encode(),
        hashlib.sha256,
    ).hexdigest()


@lru_cache
def _fernet(key: str) -> Fernet:
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError) as exc:
        raise RuntimeError("Reporter phone encryption key is invalid") from exc


def encrypt_phone(phone_number: str, settings: Settings) -> str:
    if not settings.reporter_phone_encryption_key:
        raise RuntimeError("Reporter phone encryption key is not configured")
    normalized = "".join(phone_number.split())
    return _fernet(settings.reporter_phone_encryption_key).encrypt(
        normalized.encode()
    ).decode()


def decrypt_phone(encrypted_phone: str, settings: Settings) -> str:
    if not settings.reporter_phone_encryption_key:
        raise RuntimeError("Reporter phone encryption key is not configured")
    try:
        return _fernet(settings.reporter_phone_encryption_key).decrypt(
            encrypted_phone.encode()
        ).decode()
    except (InvalidToken, ValueError) as exc:
        raise RuntimeError("Unable to decrypt reporter contact") from exc


def send_sms(phone_number: str, message: str, settings: Settings) -> dict[str, bool]:
    if not settings.at_api_key:
        return {"mock": True}

    response = httpx.post(
        settings.at_sms_url,
        headers={"apiKey": settings.at_api_key, "Accept": "application/json"},
        data={
            "username": settings.at_username,
            "to": phone_number,
            "message": message[:160],
        },
        timeout=10,
    )
    response.raise_for_status()
    return {"mock": False}
