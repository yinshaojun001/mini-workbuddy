from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, error: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content={
                "error": {
                    "code": error.code,
                    "message": error.message,
                    "details": error.details,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
        public_birth = request.url.path.startswith("/api/public/apps/") and request.url.path.endswith("/sessions")
        code = "INVALID_BIRTH_INPUT" if public_birth else "VALIDATION_ERROR"
        message = "出生信息有误" if public_birth else "请求参数有误"
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": code,
                    "message": message,
                    "details": {"fields": jsonable_encoder(error.errors())},
                }
            },
        )
