"""Sanitized example — Audit Logging.

Shows the immutable audit trail pattern for SOC 2 compliance (CC7.1).
Audit logs are best-effort — they never crash the application on failure.
"""

import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class AuditLogger:
    """Lightweight audit trail writer.

    Every write is:
    - Immutable (append-only, no UPDATE/DELETE on audit_log)
    - Best-effort (failure never crashes the app)
    - Structured (JSON changes_summary for machine readability)
    """

    def __init__(self, db):
        self._db = db
        self._storage: list[dict] = []  # in-memory for example

    def log(
        self,
        actor_id: Optional[int],
        action: str,
        resource_type: str,
        resource_id: Optional[int] = None,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """Write a single audit event.

        Args:
            actor_id: The user performing the action (None = system event)
            action: e.g. 'login', 'create_job', 'update_invoice'
            resource_type: e.g. 'job', 'invoice', 'user', 'session'
            resource_id: The affected entity's ID
            details: Free-form context (old/new values, field changes)
            ip_address: Client IP for forensic traceability
        """
        event = {
            "event_id": str(uuid.uuid4()),
            "actor_id": actor_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "changes_summary": json.dumps(details or {}),
            "ip_address": ip_address,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            # In production: db.execute(text("INSERT INTO audit_log ..."), event)
            self._storage.append(event)
        except Exception:
            # NEVER let audit logging crash the application
            logger.error("Failed to write audit log", exc_info=True)

    def query(
        self,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        action: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """Query audit events with optional filters.

        Returns events in reverse chronological order.
        """
        results = self._storage[:]

        if resource_type:
            results = [e for e in results if e["resource_type"] == resource_type]
        if resource_id is not None:
            results = [e for e in results if e["resource_id"] == resource_id]
        if action:
            results = [e for e in results if e["action"] == action]

        # Reverse chronological
        results.sort(key=lambda e: e["timestamp"], reverse=True)
        return results[:limit]

    def log_transition(
        self,
        actor_id: int,
        resource_type: str,
        resource_id: int,
        field: str,
        old_value,
        new_value,
    ) -> None:
        """Convenience — logs a field-level state transition."""
        self.log(
            actor_id=actor_id,
            action=f"update_{resource_type}",
            resource_type=resource_type,
            resource_id=resource_id,
            details={
                "field": field,
                "old": str(old_value),
                "new": str(new_value),
            },
        )
