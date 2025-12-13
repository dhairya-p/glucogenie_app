"""Main FastAPI application entry point.

This file wires together the FastAPI app, Supabase auth, and shared infrastructure.
Feature-specific routes live in `app/routers/`.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict
from supabase import Client, create_client

# Configure logging to show INFO level and above
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
    force=True,  # Override any existing configuration
)

logger = logging.getLogger(__name__)
logger.info("=== Backend logging initialized ===")


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    These map to the same SUPABASE env vars that the Flutter app uses.
    Secrets must NEVER be hard-coded in code.
    """

    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str | None = None

    neo4j_uri: str | None = None
    neo4j_username: str | None = None
    neo4j_password: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan hook.

    Initializes shared resources (Supabase client, Neo4j driver, etc.)
    once at startup and cleans them up on shutdown.
    """
    settings = Settings()
    app.state.settings = settings

    # Supabase client (use service role key when available for backend-only work).
    supabase_key = settings.supabase_service_role_key or settings.supabase_anon_key
    app.state.supabase: Client = create_client(settings.supabase_url, supabase_key)

    # TODO: Initialize Neo4j driver here when connection details are available.
    app.state.neo4j_driver = None

    logger.info("Backend startup complete")
    try:
        yield
    finally:
        neo4j_driver = getattr(app.state, "neo4j_driver", None)
        if neo4j_driver is not None:
            neo4j_driver.close()
        logger.info("Backend shutdown complete")


app = FastAPI(
    title="Diabetes Assistant Backend",
    description="FastAPI backend for the Diabetes FYP (Supabase + Agents).",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration – allow local frontend and Supabase Studio origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",  # Allow all origins for development (restrict in production)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers
from app.routers import chat, health, insights, meals

app.include_router(health.router)
app.include_router(chat.router)  # Chat router has its own prefix
app.include_router(insights.router, prefix="/api")
app.include_router(meals.router, prefix="/api")

# Future routers:
# from app.routers import glucose, profile
# app.include_router(glucose.router, prefix="/api/glucose", tags=["glucose"])
# app.include_router(profile.router, prefix="/api/profile", tags=["profile"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
