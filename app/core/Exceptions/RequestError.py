from .AppError import AppError


class ResourceNotFoundError(AppError):
    status_code = 404
    code = "resource_not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class DatabaseUnavailableError(AppError):
    status_code = 503
    code = "database_unavailable"


class BusinessRuleError(AppError):
    status_code = 422
    code = "business_rule_violation"


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"
