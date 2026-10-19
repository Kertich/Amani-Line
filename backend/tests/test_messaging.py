from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from backend import main
from backend.triage import TriageResult


def build_settings():
    return SimpleNamespace(
        at_callback_secret="secret",
        at_allowed_ips="",
        at_api_key="",
        at_username="sandbox",
        at_sms_url="https://example.com/sms",
        at_shortcode="40404",
        reporter_hmac_pepper="pepper",
        reporter_phone_encryption_key=Fernet.generate_key().decode(),
        supabase_url="https://example.com",
        supabase_anon_key="anon",
        supabase_service_role_key="service",
        cors_origins="http://localhost:5173",
        storage_bucket="report-attachments",
        admin_emails="",
        verification_queue_emails="",
        database_url="postgresql+asyncpg://example",
        ai_api_key="",
        ai_base_url="https://api.example.com/v1",
        ai_chat_model="gpt-4o-mini",
        ai_transcription_model="whisper-1",
        allowed_origins=["http://localhost:5173"],
        admin_email_set=set(),
        verification_queue_email_set=set(),
        at_allowed_ip_set=set(),
    )


class FakeTable:
    def __init__(self, name, settings):
        self.name = name
        self.settings = settings
        self.action = None
        self.row = None
        self.filters = []

    def select(self, *args, **kwargs):
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def insert(self, row):
        self.action = "insert"
        self.row = row
        return self

    def upsert(self, row, on_conflict=None):
        self.action = "upsert"
        self.row = row
        return self

    def execute(self):
        if self.name == "community_updates":
            return MagicMock(data=[{"status": "confirmed", "title": "Market flood", "source": "County", "created_at": "2024-01-01T00:00:00Z"}])
        if self.name == "reporter_contacts":
            if self.action == "upsert":
                return MagicMock(data=[self.row])
            if self.filters and self.filters[0][0] == "reporter_hash":
                phone = "+254700000001"
                payload = {"language": "en", "encrypted_phone": main.encrypt_phone(phone, self.settings)}
                return MagicMock(data=[payload])
            return MagicMock(data=[])
        if self.name == "reports":
            if self.action == "insert":
                return MagicMock(data=[{"id": "r1", "reference": "AMN-ABC123", "status": "pending"}])
            if self.filters and self.filters[0][0] == "reference":
                return MagicMock(data=[{"reference": "AMN-ABC123", "status": "pending", "language": "en", "reporter_hash": "hash"}])
            return MagicMock(data=[])
        return MagicMock(data=[])


class FakeSupabaseClient:
    def __init__(self, settings):
        self.settings = settings

    def table(self, name):
        return FakeTable(name, self.settings)


def test_ussd_callback_rejects_missing_secret():
    settings = build_settings()
    with patch.object(main, "get_settings", return_value=settings), patch.object(main, "get_admin_client", return_value=FakeSupabaseClient(settings)):
        client = TestClient(main.app)
        response = client.post(
            "/api/ussd",
            data={
                "sessionId": "s1",
                "serviceCode": "*384*123#",
                "phoneNumber": "+254700000001",
                "networkCode": "",
                "text": "1*2*1*Fire near the market",
            },
            headers={"x-at-secret": "wrong"},
        )
    assert response.status_code == 403


def test_ussd_callback_creates_report_from_menu_flow():
    settings = build_settings()
    triage = TriageResult(
        language="english",
        normalized_text="fire near the market",
        category="incident",
        confidence=0.9,
        dispute_category=None,
        summary="Fire near the market.",
        needs_human_review=False,
        review_reason=None,
        pii_flagged=False,
    )
    with patch.object(main, "get_settings", return_value=settings), \
         patch.object(main, "get_admin_client", return_value=FakeSupabaseClient(settings)), \
         patch.object(main, "analyze_report", return_value=triage), \
         patch.object(main, "_find_recent_duplicate", return_value=None), \
         patch.object(main, "send_sms"), \
         patch.object(main, "decrypt_phone", return_value="+254700000001"):
        client = TestClient(main.app)
        response = client.post(
            "/api/ussd",
            data={
                "sessionId": "s1",
                "serviceCode": "*384*123#",
                "phoneNumber": "+254700000001",
                "networkCode": "",
                "text": "1*2*1*Fire near the market",
            },
            headers={"x-at-secret": "secret"},
        )
    assert response.status_code == 200
    assert "AMN-ABC123" in response.text
    assert "Report received" in response.text


def test_inbound_sms_verify_creates_report_and_returns_reference():
    settings = build_settings()
    triage = TriageResult(
        language="english",
        normalized_text="water is blocked",
        category="incident",
        confidence=0.9,
        dispute_category=None,
        summary="Water is blocked.",
        needs_human_review=False,
        review_reason=None,
        pii_flagged=False,
    )
    with patch.object(main, "get_settings", return_value=settings), \
         patch.object(main, "get_admin_client", return_value=FakeSupabaseClient(settings)), \
         patch.object(main, "analyze_report", return_value=triage), \
         patch.object(main, "_find_recent_duplicate", return_value=None), \
         patch.object(main, "send_sms"), \
         patch.object(main, "decrypt_phone", return_value="+254700000001"):
        client = TestClient(main.app)
        response = client.post(
            "/api/sms/inbound",
            data={"from": "+254700000001", "text": "VERIFY Water is blocked"},
            headers={"x-at-secret": "secret"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["reference"] == "AMN-ABC123"
