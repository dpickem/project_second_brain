# API Endpoints

This document describes all available API endpoints and how to access them from **outside the Docker container**.

## Base URL

When running via Docker Compose, the backend API is exposed on port `8000`:

```
http://localhost:8000
```

---

## Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Root endpoint, returns API info |
| `POST` | `/ingest` | Ingest text content into the knowledge graph |
| `GET` | `/graph` | Retrieve the knowledge graph data |
| `GET` | `/api/health` | Basic health check |
| `GET` | `/api/health/detailed` | Detailed health with dependency status |
| `GET` | `/api/health/ready` | Readiness probe for orchestration |

---

## Endpoint Details

### Root

```bash
curl http://localhost:8000/
```

**Response:**
```json
{"message": "Second Brain API"}
```

---

### Ingest Content

Ingest text content into the knowledge graph. If `OPENAI_API_KEY` is configured, embeddings will be generated.

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"text": "Your content to ingest here"}'
```

**Request Body:**
```json
{
  "text": "The content you want to store in the knowledge graph"
}
```

**Response:**
```json
{"status": "ok"}
```

---

### Get Graph Data

Retrieve all nodes and relationships from the knowledge graph.

```bash
curl http://localhost:8000/graph
```

**Response:**
```json
{
  "nodes": [
    {"id": 1, "labels": ["Chunk"], "content": "...", "embedding": [...]}
  ],
  "relationships": [
    {"start": 1, "end": 2, "type": "RELATES_TO"}
  ]
}
```

---

### Health Check (Basic)

Simple health check to verify the API is running.

```bash
curl http://localhost:8000/api/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "second-brain"
}
```

---

### Health Check (Detailed)

Comprehensive health check that verifies connectivity to all dependencies:
- PostgreSQL database
- Redis cache
- Neo4j graph database
- Obsidian vault accessibility

```bash
curl http://localhost:8000/api/health/detailed
```

**Response (all healthy):**
```json
{
  "status": "healthy",
  "service": "second-brain",
  "dependencies": {
    "postgres": {"status": "healthy"},
    "redis": {"status": "healthy"},
    "neo4j": {"status": "healthy"},
    "obsidian_vault": {"status": "healthy", "path": "/vault"}
  }
}
```

**Response (degraded):**
```json
{
  "status": "degraded",
  "service": "second-brain",
  "dependencies": {
    "postgres": {"status": "healthy"},
    "redis": {"status": "unhealthy", "error": "Connection refused"},
    "neo4j": {"status": "healthy"},
    "obsidian_vault": {"status": "healthy", "path": "/vault"}
  }
}
```

---

### Readiness Probe

Used by Docker health checks, load balancers, and orchestration systems (e.g., Kubernetes) to determine if the service is ready to accept traffic.

```bash
curl http://localhost:8000/api/health/ready
```

**Response (ready):**
```json
{"ready": true}
```

**Response (not ready):**
```json
{"ready": false, "error": "Connection to database failed"}
```

---

## Interactive API Documentation

FastAPI provides automatic interactive documentation:

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Quick Test Script

Test all endpoints at once:

```bash
#!/bin/bash
BASE_URL="http://localhost:8000"

echo "=== Testing API Endpoints ==="

echo -e "\n1. Root endpoint:"
curl -s "$BASE_URL/"

echo -e "\n\n2. Basic health check:"
curl -s "$BASE_URL/api/health"

echo -e "\n\n3. Detailed health check:"
curl -s "$BASE_URL/api/health/detailed"

echo -e "\n\n4. Readiness probe:"
curl -s "$BASE_URL/api/health/ready"

echo -e "\n\n5. Get graph data:"
curl -s "$BASE_URL/graph"

echo -e "\n\n6. Ingest test content:"
curl -s -X POST "$BASE_URL/ingest" \
  -H "Content-Type: application/json" \
  -d '{"text": "Test content from endpoint test script"}'

echo -e "\n\n=== Done ==="
```

---

## Troubleshooting

### Connection Refused

If you get `Connection refused`, ensure the Docker containers are running:

```bash
docker-compose ps
docker-compose logs backend
```

### Port Already in Use

If port 8000 is already in use, you can change the port mapping in `docker-compose.yml`:

```yaml
backend:
  ports:
    - "8001:8000"  # Access via localhost:8001 instead
```

### View Backend Logs

```bash
docker-compose logs -f backend
```

