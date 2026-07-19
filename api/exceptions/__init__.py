"""
Base exception and domain-specific exceptions for the application.
"""

from typing import Any


class AppException(Exception):
    """Base exception for all application errors."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class UserAlreadyExistsError(AppException):
    """Raised when attempting to create a user with an existing email."""

    def __init__(self, email: str):
        super().__init__(
            code="USER_ALREADY_EXISTS",
            message=f"Un usuario con el correo '{email}' ya existe",
            status_code=409,
        )


class UserNotFoundError(AppException):
    """Raised when a user is not found."""

    def __init__(self, identifier: str = ""):
        message = "Usuario no encontrado"
        if identifier:
            message = f"Usuario '{identifier}' no encontrado"
        super().__init__(
            code="USER_NOT_FOUND",
            message=message,
            status_code=404,
        )


class PermissionDeniedError(AppException):
    """Raised when a user lacks permission for an action."""

    def __init__(self, message: str = "No tienes permiso para realizar esta acción"):
        super().__init__(
            code="PERMISSION_DENIED",
            message=message,
            status_code=403,
        )


class InvalidRoleError(AppException):
    """Raised when an invalid role is specified."""

    def __init__(self, roles: list[str]):
        super().__init__(
            code="INVALID_ROLE",
            message=f"Roles desconocidos: {', '.join(roles)}",
            status_code=400,
        )


class AuthenticationError(AppException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Autenticación fallida"):
        super().__init__(
            code="AUTHENTICATION_FAILED",
            message=message,
            status_code=401,
        )


class ResourceNotFoundError(AppException):
    """Raised when a generic resource is not found."""

    def __init__(self, resource: str, identifier: str | int):
        super().__init__(
            code="RESOURCE_NOT_FOUND",
            message=f"{resource} con identificador '{identifier}' no encontrado",
            status_code=404,
        )


class ResourceAlreadyExistsError(AppException):
    """Raised when attempting to create a resource that already exists."""

    def __init__(self, resource: str, field: str, value: str):
        super().__init__(
            code="RESOURCE_ALREADY_EXISTS",
            message=f"Un {resource} con {field} '{value}' ya existe",
            status_code=409,
        )


class ValidationError(AppException):
    """Raised when business validation fails."""

    def __init__(self, message: str):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=400,
        )
