class AppException(Exception):
    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppException):
    status_code = 404
    code = "not_found"


class ForbiddenError(AppException):
    status_code = 403
    code = "forbidden"


class UnauthorizedError(AppException):
    status_code = 401
    code = "unauthorized"


class ConflictError(AppException):
    status_code = 409
    code = "conflict"


class ValidationError(AppException):
    status_code = 422
    code = "validation_error"


class GoneError(AppException):
    status_code = 410
    code = "gone"
