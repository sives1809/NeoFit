"""
app/main.py
-----------
FastAPI application factory.

Run locally:
    uvicorn app.main:app --reload --port 8000

The auto-generated interactive docs are at:
    http://localhost:8000/docs        (Swagger UI)
    http://localhost:8000/redoc       (ReDoc)
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, measure, sessions, profile, diet, predict, validate

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
log = logging.getLogger("muscle_tracker")

# ── App ───────────────────────────────────────────────────────────────────────
settings = get_settings()

app = FastAPI(
    title="AI Muscle Growth Tracker API",
    version="1.0.0",
    description=(
        "Backend for the AI-powered personalized fitness platform. "
        "Processes MediaPipe Pose landmarks, computes real-world measurements, "
        "and provides diet / prediction services."
    ),
    # Disable docs in production if desired
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
API_PREFIX = "/api/v1"

app.include_router(auth.router,     prefix=API_PREFIX)
app.include_router(measure.router,  prefix=API_PREFIX)
app.include_router(sessions.router, prefix=API_PREFIX)
app.include_router(profile.router,  prefix=API_PREFIX)
app.include_router(diet.router,     prefix=API_PREFIX)
app.include_router(predict.router,  prefix=API_PREFIX)
app.include_router(validate.router, prefix=API_PREFIX)


# ── Health check (no auth required) ──────────────────────────────────────────
@app.get("/health", tags=["infra"])
async def health() -> dict:
    """Used by Railway / Render deployment health checks."""
    return {"status": "ok", "version": app.version}


# ── Startup hook ──────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup() -> None:
    log.info("=== Muscle Tracker API starting ===")
    log.info("Environment : %s", settings.app_env)
    log.info("CORS origins: %s", settings.cors_origins_list)
    log.info("Supabase URL: %s", settings.supabase_url)
    log.info("Loaded CORS origins: %s", settings.cors_origins_list)
    log.info("Backend is fully hot-reloaded and ready!")
