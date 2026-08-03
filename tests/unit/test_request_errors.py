import pytest

from app.core.Exceptions.RequestError import (
    BusinessRuleError,
    ConflictError,
    DatabaseUnavailableError,
    ForbiddenError,
    ResourceNotFoundError,
    UnauthorizedError,
)


@pytest.mark.parametrize(
    ("error_type", "expected_status", "expected_code"),
    [
        (ResourceNotFoundError, 404, "resource_not_found"),
        (ConflictError, 409, "conflict"),
        (BusinessRuleError, 422, "business_rule_violation"),
        (UnauthorizedError, 401, "unauthorized"),
        (ForbiddenError, 403, "forbidden"),
        (DatabaseUnavailableError, 503, "database_unavailable"),
    ],
)
def test_request_errors_use_consistent_http_semantics(
    error_type: type[Exception],
    expected_status: int,
    expected_code: str,
) -> None:
    error = error_type("test error")

    assert error.status_code == expected_status
    assert error.code == expected_code
