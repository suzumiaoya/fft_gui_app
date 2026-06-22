class AppError(Exception):
    """Base application error."""


class ValidationError(AppError):
    """Raised when user input or data is invalid."""
