from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend import main


def report(report_id, ward, *, status="pending", priority="normal"):
    return {
        "id": report_id,
        "reference": f"AMN-{report_id.upper()}",
        "report_type": "Local issue",
        "description": f"Issue in {ward}",
        "status": status,
        "created_at": "2025-01-01T00:00:00+00:00",
        "assigned_to_email": None,
        "ai_language": "english",
        "ai_normalized_text": None,
        "ai_category": None,
        "ai_confidence": None,
        "ai_dispute_category": None,
        "ai_summary": None,
        "ai_review_required": False,
        "ai_review_reason": None,
        "ward": ward,
        "priority": priority,
        "triage_notes": None,
        "channel": "web",
        "first_response_at": None,
        "possible_duplicate_of": None,
        "ai_pii_flagged": False,
    }


class Query:
    def __init__(self, client, table):
        self.client = client
        self.table = table
        self.filters = []
        self.page_range = None
        self.selected = ""
        self.operation = "select"
        self.row = None

    def select(self, fields, **kwargs):
        self.selected = fields
        return self

    def eq(self, key, value):
        self.filters.append(("eq", key, value))
        return self

    def in_(self, key, values):
        self.filters.append(("in", key, values))
        return self

    def is_(self, key, value):
        self.filters.append(("is", key, value))
        return self

    def lt(self, key, value):
        self.filters.append(("lt", key, value))
        return self

    def order(self, *args, **kwargs):
        return self

    def range(self, low, high):
        self.page_range = (low, high)
        return self

    def limit(self, *args):
        return self

    def or_(self, *args):
        return self

    def insert(self, row):
        self.operation = "insert"
        self.row = row
        return self

    def execute(self):
        if self.operation == "insert":
            self.client.inserted.setdefault(self.table, []).extend(
                self.row if isinstance(self.row, list) else [self.row]
            )
            return SimpleNamespace(data=self.row if isinstance(self.row, list) else [self.row], count=None)
        records = list(self.client.rows.get(self.table, []))
        for operation, key, value in self.filters:
            if operation == "eq":
                records = [row for row in records if row.get(key) == value]
            elif operation == "in":
                records = [row for row in records if row.get(key) in value]
            elif operation == "is" and value == "null":
                records = [row for row in records if row.get(key) is None]
            elif operation == "lt" and key == "created_at":
                records = [
                    row for row in records
                    if row.get(key) and row[key] < value
                ]
        count = len(records)
        if self.page_range:
            low, high = self.page_range
            records = records[low:high + 1]
        return SimpleNamespace(data=records, count=count)


class ClientStub:
    def __init__(self):
        self.rows = {
            "reports": [
                report("a1", "Mlolongo", priority="urgent"),
                report("b2", "Athi River"),
            ],
            "report_events": [],
            "dispute_requests": [
                {
                    "id": "d1",
                    "concern_type": "Land or boundary",
                    "desired_outcome": "Agree a boundary",
                    "contact_phone": None,
                    "status": "received",
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "resolution_path": None,
                    "assigned_to_email": None,
                    "triage_notes": None,
                }
            ],
            "dispute_events": [
                {
                    "dispute_id": "d1",
                    "actor_email": None,
                    "action": "created",
                    "from_status": None,
                    "to_status": "received",
                    "note": None,
                    "created_at": "2026-01-01T00:00:00+00:00",
                }
            ],
        }
        self.inserted = {}
        self.rpc_calls = []

    def table(self, name):
        return Query(self, name)

    def rpc(self, name, params):
        self.rpc_calls.append((name, params))
        return SimpleNamespace(
            execute=lambda: SimpleNamespace(
                data={
                    "id": params.get("p_report_id", params.get("p_dispute_id")),
                    "reference": "AMN-A1",
                    "status": params.get("p_status", "needs_info"),
                    "ward": "Mlolongo",
                    "priority": "urgent",
                    "triage_notes": params.get("p_notes", params.get("p_note")),
                }
            )
        )


def client_with_ward_manager():
    db = ClientStub()
    user = SimpleNamespace(email="chief@example.org")
    client = TestClient(main.app)
    client.app.dependency_overrides[main.get_verification_user] = lambda: user
    return client, db, user


