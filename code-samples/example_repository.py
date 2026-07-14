"""Sanitized example — Repository Layer.
Shows the data access pattern: pure SQL/ORM queries, no business logic."""

from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session


@dataclass
class Entity:
    """Minimal entity stub — in production this is a SQLAlchemy model."""
    id: int
    name: str
    status: str
    tenant_id: int = 1
    deleted_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Activity:
    """Activity log entry."""
    id: int
    entity_id: int
    activity_type: str
    content: str
    tenant_id: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EntityRepository:
    """
    Repository = the ONLY layer that touches the database.
    - Every query is tenant-scoped
    - Returns domain entities (or dicts), never ORM objects to callers
    - No business logic — just fetch, save, delete
    """

    def __init__(self):
        self._storage: dict[int, Entity] = {}
        self._next_id = 1

    def get_by_id(self, db: Session, entity_id: int, *, tenant_id: int = 1) -> Entity | None:
        """Fetch by ID with tenant isolation — the universal pattern."""
        entity = self._storage.get(entity_id)
        if entity and entity.tenant_id == tenant_id and entity.deleted_at is None:
            return entity
        return None

    def list_by_tenant(self, db: Session, *, tenant_id: int = 1) -> list[Entity]:
        """List all non-deleted entities for a tenant."""
        return [
            e for e in self._storage.values()
            if e.tenant_id == tenant_id and e.deleted_at is None
        ]

    def count_by_status(self, db: Session, *, tenant_id: int = 1) -> dict[str, int]:
        """Count entities grouped by status — pure aggregation."""
        counts: dict[str, int] = {}
        for e in self._storage.values():
            if e.tenant_id == tenant_id and e.deleted_at is None:
                counts[e.status] = counts.get(e.status, 0) + 1
        return counts

    def get_related(self, db: Session, entity_id: int, *, tenant_id: int = 1) -> list:
        """Get related entities — minimal stub."""
        return []

    def soft_delete(self, db: Session, entity_id: int, deleted_by: str, *, tenant_id: int = 1) -> bool:
        """Soft-delete: sets deleted_at, doesn't remove the row."""
        entity = self._storage.get(entity_id)
        if entity and entity.tenant_id == tenant_id:
            entity.deleted_at = datetime.now(timezone.utc)
            return True
        return False

    def create(self, db: Session, name: str, status: str = "active", *, tenant_id: int = 1) -> Entity:
        """Create a new entity."""
        entity = Entity(id=self._next_id, name=name, status=status, tenant_id=tenant_id)
        self._storage[entity.id] = entity
        self._next_id += 1
        return entity


class ActivityRepository:
    """Activity log — write-only append log for audit trail."""

    def __init__(self):
        self._storage: dict[int, Activity] = {}
        self._next_id = 1

    def log_activity(
        self, db: Session, entity_id: int,
        activity_type: str, content: str, *, tenant_id: int = 1,
    ) -> Activity:
        activity = Activity(
            id=self._next_id, entity_id=entity_id,
            activity_type=activity_type, content=content, tenant_id=tenant_id,
        )
        self._storage[activity.id] = activity
        self._next_id += 1
        return activity

    def get_for_entity(self, db: Session, entity_id: int, *, tenant_id: int = 1) -> list[Activity]:
        return [
            a for a in self._storage.values()
            if a.entity_id == entity_id and a.tenant_id == tenant_id
        ]
