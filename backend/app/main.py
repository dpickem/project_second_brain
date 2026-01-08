"""
Second Brain API

FastAPI application for the Second Brain knowledge management system.
Provides endpoints for content ingestion, processing, and retrieval.

Components:
- Health check endpoints
- Quick capture API (text, URL, photo, voice, PDF)
- Ingestion management (sync triggers, queue stats)
- Content retrieval and graph exploration

Run with: uvicorn app.main:app --reload
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import (
    health_router,
    capture_router,
    ingestion_router,
    processing_router,
    vault_router,
    knowledge_router,
    practice_router,
    review_router,
    analytics_router,
)
from app.services.obsidian.lifecycle import (
    startup_vault_services,
    shutdown_vault_services,
)
from app.middleware.rate_limit import setup_rate_limiting
from app.middleware.error_handling import setup_error_handling
from app.services.knowledge_graph import get_neo4j_client

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    logger.info("Starting Second Brain API...")

    # Start scheduler for periodic syncs (lazy import to avoid test failures)
    try:
        from app.services.scheduler import start_scheduler
        start_scheduler()
        logger.info("Scheduler started")
    except Exception as e:
        logger.warning(f"Failed to start scheduler: {e}")

    # Start vault services (reconciliation + watcher)
    try:
        vault_results = await startup_vault_services()
        if vault_results.get("reconciliation"):
            logger.info(
                f"Vault reconciliation: {vault_results['reconciliation']['synced']} notes synced"
            )
        if vault_results.get("watcher_started"):
            logger.info("Vault watcher started")
    except Exception as e:
        logger.warning(f"Failed to start vault services: {e}")

    yield

    # Shutdown
    logger.info("Shutting down Second Brain API...")

    # Stop vault services
    try:
        await shutdown_vault_services()
    except Exception as e:
        logger.warning(f"Failed to stop vault services: {e}")

    try:
        from app.services.scheduler import stop_scheduler
        stop_scheduler()
    except Exception:
        pass

    # Close Neo4j client
    try:
        from app.services.knowledge_graph import get_neo4j_client
        client = await get_neo4j_client()
        await client.close()
    except Exception:
        pass


app = FastAPI(
    title="Second Brain API",
    description="Knowledge management and learning system API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error handling middleware (catches unhandled exceptions, provides correlation IDs)
setup_error_handling(app, debug=settings.DEBUG)

# Rate limiting middleware (prevents abuse)
# Note: Disabled by default, enable in production by setting RATE_LIMITING_ENABLED=true
setup_rate_limiting(app, enabled=getattr(settings, "RATE_LIMITING_ENABLED", False))

# Include routers
app.include_router(health_router.router)
app.include_router(capture_router.router)
app.include_router(ingestion_router.router)
app.include_router(processing_router.router)
app.include_router(vault_router.router)
app.include_router(knowledge_router.router)
app.include_router(practice_router.router)
app.include_router(review_router.router)
app.include_router(analytics_router.router)


@app.get("/graph")
async def graph():
    """
    Get all nodes and relationships from Neo4j.

    Returns a graph structure with nodes and relationships.
    """
    if not settings.NEO4J_PASSWORD:
        return {"nodes": [], "relationships": [], "message": "Neo4j not configured"}

    try:
        client = await get_neo4j_client()
        return await client.get_all_graph_data()
    except Exception as e:
        logger.warning(f"Failed to get graph data: {e}")
        return {"nodes": [], "relationships": [], "message": str(e)}


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Second Brain API",
        "version": "0.1.0",
        "docs": "/docs",
        "endpoints": {
            "capture": "/api/capture",
            "ingestion": "/api/ingestion",
            "processing": "/api/processing",
            "health": "/api/health",
            "knowledge": "/api/knowledge",
            "practice": "/api/practice",
            "review": "/api/review",
            "analytics": "/api/analytics",
        },
    }
