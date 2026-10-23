from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend import main


class ReportsTable:
    def __init__(self):
        self.row = None

    def insert(self, row):
        self.row = row
        return self

    def execute(self):
        return SimpleNamespace(
            data=[
                {
                    **self.row,
                    "id": "report-id",
                    "reference": "AMN-ABC123",
                    "status": "pending",
                }
            ]
        )


class ReportsClient:
    def __init__(self):
        self.reports = ReportsTable()

    def table(self, name):
        assert name == "reports"
        return self.reports


def test_web_report_is_saved_with_normalized_ward():
    db = ReportsClient()
    triage = SimpleNamespace(
        language="en",
        normalized_text="Road blocked",
        category="local_issue",
        confidence=0.9,
        dispute_category=None,
        summary="Road blocked.",
        needs_human_review=False,
        review_reason=None,
        pii_flagged=False,
    )
    with patch.object(main, "get_admin_client", return_value=db), \
         patch.object(main, "analyze_report", return_value=triage), \
         patch.object(main, "_find_recent_duplicate", return_value=None):
        response = TestClient(main.app).post(
            "/api/reports",
            json={
                "report_type": "Local issue",
                "description": "Road blocked",
                "ward": "  Mlolongo  ",
            },
        )

    assert response.status_code == 201
    assert db.reports.row["ward"] == "Mlolongo"
    assert db.reports.row["channel"] == "web"


def test_web_report_requires_a_ward_for_routing():
    response = TestClient(main.app).post(
        "/api/reports",
        json={"report_type": "Local issue", "description": "Road blocked"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Ward is required for web reports"
