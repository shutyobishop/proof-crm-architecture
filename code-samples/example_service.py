"""Sanitized example — Service Layer.
Shows the orchestration pattern: multiple repos, business rules, no HTTP."""

from sqlalchemy.orm import Session
from example_repository import EntityRepository, ActivityRepository


class EntityService:
    """
    Service layer owns all business logic.
    - Composes multiple repositories
    - Enforces business rules
    - Never sees HTTP requests or responses
    - Every tenant-scoped function has *, tenant_id: int = 1
    """

    def __init__(self, entity_repo: EntityRepository, activity_repo: ActivityRepository | None = None):
        self._repo = entity_repo
        self._activity_repo = activity_repo or ActivityRepository()

    def get_detail(
        self,
        db: Session,
        entity_id: int,
        user_id: int | None = None,
        *, tenant_id: int = 1,
    ) -> dict:
        """
        Orchestrates data from multiple repositories.
        
        Returns a dict — never touches HTTP. Router decides
        whether to render HTML or return JSON.
        """
        entity = self._repo.get_by_id(db, entity_id, tenant_id=tenant_id)
        if not entity:
            return {"entity": None}

        # Compose from multiple data sources
        activities = self._activity_repo.get_for_entity(db, entity_id, tenant_id=tenant_id)
        related = self._repo.get_related(db, entity_id, tenant_id=tenant_id)

        return {
            "entity": entity,
            "activities": activities,
            "related_count": len(related),
            "can_edit": user_id is not None,
        }

    def soft_delete(
        self,
        db: Session,
        entity_id: int,
        deleted_by: str,
        *, tenant_id: int = 1,
    ) -> bool:
        """Business rule: soft-delete, don't hard-delete."""
        entity = self._repo.get_by_id(db, entity_id, tenant_id=tenant_id)
        if not entity:
            return False
        self._repo.soft_delete(db, entity_id, deleted_by, tenant_id=tenant_id)
        self._activity_repo.log_activity(
            db, entity_id, "deleted", f"Deleted by {deleted_by}", tenant_id=tenant_id,
        )
        return True
