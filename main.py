import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import v1_router
from app.core.config import settings
from app.exceptions.app_exceptions import AppException
from app.exceptions.handlers import (
    app_exception_handler,
    generic_exception_handler,
    validation_exception_handler,
)
from app.middleware.logging import LoggingMiddleware
from app.middleware.request_id import RequestIDMiddleware

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


def create_app() -> FastAPI:
    application = FastAPI(
        title="Jira Backend API",
        description="Simplified Jira-like Issue Tracking System",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(LoggingMiddleware)
    application.add_middleware(RequestIDMiddleware)

    application.add_exception_handler(AppException, app_exception_handler)
    application.add_exception_handler(RequestValidationError, validation_exception_handler)
    application.add_exception_handler(Exception, generic_exception_handler)

    application.include_router(v1_router)

    @application.get("/health", response_model=dict, tags=["Health"])
    async def health_check() -> dict:
        return {"status": "ok"}

    return application


app = create_app()
