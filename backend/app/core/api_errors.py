from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def error_payload(code: str, message: str, *, detail: Any | None = None, fields: Any | None = None) -> dict[str, Any]:
    return {"code": code, "message": message, "detail": detail, "fields": fields}


def http_error_code(status_code: int, message: str) -> str:
    lowered = message.lower()
    if status_code == status.HTTP_401_UNAUTHORIZED:
        if "refresh" in lowered:
            return "AUTH_REFRESH_INVALID"
        if "expired" in lowered:
            return "AUTH_TOKEN_EXPIRED"
        if "credential" in lowered or "password" in lowered:
            return "AUTH_INVALID_CREDENTIALS"
        return "AUTH_UNAUTHORIZED"
    if status_code == status.HTTP_403_FORBIDDEN:
        return "AUTH_FORBIDDEN"
    if status_code == status.HTTP_404_NOT_FOUND:
        return "RESOURCE_NOT_FOUND"
    if status_code == status.HTTP_413_CONTENT_TOO_LARGE:
        return "FILE_TOO_LARGE"
    if status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE:
        return "FILE_UNSUPPORTED_TYPE"
    if status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        return "RATE_LIMITED"
    if status_code == status.HTTP_400_BAD_REQUEST:
        if "file too large" in lowered:
            return "FILE_TOO_LARGE"
        if "unsupported file" in lowered or "not supported" in lowered or "not yet supported" in lowered:
            return "FILE_UNSUPPORTED_TYPE"
        if "already registered" in lowered:
            return "AUTH_ACCOUNT_EXISTS"
        return "BAD_REQUEST"
    return "INTERNAL_ERROR" if status_code >= 500 else "BAD_REQUEST"


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    message = str(exc.detail) if exc.detail else "Request failed"
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(http_error_code(exc.status_code, message), message),
        headers=exc.headers,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_payload("VALIDATION_ERROR", "请求参数不正确", fields=exc.errors()),
    )


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=error_payload("BAD_REQUEST", str(exc)))
