"""
OneHub API entrypoint.

Run locally with:
    uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.api.router import api_router
from app.core.config import settings
from app.core.errors import AppError
from app.db.prisma import check_db_connection, connect_db, disconnect_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await disconnect_db()


app = FastAPI(
    title="OneHub API",
    description=(
        "Backend for the OneHub customer and admin apps. "
        "Public catalog browsing, authenticated customer ordering, "
        "and store-scoped admin management, all on one API."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

if settings.cors_origins_list or not settings.is_production:
    app.add_middleware(
        CORSMiddleware,
        # Defaults cover both Vite apps' dev (5173 customer / 5174
        # admin) and preview (4173 / 4174) servers, plus a fallback
        # Expo dev port in case the admin app moves back to Expo.
        # Overridden entirely by CORS_ORIGINS in production — never
        # falls back to these.
        allow_origins=settings.cors_origins_list
        or [
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:4173",
            "http://localhost:4174",
            "http://localhost:8081",
            "http://localhost:19006",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "One or more fields are invalid.",
                "details": exc.errors() if not settings.is_production else None,
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    # Never leak stack traces or internals in production.
    if not settings.is_production:
        raise exc
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "Something went wrong."}},
    )


@app.get("/health", tags=["System"], summary="Liveness check")
async def health():
    return {"status": "ok"}


@app.get("/health/db", tags=["System"], summary="Database connectivity check")
async def health_db():
    is_connected = await check_db_connection()
    return {"status": "ok" if is_connected else "unavailable"}


app.include_router(api_router)
