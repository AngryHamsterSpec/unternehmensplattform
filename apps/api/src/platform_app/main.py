"""ASGI-Einstieg mit sicheren Fehlern, Grenzen und nachvollziehbaren Requests."""

import json
import logging
import re
import time
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from threading import Lock
from typing import Any
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import RequestResponseEndpoint

from platform_app.api import router as business_router
from platform_app.data.intelligence_router import router as intelligence_router
from platform_app.data.router import router as data_router
from platform_app.data.uploads import router as upload_router
from platform_app.explanations.router import router as explanation_router
from platform_app.identity.router import metadata
from platform_app.identity.router import router as identity_router
from platform_app.identity.security import cookie_name, valid_token
from platform_app.shared.config import get_settings
from platform_app.shared.context import request_id
from platform_app.shared.db import engine_for

logger = logging.getLogger("platform")
logging.basicConfig(level=logging.INFO, format="%(message)s")


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    get_settings()
    yield


app = FastAPI(
    title="Unternehmensplattform",
    version="0.1.0",
    lifespan=lifespan,
    description="Synthetischer Demonstrator für nachvollziehbare Architekturentscheidungen.",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)
app.include_router(identity_router)
app.include_router(business_router)
app.include_router(data_router)
app.include_router(intelligence_router)
app.include_router(upload_router)
app.include_router(explanation_router)
_requests: dict[str, deque[float]] = defaultdict(deque)
_lock = Lock()


def problem(
    request: Request, status: int, detail: str, fields: list[dict[str, str]] | None = None
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": "about:blank",
        "title": "Anfrage konnte nicht abgeschlossen werden",
        "status": status,
        "detail": detail,
        "instance": request.url.path,
        "request_id": str(getattr(request.state, "request_id", "")),
    }
    if fields:
        body["field_errors"] = fields
    return JSONResponse(body, status_code=status, media_type="application/problem+json")


async def bounded_request(request: Request, call_next: RequestResponseEndpoint) -> Response:
    # Lokales Gesamtlimit je direktem Peer; der Proxy begrenzt Loginversuche zusätzlich.
    # Forwarded-Header ungeprüfter Clients werden nicht als vertrauenswürdige IP übernommen.
    if not request.url.path.startswith("/api/v1/health/"):
        peer = request.client.host if request.client else "unknown"
        with _lock:
            now = time.monotonic()
            if len(_requests) >= 10000:
                for key in list(_requests):
                    if not _requests[key] or _requests[key][-1] < now - 60:
                        _requests.pop(key, None)
                if len(_requests) >= 10000 and peer not in _requests:
                    return problem(request, 429, "Zu viele gleichzeitige Verbindungen.")
            queue = _requests[peer]
            while queue and queue[0] < now - 60:
                queue.popleft()
            if len(queue) >= get_settings().request_limit_per_minute:
                return problem(request, 429, "Zu viele Anfragen. Bitte kurz warten.")
            queue.append(now)
    try:
        length = int(request.headers.get("content-length", "0"))
    except ValueError:
        return problem(request, 400, "Ungültige Anfragegröße.")
    if length < 0:
        return problem(request, 400, "Ungültige Anfragegröße.")
    chunk_upload = (
        request.method == "PUT"
        and re.fullmatch(r"/api/v1/data-uploads/[0-9a-fA-F-]{36}/chunks/[0-9]+", request.url.path)
        is not None
    )
    body_limit = 4194304 if chunk_upload else 262144
    if length > body_limit:
        return problem(request, 413, "Die Anfrage ist zu groß.")
    if request.method in {"POST", "PATCH", "PUT"}:
        parts = bytearray()
        async for chunk in request.stream():
            if len(parts) + len(chunk) > body_limit:
                return problem(request, 413, "Die Anfrage ist zu groß.")
            parts.extend(chunk)
        # Starlette BaseHTTPMiddleware reicht den gepufferten Body an die Route weiter.
        request._body = bytes(parts)
    public_paths = {
        "/api/v1/auth/login",
        "/api/v1/auth/callback",
        "/api/v1/health/live",
        "/api/v1/health/ready",
    }
    if request.url.path.startswith("/api/v1/") and request.url.path not in public_paths:
        if not valid_token(request.cookies.get(cookie_name(get_settings(), "session"))):
            return problem(request, 401, "Bitte anmelden.")
    return await call_next(request)


@app.middleware("http")
async def boundaries(request: Request, call_next: RequestResponseEndpoint) -> Response:
    request.state.request_id = uuid4()
    context_token = request_id.set(request.state.request_id)
    start = time.monotonic()
    try:
        try:
            response = await bounded_request(request, call_next)
        except (SQLAlchemyError, httpx.HTTPError):
            response = problem(
                request, 503, "Ein notwendiger Dienst ist vorübergehend nicht verfügbar."
            )
        except Exception as error:
            logger.error(
                json.dumps(
                    {
                        "event": "request_failed",
                        "error_type": type(error).__name__,
                        "request_id": str(request.state.request_id),
                    }
                )
            )
            response = problem(
                request,
                500,
                "Ein interner Fehler ist aufgetreten. Die Anfragekennung hilft bei der Prüfung.",
            )
        response.headers["X-Request-ID"] = str(request.state.request_id)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        if response.status_code == 429:
            response.headers["Retry-After"] = "60"
        logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": str(request.state.request_id),
                    "method": request.method,
                    "status": response.status_code,
                    "duration_ms": round((time.monotonic() - start) * 1000, 2),
                }
            )
        )
        return response
    finally:
        request_id.reset(context_token)


@app.exception_handler(HTTPException)
async def http_error(request: Request, error: HTTPException) -> JSONResponse:
    return problem(request, error.status_code, str(error.detail))


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
    return problem(
        request,
        422,
        "Bitte Eingaben und Einheiten prüfen.",
        [{"field": ".".join(str(v) for v in e["loc"]), "code": e["type"]} for e in error.errors()],
    )


@app.get("/api/v1/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/health/ready")
def ready() -> dict[str, str]:
    try:
        with engine_for().connect() as conn:
            conn.execute(text("SELECT 1"))
            revision = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            if revision != "0005":
                raise RuntimeError("schema")
        metadata()
        return {"status": "ready", "version": "0.1.0"}
    except (SQLAlchemyError, RuntimeError, httpx.HTTPError):
        raise HTTPException(
            503, "Datenbank, Schema oder Anmeldedienst ist noch nicht bereit."
        ) from None
