from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend import main
from backend.ussd import handle_ussd


class FakeQuery:
    def __init__(self, data):
        self.data = data

    def select(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def execute(self):
        return SimpleNamespace(data=self.data)


class FakePublicClient:
    def __init__(self, rows):
        self.rows = rows

    def table(self, name):
        assert name == "public_community_updates"
        return FakeQuery(self.rows)


def test_confirmed_report_review_requires_a_source():
    client = TestClient(main.app)
    main.app.dependency_overrides[main.get_verification_user] = lambda: SimpleNamespace(
        email="reviewer@example.test"
    )
    try:
        response = client.post(
            "/api/reports/report-1/publish",
            json={
                "status": "confirmed",
                "title": "Water outage",
                "detail": "Water is unavailable near the market.",
                "verification_method": "official_notice",
                "evidence_note": "County notice checked.",
            },
        )
    finally:
        main.app.dependency_overrides.pop(main.get_verification_user, None)

    assert response.status_code == 422
    assert "source is required" in response.text


def test_author_cannot_approve_their_own_draft():
    actor = SimpleNamespace(email="author@example.test")
    update = {
        "id": "update-1",
        "author_email": "author@example.test",
        "source_report_id": "report-1",
    }
    main.app.dependency_overrides[main.get_verification_user] = lambda: actor
    try:
        with patch.object(main, "_load_community_update", return_value=update), patch.object(
            main,
            "_moderator_context",
            return_value=("Verified by Ward Office, Ward administrator", "author@example.test"),
        ), patch.object(main, "get_admin_client") as get_client:
            response = TestClient(main.app).post("/api/updates/update-1/approve")
    finally:
        main.app.dependency_overrides.pop(main.get_verification_user, None)

    assert response.status_code == 409
    assert "cannot approve your own draft" in response.json()["detail"]
    get_client.assert_not_called()


def test_public_updates_hide_reviewer_emails_and_phone_hashes_and_show_retractions():
    phone_hash = "a" * 64
    rows = [
        {
            "id": "update-1",
            "status": "confirmed",
            "workflow_status": "retracted",
            "title": "Water outage",
            "detail": "The market has a water outage.",
            "source": "County notice",
            "published_at": "2026-10-19T10:00:00Z",
            "publisher_label": "Verified by approver@example.test, Ward administrator",
            "verification_method": "official_notice",
            "correction_reason": f"The notice {phone_hash} referred to another ward.",
            "correction_history": [
                {
                    "action": "retracted",
                    "reason": f"The notice {phone_hash} referred to another ward.",
                    "actor_label": "Verified by approver@example.test, Ward administrator",
                    "created_at": "2026-10-19T11:00:00Z",
                }
            ],
            "author_email": "author@example.test",
            "approved_by_email": "approver@example.test",
            "reporter_hash": "private-phone-hash",
        }
    ]
    with patch.object(main, "get_admin_client", return_value=FakePublicClient(rows)):
        response = TestClient(main.app).get("/api/updates")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["workflow_status"] == "retracted"
    assert "[redacted]" in body[0]["correction_reason"]
    assert "author_email" not in body[0]
    assert "approved_by_email" not in body[0]
    assert "reporter_hash" not in body[0]
    assert "author@example.test" not in response.text
    assert "approver@example.test" not in response.text
    assert phone_hash not in response.text

    ussd = handle_ussd(
        "1*1",
        updates=[
            {
                "status": "confirmed",
                "workflow_status": body[0]["workflow_status"],
                "source": body[0]["source"],
                "published_at": body[0]["published_at"],
                "publisher_label": body[0]["publisher_label"],
                "correction_reason": body[0]["correction_reason"],
                "title": body[0]["title"],
            }
        ],
    )
    assert "RETRACTED" in ussd.response
    assert "County notice" in ussd.response
    assert "redacted" in ussd.response
