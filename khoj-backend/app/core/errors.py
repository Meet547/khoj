from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status: int = 400,
        *,
        retryable: bool = False,
        retry_after: int | None = None,
    ):
        self.code, self.message, self.status = code, message, status
        self.retryable, self.retry_after = retryable, retry_after


def error_response(error: AppError) -> JSONResponse:
    headers = {"Retry-After": str(error.retry_after)} if error.retry_after is not None else {}
    return JSONResponse(
        status_code=error.status,
        content={
            "error": {"code": error.code, "message": error.message, "retryable": error.retryable}
        },
        headers=headers,
    )


def install_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error(request: Request, exc: AppError) -> JSONResponse:
        return error_response(exc)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Never echo the submitted phone, OTP, transcript or Pydantic input payload.
        return error_response(
            AppError("invalid_request", "Please check the information and try again.", 422)
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return error_response(
            AppError(
                "not_found" if exc.status_code == 404 else "request_failed",
                "This request could not be completed.",
                exc.status_code,
            )
        )
