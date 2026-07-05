from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api import attempts, auth, chat, conversations, documents, files, health, knowledge, learning, mistakes, plans, rag, speech, twins, usage, users
from app.core.api_errors import http_exception_handler, validation_exception_handler, value_error_handler
from app.core.config import load_settings
from app.core.middleware import request_logging_middleware
from app.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="EchoLearn Backend", version="0.1.0", lifespan=lifespan)
    settings = load_settings()
    allow_origins = [origin.strip() for origin in settings.cors_allow_origins.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.middleware("http")(request_logging_middleware)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(attempts.router)
    app.include_router(chat.router)
    app.include_router(conversations.router)
    app.include_router(learning.router)
    app.include_router(mistakes.router)
    app.include_router(plans.router)
    app.include_router(twins.router)
    app.include_router(files.router)
    app.include_router(documents.router)
    app.include_router(knowledge.router)
    app.include_router(rag.router)
    app.include_router(speech.router)
    app.include_router(usage.router)

    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValueError, value_error_handler)

    return app


app = create_app()
