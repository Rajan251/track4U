import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.db.session import engine
from app.services.scheduler import start_scheduler, stop_scheduler
from app.web.router import web_router

logger = logging.getLogger(__name__)

# Configure root logger
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- Startup ----
    logger.info("🚀 Track4U starting up...")

    # Start 2× daily background scheduler
    scheduler = start_scheduler()
    logger.info("✅ Background scheduler active.")

    yield

    # ---- Shutdown ----
    logger.info("🛑 Track4U shutting down...")
    stop_scheduler()
    await engine.dispose()
    logger.info("👋 Shutdown complete.")


app = FastAPI(
    title="Track4U — SaaS Task Manager & Expiry Tracker",
    description=(
        "Multi-tenant SaaS Task Manager with:\n"
        "- 🌐 Domain & SSL Expiry Tracking (2× daily email alerts)\n"
        "- 🔔 Custom Date Reminders (e.g. password expiry, renewals)\n"
        "- 📋 Project & Task Management with Kanban board\n"
        "- ✉️ Smart email alerts with auto-stop on renewal"
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
origins = (
    settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create static dir if missing and mount
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "version": "2.0.0",
        "environment": settings.ENV,
        "database": "sqlite",
        "scheduler": "running (2× daily: 8AM + 8PM IST)",
        "smtp_configured": bool(settings.SMTP_USER and settings.SMTP_USER.strip()),
    }


# Include Routers
app.include_router(api_v1_router)
app.include_router(web_router)
