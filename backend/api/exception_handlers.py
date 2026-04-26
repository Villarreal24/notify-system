import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from services.notifications import CategoryNotFoundError

logger = logging.getLogger(__name__)


def _body(*, code: str, detail: str | list[dict[str, Any]] | Any) -> dict[str, Any]:
    return {"code": code, "detail": detail}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(CategoryNotFoundError)
    async def category_not_found(
        _request: Request, exc: CategoryNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=_body(code="CATEGORY_NOT_FOUND", detail=str(exc)),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=_body(code="VALIDATION_ERROR", detail=exc.errors()),
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error(
        _request: Request, exc: SQLAlchemyError
    ) -> JSONResponse:
        logger.exception("Database error: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_body(
                code="DATABASE_ERROR", detail="A database error occurred. Please try again later."
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_body(
                code="HTTP_ERROR" if exc.status_code >= 500 else "CLIENT_ERROR",
                detail=exc.detail,
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_body(
                code="INTERNAL_ERROR",
                detail="An unexpected error occurred. Please try again later.",
            ),
        )