def test_ward_manager_queue_is_limited_by_api_to_their_ward():
    client, db, _ = client_with_ward_manager()
    with patch.object(main, "get_admin_client", return_value=db), \
         patch.object(main, "get_reviewer_profile", return_value={"ward": "Mlolongo"}), \
         patch.object(main, "is_admin_user", return_value=False):
        response = client.get("/api/reports/queue")
    client.app.dependency_overrides.clear()

    assert response.status_code == 200
    result = response.json()
    assert [item["ward"] for item in result["items"]] == ["Mlolongo"]
    assert result["items"][0]["sla_overdue"] is True
    assert result["counts"]["pending"] == 1


def test_queue_filters_and_pagination_are_applied_server_side():
    client, db, _ = client_with_ward_manager()
    with patch.object(main, "get_admin_client", return_value=db), \
         patch.object(main, "get_reviewer_profile", return_value={"ward": "Mlolongo"}), \
         patch.object(main, "is_admin_user", return_value=False):
        response = client.get(
            "/api/reports/queue?status=pending&type=Local%20issue&channel=web"
            "&priority=urgent&page=1&page_size=1"
        )
    client.app.dependency_overrides.clear()

    assert response.status_code == 200
    result = response.json()
    assert result["total"] == 1
    assert result["page_size"] == 1
    assert result["items"][0]["reference"] == "AMN-A1"


def test_ward_manager_cannot_query_or_triage_another_ward():
    client, db, _ = client_with_ward_manager()
    with patch.object(main, "get_admin_client", return_value=db), \
         patch.object(main, "get_reviewer_profile", return_value={"ward": "Mlolongo"}), \
         patch.object(main, "is_admin_user", return_value=False):
        filtered = client.get("/api/reports/queue?ward=Athi%20River")
        triage = client.patch(
            "/api/reports/b2/triage",
            json={"action": "triage", "priority": "urgent"},
        )
    client.app.dependency_overrides.clear()

    assert filtered.status_code == 403
    assert triage.status_code == 404
    assert db.rpc_calls == []


def test_ward_triage_action_calls_audited_database_operation():
    client, db, _ = client_with_ward_manager()
    with patch.object(main, "get_admin_client", return_value=db), \
         patch.object(main, "get_reviewer_profile", return_value={"ward": "Mlolongo"}), \
         patch.object(main, "is_admin_user", return_value=False):
        response = client.patch(
            "/api/reports/a1/triage",
            json={
                "action": "request_more_info",
                "priority": "urgent",
                "notes": "Please add a time and location.",
            },
        )
    client.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "needs_info"
    assert db.rpc_calls[0][0] == "update_report_triage"
    assert db.rpc_calls[0][1]["p_actor_email"] == "chief@example.org"


def test_dismiss_requires_a_reason():
    response = main.ReportTriageUpdate.model_validate(
        {"action": "dismiss", "reason": "Duplicate"}
    )
    assert response.reason == "Duplicate"

    from pydantic import ValidationError

    try:
        main.ReportTriageUpdate.model_validate({"action": "dismiss"})
    except ValidationError:
        pass
    else:
        raise AssertionError("Dismissal without a reason should be rejected")


def test_admin_can_route_and_schedule_dispute_through_audited_operation():
    client = TestClient(main.app)
    user = SimpleNamespace(email="admin@example.org")
    client.app.dependency_overrides[main.get_admin_user] = lambda: user
    db = ClientStub()
    with patch.object(main, "get_admin_client", return_value=db):
        response = client.patch(
            "/api/admin/disputes/d1",
            json={
                "resolution_path": "elder_baraza",
                "status": "scheduled",
                "note": "Baraza on Friday",
            },
        )
    client.app.dependency_overrides.clear()

    assert response.status_code == 200
    name, params = db.rpc_calls[0]
    assert name == "update_dispute"
    assert params["p_actor_email"] == "admin@example.org"
    assert params["p_status"] == "scheduled"


def test_admin_disputes_include_audit_timeline():
    client = TestClient(main.app)
    user = SimpleNamespace(email="admin@example.org")
    client.app.dependency_overrides[main.get_admin_user] = lambda: user
    with patch.object(main, "get_admin_client", return_value=ClientStub()):
        response = client.get("/api/admin/disputes")
    client.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()[0]["timeline"][0]["action"] == "created"
