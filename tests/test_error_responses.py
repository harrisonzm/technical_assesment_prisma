import json

from app.schemas.errors import create_error_response


def test_create_error_response_uses_error_schema():
    response = create_error_response(
        status_code=404,
        code="resource_not_found",
        message="Resource was not found",
        details={"resource_id": 42},
        request_id="request-123",
    )

    assert response.status_code == 404
    assert json.loads(response.body) == {
        "error": {
            "code": "resource_not_found",
            "message": "Resource was not found",
            "details": {"resource_id": 42},
            "request_id": "request-123",
        }
    }
