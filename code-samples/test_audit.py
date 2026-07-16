"""Tests for the audit logging example."""

import pytest
from unittest.mock import MagicMock

from example_audit import AuditLogger


@pytest.fixture
def audit():
    return AuditLogger(db=MagicMock())


class TestAuditLogger:
    def test_log_basic_event(self, audit):
        """Basic audit event is recorded."""
        audit.log(actor_id=1, action="login", resource_type="session")
        events = audit.query()
        assert len(events) == 1
        assert events[0]["action"] == "login"
        assert events[0]["actor_id"] == 1

    def test_log_with_details(self, audit):
        """Details dict is JSON-serialized."""
        audit.log(
            actor_id=2, action="update_job", resource_type="job", resource_id=42,
            details={"field": "status", "old": "Lead", "new": "In Progress"},
        )
        events = audit.query()
        assert len(events) == 1
        assert "Lead" in events[0]["changes_summary"]

    def test_log_system_event(self, audit):
        """System events have actor_id=None."""
        audit.log(actor_id=None, action="cron_cleanup", resource_type="system")
        events = audit.query()
        assert events[0]["actor_id"] is None

    def test_query_by_resource_type(self, audit):
        """Can filter by resource_type."""
        audit.log(1, "create_job", "job", 1)
        audit.log(1, "create_invoice", "invoice", 1)
        audit.log(1, "update_job", "job", 2)

        jobs = audit.query(resource_type="job")
        invoices = audit.query(resource_type="invoice")

        assert len(jobs) == 2
        assert len(invoices) == 1
        assert all(e["resource_type"] == "job" for e in jobs)

    def test_query_by_action(self, audit):
        """Can filter by action."""
        audit.log(1, "login", "session")
        audit.log(1, "logout", "session")
        audit.log(1, "login", "session")

        logins = audit.query(action="login")
        assert len(logins) == 2

    def test_query_limit(self, audit):
        """Limit caps results."""
        for i in range(10):
            audit.log(1, f"action_{i}", "test", i)

        results = audit.query(limit=3)
        assert len(results) == 3

    def test_query_reverse_chronological(self, audit):
        """Most recent events come first."""
        audit.log(1, "first", "test")
        audit.log(1, "second", "test")
        audit.log(1, "third", "test")

        results = audit.query()
        assert results[0]["action"] == "third"
        assert results[2]["action"] == "first"

    def test_log_transition(self, audit):
        """Field transition helper works."""
        audit.log_transition(1, "job", 42, "status", "Lead", "Active")
        events = audit.query()
        assert len(events) == 1
        assert events[0]["action"] == "update_job"
        assert "Lead" in events[0]["changes_summary"]
        assert "Active" in events[0]["changes_summary"]

    def test_log_never_raises(self, audit):
        """Even on 'failure', log() never crashes — best-effort pattern."""
        # The in-memory version never fails, but the contract guarantees
        # that exceptions are caught and logged, not propagated.
        try:
            audit.log(1, "test", "test")
        except Exception:
            pytest.fail("audit.log() should never raise")
