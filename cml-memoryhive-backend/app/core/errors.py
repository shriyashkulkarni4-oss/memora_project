"""Stable JSON error responses for every API route."""

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

ERROR_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
}


def error_payload(
    status_code: int,
    message: str,
    details: dict[str, Any] | list[Any] | None = None,
) -> dict[str, Any]:
    return {
        "error": {
            "code": ERROR_CODES.get(status_code, "REQUEST_FAILED"),
            "message": message,
            "details": details,
        }
    }


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_error_handler(
        _request: Request, exception: HTTPException
    ) -> JSONResponse:
        detail = exception.detail
        message = detail if isinstance(detail, str) else "Request failed"
        details = None if isinstance(detail, str) else jsonable_encoder(detail)
        return JSONResponse(
            status_code=exception.status_code,
            content=error_payload(exception.status_code, message, details),
            headers=exception.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, exception: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_payload(
                422,
                "Request validation failed",
                jsonable_encoder(exception.errors()),
            ),
        )
