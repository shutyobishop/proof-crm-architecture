# Code Samples

Sanitized architectural patterns from Prism CRM. These show the *how* without exposing any business logic.

## Files

| File | Pattern |
|------|---------|
| `example_router.py` | Thin router — parse HTTP, validate, delegate |
| `example_service.py` | Service layer — orchestrates repos, owns business rules |
| `example_repository.py` | Repository — pure data access, tenant-scoped |
| `example_schemas.py` | Pydantic domain contracts — zero ORM leakage |
| `example_audit.py` | Immutable audit trail — SOC 2 best-effort logging |
| `example_retry.py` | Exponential backoff retry — transient error resilience |

## Tests

```bash
pip install fastapi sqlalchemy pydantic pytest
python3 -m pytest code-samples/ -v
```

All samples are self-contained and pass with zero external dependencies beyond the three listed above.
