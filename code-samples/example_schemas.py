"""Sanitized example — Pydantic Schema Contracts.

Shows the inter-domain contract pattern: domains communicate through
Pydantic schemas, never through SQLAlchemy ORM models directly.
This prevents cross-domain ORM leakage — a Level 400 architectural rule.
"""

from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════
#  Contact Domain — ContactRead is the public contract
# ═══════════════════════════════════════════════════════════════

@dataclass
class Contact:
    """Stub of the SQLAlchemy model — NOT exposed outside domains/contacts."""
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    tenant_id: int = 1


class ContactRead(BaseModel):
    """The read schema — what other domains are allowed to see."""
    id: int
    name: str
    email: str
    phone: Optional[str] = None

    model_config = {"from_attributes": True}  # Pydantic v2 — enables ORM mapping


# ═══════════════════════════════════════════════════════════════
#  Job Domain — references ContactRead, never Contact model
# ═══════════════════════════════════════════════════════════════

class JobCreate(BaseModel):
    """Contract for creating a job. Validates at the boundary."""
    contact_id: int = Field(..., gt=0, description="Must be a valid contact ID")
    job_type: str = Field(default="Standard", min_length=2, max_length=100)
    status: str = Field(default="Lead", min_length=2, max_length=50)
    description: Optional[str] = None


class JobRead(BaseModel):
    """Contract for reading a job — exposes only what callers need."""
    id: int
    job_type: str
    status: str
    description: Optional[str] = None
    contact: Optional[ContactRead] = None  # ← schema, NOT ORM model
    created_at: datetime = Field(default_factory=datetime.now)

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════
#  Usage example — converting between model and schema
# ═══════════════════════════════════════════════════════════════

def model_to_read_schema(contact: Contact) -> ContactRead:
    """Convert ORM model → Pydantic schema at domain boundary."""
    return ContactRead.model_validate(contact)


def validate_job_create(data: dict) -> JobCreate:
    """Validate incoming job data at the API boundary."""
    return JobCreate.model_validate(data)
