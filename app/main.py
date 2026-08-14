"""
FastAPI application entry point.

- Overrides default exception handlers for strict { "data": ..., "error": ... } envelope
- Lifespan: creates tables and seeds data on startup
- CORS middleware for Vapi tool calls
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.database import create_db_and_tables
from app.routes import router
from app.seed import seed_patients

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan: Startup & Shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run on startup: create tables and seed data."""
    logger.info("Starting up - creating database tables...")
    create_db_and_tables()
    logger.info("Seeding database if empty...")
    seed_patients()
    logger.info("Application ready.")
    yield
    logger.info("Shutting down.")


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Voice AI Agent — Patient Registration API",
    description="REST API for patient demographic data, designed for voice AI agent integration.",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# CORS Middleware (required for Vapi/Retell tool calls)
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Exception Handlers — STRICT ENVELOPE OVERRIDE
#
# CRITICAL: FastAPI's default handlers return {"detail": [...]} for 422 errors
# and {"detail": "..."} for HTTP exceptions. We MUST override both to return
# the strict envelope: { "data": null, "error": "..." }
# ---------------------------------------------------------------------------

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    """
    Override FastAPI's default 422 handler.
    Parses exc.errors() into clean, professional field-level messages.
    
    Output:  {"data": null, "error": "email: Value is not a valid email address"}
    NOT:     {"detail": [{"loc": ["body", "email"], "msg": "...", "type": "..."}]}
    """
    errors = exc.errors()
    messages = []
    for err in errors:
        # Build field path, excluding "body" prefix
        field_parts = [str(loc) for loc in err.get("loc", []) if loc != "body"]
        field = " -> ".join(field_parts) if field_parts else "unknown"
        msg = err.get("msg", "Invalid value")
        messages.append(f"{field}: {msg}")

    return JSONResponse(
        status_code=422,
        content={"data": None, "error": "; ".join(messages)},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc: StarletteHTTPException):
    """
    Override Starlette's default HTTP exception handler.
    Ensures 404, 405, etc. all return the strict envelope.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"data": None, "error": str(exc.detail)},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc: Exception):
    """
    Catch-all for unhandled exceptions.
    Logs the real error but returns a safe message to the client.
    """
    logger.error(f"Unhandled exception: {type(exc).__name__}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"data": None, "error": "Internal server error"},
    )


# ---------------------------------------------------------------------------
# Include Routes
# ---------------------------------------------------------------------------

app.include_router(router)


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@app.get("/")
def health_check():
    """Health check endpoint for deployment monitoring."""
    return {"status": "healthy"}
