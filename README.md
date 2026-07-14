# Proof CRM — Architecture & Design Patterns

> **A production CRM built with FastAPI, Domain-Driven Design, and Supabase.**  
> This repo shows the architectural decisions, not the business logic.

![Architecture](architecture/overview.png)

---

## The Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Runtime** | Python 3.11+ on Linux | Battle-tested, async capable |
| **API Framework** | FastAPI + Starlette | Async-native, auto OpenAPI docs |
| **ORM** | SQLAlchemy 2.0 (async + sync) | Mature, migration-friendly |
| **Database** | PostgreSQL on Supabase | SOC 2, auto-scaling, 100% managed |
| **Auth** | bcrypt sessions (migrating to Supabase Auth) | Zero-dependency for now |
| **Storage** | Supabase Storage (S3-compatible) | Built-in CDN, bucket policies |
| **Monitoring** | pg_stat_statements + structured JSON logs | Query-level visibility |
| **Backup** | pg_dump via cron | 7-day rolling retention |

---

## Architecture: Modular Monolith with DDD

```
┌──────────────────────────────────────────────────────────┐
│                     Presentation Layer                    │
│  FastAPI Routers  ·  Jinja2 Templates  ·  Static Assets  │
└────────────────────────┬─────────────────────────────────┘
                         │ HTTP / JSON
┌────────────────────────▼─────────────────────────────────┐
│                     Application Layer                     │
│  Auth  ·  Permissions  ·  Request Validation  ·  Caching  │
└────────────────────────┬─────────────────────────────────┘
                         │ Service Calls
┌────────────────────────▼─────────────────────────────────┐
│                     Domain Layer                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ Auth     │ │ Jobs     │ │ Contacts │ │ Documents│   │
│  │ Domain   │ │ Domain   │ │ Domain   │ │ Domain   │   │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘   │
│       │            │            │            │          │
│  ┌────▼─────┐ ┌────▼─────┐ ┌────▼─────┐ ┌────▼─────┐   │
│  │Services   │ │Services   │ │Services   │ │Services   │   │
│  │ (Logic)   │ │ (Logic)   │ │ (Logic)   │ │ (Logic)   │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘   │
│       │            │            │            │          │
│  ┌────▼─────┐ ┌────▼─────┐ ┌────▼─────┐ ┌────▼─────┐   │
│  │Repos     │ │Repos     │ │Repos     │ │Repos     │     │
│  │(Data)    │ │(Data)    │ │(Data)    │ │(Data)    │    │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
└────────────────────────┬─────────────────────────────────┘
                         │ SQL / REST
┌────────────────────────▼─────────────────────────────────┐
│                  Infrastructure Layer                     │
│  PostgreSQL (Supabase)  ·  Redis  ·  SMTP  ·  SMS  ·  S3 │
└──────────────────────────────────────────────────────────┘
```

### Key Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| **Modular Monolith, not Microservices** | Single team, single deploy, zero network overhead. Can split later if needed. |
| **Headless Service Layer** | All business logic lives in `domains/*/service.py`. Routers are thin — they parse HTTP, validate, delegate. |
| **Repository Pattern** | `domains/*/repository.py` owns all SQLAlchemy queries. Services never touch the ORM directly. |
| **Multi-Tenant by Design** | Every table has `tenant_id`. Every service function has a `tenant_id` param. RLS enforces it at the DB level. |
| **Isolated Repositories** | Repositories never import other domains' repos. Cross-domain logic lives in services. |
| **Supabase as Primary, Not Adjunct** | Not a "also on Supabase" — the primary engine IS PostgreSQL/Supabase. SQLite is only for local dev. |

---

## Security Architecture

```
┌─────────────────────────────────────────┐
│          Rate Limiter (5/min/IP)        │
│           In-memory dict                │
├─────────────────────────────────────────┤
│           JWT Session Token             │
│            bcrypt password hash          │
├─────────────────────────────────────────┤
│     RLS Tenant Isolation Policy         │
│  CREATE POLICY ... USING (tenant_id =   │
│    (auth.jwt()->>'tenant_id')::int)     │
├─────────────────────────────────────────┤
│          Row-Level Security             │
│    ENABLE ROW LEVEL SECURITY on 109/109 │
├─────────────────────────────────────────┤
│          FK Indexes (216 total)         │
│  183 CONCURRENTLY-created for perf      │
├─────────────────────────────────────────┤
│        pg_stat_statements enabled       │
│        Query-level performance monitoring │
└─────────────────────────────────────────┘
```

### RLS Policy (all 109 tables)
```sql
CREATE POLICY tenant_isolation_policy ON [table]
    FOR ALL
    USING (tenant_id = (auth.jwt()->>'tenant_id')::int);
```

### Login Rate Limiter
```python
# Pure stdlib — no external deps
_login_attempts: dict[str, int] = {}
WINDOW = 60  # seconds
MAX_ATTEMPTS = 5

def _rate_limited(ip: str) -> bool:
    key = f"{ip}:{int(time.time() / WINDOW)}"
    return _login_attempts.get(key, 0) >= MAX_ATTEMPTS

def _record_attempt(ip: str) -> None:
    key = f"{ip}:{int(time.time() / WINDOW)}"
    _login_attempts[key] = _login_attempts.get(key, 0) + 1
```

