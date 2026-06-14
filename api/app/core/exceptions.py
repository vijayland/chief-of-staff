from fastapi import HTTPException, status


class NotFoundError(HTTPException):
    def __init__(self, resource: str = "Resource") -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=f"{resource} not found")


class UnauthorizedError(HTTPException):
    def __init__(self, detail: str = "Not authenticated") -> None:
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail,
                         headers={"WWW-Authenticate": "Bearer"})


class ForbiddenError(HTTPException):
    def __init__(self, detail: str = "Access denied") -> None:
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class ConflictError(HTTPException):
    def __init__(self, detail: str = "Resource already exists") -> None:
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class BadRequestError(HTTPException):
    def __init__(self, detail: str = "Bad request") -> None:
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class GoogleAuthError(BadRequestError):
    def __init__(self, detail: str = "Google authentication failed") -> None:
        super().__init__(detail=detail)


class IntegrationError(HTTPException):
    def __init__(self, service: str, detail: str) -> None:
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{service} integration error: {detail}"
        )
