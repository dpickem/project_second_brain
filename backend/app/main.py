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
from neo4j import GraphDatabase

from app.config import settings
from app.routers import (
    health_router,
    capture_router,
    ingestion_router,
    processing_router,
    vault_router,
    knowledge_router,
)
from app.services.scheduler import start_scheduler, stop_scheduler
from app.services.obsidian.lifecycle import (
    startup_vault_services,
    shutdown_vault_services,
)

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

    # Start scheduler for periodic syncs
    try:
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
        stop_scheduler()
    except Exception:
        pass

    # Close Neo4j driver
    if _driver:
        _driver.close()


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

# Include routers
app.include_router(health_router.router)
app.include_router(capture_router.router)
app.include_router(ingestion_router.router)
app.include_router(processing_router.router)
app.include_router(vault_router.router)
app.include_router(knowledge_router.router)

# Neo4j driver (initialized if password is configured)
_driver = None
if settings.NEO4J_PASSWORD:
    try:
        _driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
        logger.info("Neo4j driver initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize Neo4j driver: {e}")


@app.get("/graph")
async def graph():
    """
    Get all nodes and relationships from Neo4j.

    Returns a graph structure with nodes and relationships.
    """
    if not _driver:
        return {"nodes": [], "relationships": [], "message": "Neo4j not configured"}

    with _driver.session() as session:
        result = session.run("MATCH (n)-[r]->(m) RETURN n,r,m")
        nodes = []
        rels = []
        seen = set()

        for record in result:
            n = record["n"]
            m = record["m"]
            r = record["r"]

            if n.id not in seen:
                nodes.append({"id": n.id, "labels": list(n.labels), **dict(n)})
                seen.add(n.id)

            if m.id not in seen:
                nodes.append({"id": m.id, "labels": list(m.labels), **dict(m)})
                seen.add(m.id)

            rels.append(
                {
                    "start": r.start_node.id,
                    "end": r.end_node.id,
                    "type": r.type,
                }
            )

    return {"nodes": nodes, "relationships": rels}


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
        },
    }