---

## DDD Patterns: Sanitized Code Samples

### 1. Router Layer (Thin — HTTP only)
```python
# domains/jobs/router.py
@router.get("/jobs/{job_id:int}", response_class=HTMLResponse)
async def job_detail(
    job_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Thin router — only handles HTTP, delegates to service."""
    data = jobs_service.get_job_detail(db, job_id, user_id=user.id)
    if not data["job"]:
        raise HTTPException(status_code=404, detail="Job not found")
    return render("jobs/detail.html", **data)
```

### 2. Service Layer (All business logic lives here)
```python
# domains/jobs/service.py
def get_job_detail(
    db: Session,
    job_id: int,
    user_id: int,
    *, tenant_id: int = 1,
) -> dict:
    """Orchestrates data from multiple repositories."""
    job = _repo.get_by_id(db, job_id, tenant_id=tenant_id)
    if not job:
        return {"job": None}
    activities = activity_repo.get_for_job(db, job_id, tenant_id=tenant_id)
    documents = document_repo.get_for_job(db, job_id, tenant_id=tenant_id)
    return {
        "job": job,
        "activities": activities,
        "documents": documents,
        "can_edit": _user_can_edit_job(user_id, job),
    }
```

### 3. Repository Layer (Data access — no business logic)
```python
# domains/jobs/repository.py
def get_by_id(db: Session, job_id: int, *, tenant_id: int = 1) -> Job | None:
    """Single responsibility: fetch data. No business rules."""
    return (
        db.query(Job)
        .filter(Job.id == job_id, Job.tenant_id == tenant_id, Job.deleted_at.is_(None))
        .first()
    )

def count_by_status(db: Session, *, tenant_id: int = 1) -> dict[str, int]:
    """Pipeline counts grouped by status — pure aggregation query."""
    rows = (
        db.query(Job.status, func.count(Job.id))
        .filter(Job.tenant_id == tenant_id, Job.deleted_at.is_(None))
        .group_by(Job.status)
        .all()
    )
    return {row[0]: row[1] for row in rows}
```

### 4. Multi-tenant Parameter Convention
```python
# Every service function that accesses tenant-scoped data uses this:
def some_service_func(
    db: Session,
    entity_id: int,
    *, tenant_id: int = 1,  # keyword-only, never positional
) -> Entity:
    return repo.query(db, entity_id, tenant_id=tenant_id)
```

---

## Test Suite Results

```
collected 164 items

tests/unit/domains/jobs/test_service.py ..............    [  8%]
tests/unit/domains/auth/test_router.py ..............     [ 16%]
tests/unit/domains/contacts/ ...                          [ 25%]
tests/unit/domains/documents/ ...                         [ 33%]
...
tests/e2e/test_dichotomy.py ....                          [ 85%]
tests/e2e/test_field_alive.py ....                        [ 93%]
...

125 passed, 39 skipped, 1 xfailed in 9.67s
```

- **76% pass rate** (125/164 active tests)
- **39 intentionally skipped** — E2E tests requiring browser automation
- **0 failures** — entire active suite is green
- **Fast execution** — suite completes in under 10 seconds

---

## Database Schema Stats

| Metric | Value |
|--------|-------|
| Tables | 109 |
| RLS Policies | 109 (1 per table, tenant-scoped) |
| FK Indexes | 216 (183 auto-generated) |
| Active Rows | ~11,000+ |
| ORM Models | 130+ (SQLAlchemy declarative) |
| Most Recent ANALYZE | 2026-07-14 |

---

## Key Operational Metrics

```
System:     Linux 6.8, 2 vCPU, 2GB RAM
CRM Port:   8001, Uvicorn with 2 workers
DB:         PostgreSQL 17.6 on Supabase (managed)
Backup:     Daily pg_dump at 03:00 UTC, 7-day rolling
Keepalive:  DB ping + ANALYZE every 6 hours
Cron Jobs:  36 active (down from 52)
```

---

## Why These Patterns?

| Problem | Solution |
|---------|----------|
| "Routers got fat with business logic" | Thin routers, service layer owns decisions |
| "One big models.py" | Extracted into `domains/*/models.py` |
| "ORM queries everywhere" | Repository pattern — only repos touch SQLAlchemy |
| "Tenant isolation was manual" | RLS at DB level + param at service level |
| "No query visibility" | pg_stat_statements + structured JSON logging |
| "No backup" | Automated pg_dump with retention |
| "Route shadowing" | `:int` constraints on parameterized routes |
| "Hard to test" | Unit tests with mocked repos, full test isolation |

---

## Running the Sanitized Examples

```bash
# Clone this repo
git clone git@github.com:shutyobishop/proof-crm-architecture.git
cd proof-crm-architecture

# Install deps
python3 -m venv venv
source venv/bin/activate
pip install fastapi sqlalchemy pydantic

# Run the example tests
python3 -m pytest code-samples/
```

> ℹ️ This repo contains **architectural patterns only** — no business logic, no secrets, no proprietary code.  
> The actual CRM is private at `github.com/shutyobishop/Proof-CRM`.

---

## License

MIT — see [LICENSE](LICENSE).

Built by [shutyobishop](https://github.com/shutyobishop).
