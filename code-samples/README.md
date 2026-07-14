# Sanitized Code Samples

These files demonstrate the **architectural patterns** used in Proof CRM — not the business logic.

| Sample | Pattern Demonstrated |
|--------|---------------------|
| `example_router.py` | Thin router → service → repository flow |
| `example_service.py` | Service layer orchestrates multiple repos |
| `example_repository.py` | Repository pattern with tenant isolation |
| `test_example.py` | Unit test pattern with mocked repos |

All samples are self-contained and runnable with pytest.
