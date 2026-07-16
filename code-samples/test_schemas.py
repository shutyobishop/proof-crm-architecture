"""Tests for the schema contract examples."""

import pytest
from datetime import datetime

from example_schemas import (
    Contact,
    ContactRead,
    JobCreate,
    JobRead,
    model_to_read_schema,
    validate_job_create,
)


class TestContactRead:
    def test_from_model(self):
        """ContactRead can be constructed from a Contact model."""
        contact = Contact(id=1, name="Alice", email="alice@example.com")
        schema = model_to_read_schema(contact)
        assert schema.id == 1
        assert schema.name == "Alice"
        assert schema.email == "alice@example.com"

    def test_nullable_phone(self):
        """Phone is optional — None is valid."""
        schema = ContactRead(id=1, name="Bob", email="bob@example.com", phone=None)
        assert schema.phone is None

    def test_phone_present(self):
        """Phone is preserved when present."""
        schema = ContactRead(id=1, name="Bob", email="bob@example.com", phone="555-0100")
        assert schema.phone == "555-0100"


class TestJobCreate:
    def test_valid_job(self):
        """Minimal valid job creation."""
        job = JobCreate(contact_id=1)
        assert job.contact_id == 1
        assert job.job_type == "Standard"
        assert job.status == "Lead"

    def test_custom_type_and_status(self):
        """Custom job_type and status are accepted."""
        job = JobCreate(contact_id=2, job_type="Emergency", status="In Progress")
        assert job.job_type == "Emergency"
        assert job.status == "In Progress"

    def test_missing_contact_id(self):
        """contact_id is required."""
        with pytest.raises(ValueError):
            JobCreate()  # type: ignore[call-arg]

    def test_zero_contact_id(self):
        """contact_id must be > 0."""
        with pytest.raises(ValueError):
            JobCreate(contact_id=0)

    def test_negative_contact_id(self):
        """contact_id must be positive."""
        with pytest.raises(ValueError):
            JobCreate(contact_id=-1)

    def test_validate_from_dict(self):
        """validate_job_create accepts raw dicts."""
        job = validate_job_create({"contact_id": 5, "job_type": "Custom"})
        assert job.contact_id == 5
        assert job.job_type == "Custom"


class TestJobRead:
    def test_without_contact(self):
        """JobRead works without a contact (nullable)."""
        job = JobRead(
            id=1, job_type="Standard", status="Lead", contact=None,
            created_at=datetime(2026, 7, 15),
        )
        assert job.id == 1
        assert job.contact is None

    def test_with_contact_schema(self):
        """JobRead references ContactRead, never Contact model."""
        contact = ContactRead(id=10, name="Carol", email="carol@example.com")
        job = JobRead(
            id=2, job_type="Standard", status="Active",
            contact=contact, created_at=datetime(2026, 7, 15),
        )
        assert job.contact is not None
        assert job.contact.id == 10
        assert job.contact.name == "Carol"
