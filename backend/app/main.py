"""Wire HTTP routes, startup and shutdown, and optional frontend serving."""

import os
from contextlib import asynccontextmanager
from http import HTTPStatus
from pathlib import Path

from dotenv import dotenv_values
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.ai_work import AIWork, ProviderBusy
from app.api import router
from app.deps import open_database
from app.frontend import serve_frontend

BACKEND_DIR = Path(__file__).resolve().parents[1]
DEV_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")
PROVIDER_ENV_PREFIXES = ("SCENTFOLIO_LLM_", "ANTHROPIC_", "OPENAI_")


def _load_provider_environment() -> None:
    disabled = os.getenv("PYTHON_DOTENV_DISABLED", "").lower()
    if disabled in {"1", "true", "t", "yes", "y"}:
        return
    # Keep the existing priority of exported credentials and keep server settings
    # independent of the provider's .env file.
    for name, value in dotenv_values(BACKEND_DIR / ".env").items():
        if value is not None and name.startswith(PROVIDER_ENV_PREFIXES):
            os.environ.setdefault(name, value)


def create_app(database_url: str | None = None) -> FastAPI:
    """Build a FastAPI app that opens its database during startup.

    An explicit database URL overrides the server environment.
    """
    db_url = database_url or os.environ.get(
        "SCENTFOLIO_DB_URL", "sqlite:///scentfolio.db"
    )

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        engine, sessions = open_database(db_url)
        try:
            _load_provider_environment()
            application.state.session_factory = sessions
            yield
        finally:
            engine.dispose()

    app = FastAPI(title="Scentfolio", lifespan=lifespan)
    app.state.ai_work = AIWork(
        max_concurrent=int(os.getenv("SCENTFOLIO_AI_CONCURRENCY", "4"))
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=DEV_ORIGINS,
        allow_methods=("GET", "POST", "PATCH", "DELETE", "HEAD", "OPTIONS"),
        allow_headers=("Content-Type",),
        expose_headers=("X-Total-Count", "Retry-After"),
    )

    @app.middleware("http")
    async def check_write_origin(request: Request, call_next):
        origin = request.headers.get("origin")
        if request.method in {"POST", "PATCH", "PUT", "DELETE"} and origin is not None:
            host_origin = str(request.base_url).rstrip("/")
            if origin != host_origin and origin not in DEV_ORIGINS:
                return JSONResponse(
                    {"detail": "This origin cannot make changes to the collection."},
                    status_code=HTTPStatus.FORBIDDEN,
                )
        return await call_next(request)

    @app.exception_handler(ProviderBusy)
    async def provider_busy(_request: Request, exc: ProviderBusy):
        return JSONResponse(
            {"detail": str(exc)},
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            headers={"Retry-After": "2"},
        )

    app.include_router(router)
    if os.getenv("SCENTFOLIO_SERVE_UI") == "1":
        serve_frontend(app, BACKEND_DIR.parent / "frontend" / "dist")
    return app


app = create_app()
