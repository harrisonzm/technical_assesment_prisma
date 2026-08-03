from .AppError import AppError
class ResourceNotFoundError(AppError):
    status_code = 400
    code = 'resource_not_found'

class ConflictError(AppError):
    status_code = 409
    code = 'conflict'

class DatabaseUnavailableError(AppError):
    status_code = 503
    code = 'database_unavailable'
    
class BussinesRuleError(AppError):
    code = 422
    code = 'bussines_rule_violation'

class UnauthorazedError(AppError):
    status_code = 401
    code = 'unauthorazed'

class forbiddenError(AppError):
    status_code = 403
    code = 'forbidden'
