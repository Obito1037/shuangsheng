from __future__ import annotations

from fastapi import HTTPException, status


def deny_not_found(resource: object | None, message: str = "Resource not found") -> object:
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
    return resource

