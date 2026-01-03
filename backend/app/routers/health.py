"""
Health Check Endpoints

Provides health check endpoints for monitoring and orchestration.

Endpoints:
- GET /api/health - Basic health check
- GET /api/health/detailed - Detailed health with dependency checks
- GET /api/health/ready - Readiness probe for orchestration systems
"""

from fastapi import APIRouter, Depends
from neo4j import GraphDatabase
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.base import get_db
from app.db.redis import get_redis
from app.services.queue import celery_app

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
async def health_check():
    """
    Basic health check.

    Returns a simple status response indicating the API is running.
    """
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
    }


@router.get("/detailed")
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """
    Detailed health check with dependency status.

    Checks connectivity to:
    - PostgreSQL database
    - Redis cache
    - Neo4j graph database
    - Obsidian vault accessibility
    - Celery workers
    """
    health = {"status": "healthy", "service": settings.APP_NAME, "dependencies": {}}

    # Check PostgreSQL
    try:
        await db.execute(text("SELECT 1"))
        health["dependencies"]["postgres"] = {"status": "healthy"}
    except Exception as e:
        health["dependencies"]["postgres"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"

    # Check Redis
    try:
        r = await get_redis()
        await r.ping()
        health["dependencies"]["redis"] = {"status": "healthy"}
    except Exception as e:
        health["dependencies"]["redis"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"

    # Check Neo4j
    try:
        driver = GraphDatabase.driver(
            settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        with driver.session() as session:
            session.run("RETURN 1")
        driver.close()
        health["dependencies"]["neo4j"] = {"status": "healthy"}
    except Exception as e:
        health["dependencies"]["neo4j"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"

    # Check Obsidian vault
    try:
        vault_path = Path(settings.OBSIDIAN_VAULT_PATH)
        if vault_path.exists() and vault_path.is_dir():
            health["dependencies"]["obsidian_vault"] = {
                "status": "healthy",
                "path": str(vault_path),
            }
        else:
            health["dependencies"]["obsidian_vault"] = {
                "status": "unhealthy",
                "error": "Vault directory not found",
            }
            health["status"] = "degraded"
    except Exception as e:
        health["dependencies"]["obsidian_vault"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        health["status"] = "degraded"

    # Check Celery workers
    try:
        inspect = celery_app.control.inspect(timeout=2.0)
        ping_response = inspect.ping()
        
        if ping_response:
            worker_names = list(ping_response.keys())
            active = inspect.active() or {}
            active_tasks = sum(len(v) for v in active.values())
            
            health["dependencies"]["celery_workers"] = {
                "status": "healthy",
                "worker_count": len(worker_names),
                "workers": worker_names,
                "active_tasks": active_tasks,
            }
        else:
            health["dependencies"]["celery_workers"] = {
                "status": "unhealthy",
                "error": "No workers responding",
                "worker_count": 0,
            }
            health["status"] = "degraded"
    except Exception as e:
        health["dependencies"]["celery_workers"] = {
            "status": "unhealthy",
            "error": str(e),
            "worker_count": 0,
        }
        health["status"] = "degraded"

    return health


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Readiness probe for orchestration systems.

    Returns 200 only if the service is ready to accept traffic.
    Checks critical dependencies (database, Redis).

    Used by: Docker health checks, load balancers, Kubernetes, etc.
    """
    try:
        # Check database connectivity
        await db.execute(text("SELECT 1"))

        # Check Redis connectivity
        r = await get_redis()
        await r.ping()

        return {"ready": True}
    except Exception as e:
        return {"ready": False, "error": str(e)}
