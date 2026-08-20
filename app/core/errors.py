"""
Application error types and the consistent error envelope used
across the API:

    { "error": { "code": "...", "message": "..." } }

Raise `AppError` (or a subclass) from services/routes; the handler
registered in app.main converts it into this shape automatically.
"""

from fastapi import status


class AppError(Exception):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "BAD_REQUEST"

    def __init__(self, message: str, code: str | None = None, status_code: int | None = None):
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "UNAUTHORIZED"


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "FORBIDDEN"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "CONFLICT"


class ValidationAppError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "VALIDATION_ERROR"


class RateLimitError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "RATE_LIMITED"


class ProductUnavailableError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "PRODUCT_UNAVAILABLE"


class StoreInactiveError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "STORE_INACTIVE"


class InvalidStatusTransitionError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "INVALID_STATUS_TRANSITION"
