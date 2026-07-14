"""Tests for example code samples — showing the test pattern."""

from unittest.mock import MagicMock
import pytest

from example_repository import EntityRepository, ActivityRepository
from example_service import EntityService


@pytest.fixture
def repo():
    return EntityRepository()


@pytest.fixture
def activity_repo():
    return ActivityRepository()


@pytest.fixture
def service(repo, activity_repo):
    return EntityService(repo, activity_repo)


@pytest.fixture
def db():
    """In production, this would be a real SQLAlchemy session.
    Here we use a MagicMock since the in-memory storage doesn't need it."""
    return MagicMock()


class TestEntityService:
    def test_get_detail_found(self, service, repo, db):
        """Service returns entity data when it exists."""
        repo.create(db, "Test Entity")
        result = service.get_detail(db, 1)
        assert result["entity"] is not None
        assert result["entity"].name == "Test Entity"
        assert result["related_count"] == 0

    def test_get_detail_not_found(self, service, db):
        """Service returns empty dict when entity doesn't exist."""
        result = service.get_detail(db, 999)
        assert result["entity"] is None

    def test_get_detail_tenant_isolation(self, service, repo, db):
        """Entities from tenant 1 are invisible to tenant 2."""
        repo.create(db, "Entity T1", tenant_id=1)
        result_t1 = service.get_detail(db, 1, tenant_id=1)
        result_t2 = service.get_detail(db, 1, tenant_id=2)
        assert result_t1["entity"] is not None
        assert result_t2["entity"] is None

    def test_soft_delete(self, service, repo, db):
        """Soft delete marks as deleted but doesn't remove."""
        repo.create(db, "To Delete")
        result = service.soft_delete(db, 1, deleted_by="test_user")
        assert result is True
        # Verify it's no longer visible
        detail = service.get_detail(db, 1)
        assert detail["entity"] is None

    def test_soft_delete_nonexistent(self, service, db):
        """Soft delete returns False for non-existent entities."""
        result = service.soft_delete(db, 999, deleted_by="test_user")
        assert result is False

    def test_count_by_status(self, service, repo, db):
        """Status aggregation counts correctly."""
        repo.create(db, "Entity 1", status="active")
        repo.create(db, "Entity 2", status="active")
        repo.create(db, "Entity 3", status="completed")
        counts = repo.count_by_status(db)
        assert counts == {"active": 2, "completed": 1}


class TestEntityRepository:
    def test_create_and_find(self, repo, db):
        entity = repo.create(db, "New Entity")
        found = repo.get_by_id(db, entity.id)
        assert found is not None
        assert found.name == "New Entity"

    def test_tenant_isolation(self, repo, db):
        repo.create(db, "T1 Only", tenant_id=1)
        t1_list = repo.list_by_tenant(db, tenant_id=1)
        t2_list = repo.list_by_tenant(db, tenant_id=2)
        assert len(t1_list) == 1
        assert len(t2_list) == 0

    def test_soft_delete_hides_entity(self, repo, db):
        repo.create(db, "To Delete")
        repo.soft_delete(db, 1, "admin")
        found = repo.get_by_id(db, 1)
        assert found is None

    def test_list_excludes_deleted(self, repo, db):
        repo.create(db, "Active")
        repo.create(db, "To Delete")
        repo.soft_delete(db, 2, "admin")
        entities = repo.list_by_tenant(db)
        names = [e.name for e in entities]
        assert "Active" in names
        assert "To Delete" not in names


class TestActivityRepository:
    def test_log_activity(self, activity_repo, db):
        activity = activity_repo.log_activity(db, 1, "created", "Entity created")
        assert activity.id == 1
        assert activity.activity_type == "created"

    def test_get_for_entity(self, activity_repo, db):
        activity_repo.log_activity(db, 1, "created", "Entity 1 created")
        activity_repo.log_activity(db, 2, "created", "Entity 2 created")
        activities = activity_repo.get_for_entity(db, 1)
        assert len(activities) == 1
        assert activities[0].entity_id == 1
