from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from platform_app.explanations.models import ExplanationRequest
from platform_app.explanations.router import view
from platform_app.intake.models import now


def request_row(age=0, status="RESERVED"):
    return ExplanationRequest(
        id=uuid4(),
        assessment_id=uuid4(),
        status=status,
        model="test-model",
        price_version="test-price",
        reserved_usd=Decimal("0.01"),
        created_at=now() - timedelta(seconds=age),
        output=None,
        failure_code=None,
    )


def test_recent_reservation_remains_pending():
    assert view(request_row())["status"] == "RESERVED"


def test_crashed_request_becomes_unknown_without_changing_persisted_state():
    row = request_row(age=31)
    result = view(row)
    assert result["status"] == "INDETERMINATE"
    assert result["failure_code"] == "OUTCOME_UNKNOWN"
    assert row.status == "RESERVED"
    assert result["reserved_usd"] == "0.01"


def test_finished_request_does_not_expire():
    assert view(request_row(age=3600, status="SUCCEEDED"))["status"] == "SUCCEEDED"
