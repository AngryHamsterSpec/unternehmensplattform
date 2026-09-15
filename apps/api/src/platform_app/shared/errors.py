"""Fehlerantworten enthalten keine Interna oder ungeprüfte Eingabekopien."""

from fastapi import HTTPException


class ApiError(HTTPException):
    def __init__(self, status: int, detail: str, code: str = "request_error") -> None:
        super().__init__(status_code=status, detail=detail)
        self.code = code
