class AppError(Exception):
    """ Base controled exception"""
    status_code = 500
    
    code = 'internal_error'
    
    def __init__(
        self,
        message: str,
        *,
        details: dict | None = None):
        super(message)
        self.message = message
        self.details = details