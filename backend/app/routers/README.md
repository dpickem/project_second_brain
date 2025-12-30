# API Endpoints

This document describes all available API endpoints and how to access them from **outside the Docker container**.

## Base URL

When running via Docker Compose, the backend API is exposed on port `8000`:

```
http://localhost:8000
```

---

## Endpoints Overview

### Root Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Root endpoint, returns API info |
| `GET` | `/graph` | Retrieve the knowledge graph data |

### Health Endpoints (`/api/health`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Basic health check |
| `GET` | `/api/health/detailed` | Detailed health with dependency status |
| `GET` | `/api/health/ready` | Readiness probe for orchestration |

### Capture Endpoints (`/api/capture`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/capture/text` | Quick text/idea capture |
| `POST` | `/api/capture/url` | URL/article capture |
| `POST` | `/api/capture/photo` | Photo capture for OCR (single image) |
| `POST` | `/api/capture/voice` | Voice memo capture |
| `POST` | `/api/capture/pdf` | PDF document upload |
| `POST` | `/api/capture/book` | Batch book page capture (multiple images) |

### Ingestion Management (`/api/ingestion`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/ingestion/raindrop/sync` | Trigger Raindrop.io sync |
| `POST` | `/api/ingestion/github/sync` | Trigger GitHub starred sync |
| `GET` | `/api/ingestion/status/{content_id}` | Get processing status |
| `GET` | `/api/ingestion/queue/stats` | Get queue statistics |
| `GET` | `/api/ingestion/scheduled` | List scheduled jobs |
| `POST` | `/api/ingestion/scheduled/{job_id}/trigger` | Trigger scheduled job |
| `GET` | `/api/ingestion/pending` | List pending content |

---

## Capture vs Ingestion: Understanding the Difference

The API separates content acquisition into two distinct patterns:

### Capture (`/api/capture/*`) — Direct User Input

**Purpose:** Low-friction endpoints for capturing content directly from the user.

**Use case:** You're on your phone, have an idea, see an interesting article, take a photo of a book page, or record a voice memo. You want to capture it *now* with minimal friction.

**Characteristics:**
- **User-initiated:** You explicitly send content to capture
- **Immediate response:** Returns instantly after queueing (doesn't wait for processing)
- **Mobile-friendly:** Designed for quick capture from any device
- **File uploads:** Accepts photos, audio, PDFs directly
- **Single items:** One piece of content per request

**Flow:**
```
User → POST /api/capture/... → Queued → Background Processing → Obsidian Note
```

**Example scenarios:**
- Jotting down a quick idea while commuting
- Saving an article URL to read later
- Photographing a whiteboard after a meeting
- Recording a voice memo with thoughts on a book

**Note on book capture:**
Use `/api/capture/book` to upload multiple pages as a single book (batch processing). Use `/api/capture/photo` with `capture_type=book_page` for individual pages. See the "Batch Book Processing" section for details.

---

### Ingestion (`/api/ingestion/*`) — External Service Sync & Pipeline Management

**Purpose:** Administrative endpoints for syncing from external services and managing the processing pipeline.

**Use case:** You want to pull in bookmarks from Raindrop.io, sync starred GitHub repos, check if your content finished processing, or monitor the queue.

**Characteristics:**
- **System-initiated:** Pulls content from external APIs (Raindrop, GitHub)
- **Bulk operations:** Syncs many items at once
- **Scheduled:** Can run automatically on a schedule
- **Administrative:** Includes monitoring and management endpoints
- **No file uploads:** Works with external service APIs

**Flow:**
```
External Service (Raindrop/GitHub) → Sync Task → Queued → Background Processing → Obsidian Notes
```

**Example scenarios:**
- Daily automatic sync of new Raindrop bookmarks
- Importing your starred GitHub repositories
- Checking if a PDF finished processing
- Viewing how many items are in the processing queue
- Triggering a manual sync before going offline

---

### Quick Comparison

| Aspect | Capture | Ingestion |
|--------|---------|-----------|
| **Source** | Direct user input | External services |
| **Trigger** | User action | Manual trigger or schedule |
| **Volume** | Single item | Bulk (many items) |
| **Files** | Accepts uploads | No uploads |
| **Primary use** | Quick capture | Sync & management |
| **Typical client** | Mobile app, browser | Admin dashboard, cron |

---

## Batch Book Processing

### The Use Case

You're reading a physical book, taking photos of pages with highlights and margin notes. You want all those pages processed together as a single book, not as disconnected individual captures.

### Batch Book Endpoint

Use `/api/capture/book` to upload multiple page images as a single book:

```bash
curl -X POST http://localhost:8000/api/capture/book \
  -F "files=@page1.jpg" \
  -F "files=@page2.jpg" \
  -F "files=@page3.jpg" \
  -F "title=Deep Work" \
  -F "authors=Cal Newport" \
  -F "max_concurrency=10"
```

**Form Parameters:**
- `files` (required): Multiple image files (repeat `-F "files=@..."` for each page)
- `title` (optional): Book title (will be inferred from OCR if not provided)
- `authors` (optional): Comma-separated author names
- `isbn` (optional): ISBN if known
- `notes` (optional): Your notes about the book
- `max_concurrency` (optional): Parallel OCR calls, default 5 (5-20 recommended)

**Response:**
```json
{
  "status": "captured",
  "id": "uuid-string",
  "title": "Deep Work",
  "page_count": 3,
  "file_paths": ["/uploads/book_pages/..."],
  "max_concurrency": 10,
  "message": "Book with 3 pages queued for parallel OCR processing"
}
```

**Parallel Processing:**

Pages are processed in parallel using `asyncio.gather()` with a semaphore to limit concurrent API calls. This dramatically reduces processing time for large books.

| Pages | Concurrency | Estimated Time |
|-------|-------------|----------------|
| 10 | 5 | ~30 seconds |
| 50 | 10 | ~75 seconds |
| 100 | 10 | ~2.5 minutes |
| 200 | 15 | ~4 minutes |

**Task timeout:** 60 minutes (handles up to ~400 pages)

**What the pipeline does:**
- Processes page images via Vision LLM in **parallel** (limited by max_concurrency)
- Extracts page numbers from the images (doesn't assume upload order)
- Detects chapters from running headers/footers
- Distinguishes printed text from handwritten margin notes
- Identifies highlights and underlines
- Aggregates all pages into a single Obsidian note
- Tracks LLM costs for all API calls

### Individual Page Capture (Alternative)

If you prefer to capture pages one at a time, use `/api/capture/photo`:

```bash
curl -X POST http://localhost:8000/api/capture/photo \
  -F "file=@page1.jpg" -F "capture_type=book_page" -F "book_title=Deep Work"
```

**Limitation:** Each page becomes a separate content item rather than a unified book.

---

## Root Endpoints

### Root

```bash
curl http://localhost:8000/
```

**Response:**
```json
{
  "name": "Second Brain API",
  "version": "0.1.0",
  "docs": "/docs",
  "endpoints": {
    "capture": "/api/capture",
    "ingestion": "/api/ingestion",
    "health": "/api/health"
  }
}
```

### Get Graph Data

Retrieve all nodes and relationships from the Neo4j knowledge graph.

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

## Health Endpoints

### Basic Health Check

Simple health check to verify the API is running.

```bash
curl http://localhost:8000/api/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "Second Brain"
}
```

### Detailed Health Check

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
  "service": "Second Brain",
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
  "service": "Second Brain",
  "dependencies": {
    "postgres": {"status": "healthy"},
    "redis": {"status": "unhealthy", "error": "Connection refused"},
    "neo4j": {"status": "healthy"},
    "obsidian_vault": {"status": "healthy", "path": "/vault"}
  }
}
```

### Readiness Probe

Used by Docker health checks, load balancers, and orchestration systems (e.g., Kubernetes).

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

## Capture Endpoints

All capture endpoints return immediately after queueing content for background processing.

### Capture Text

Quick text capture for ideas, notes, and thoughts.

```bash
curl -X POST http://localhost:8000/api/capture/text \
  -F "content=My brilliant idea about knowledge management" \
  -F "title=Optional title" \
  -F "tags=idea,productivity"
```

**Form Parameters:**
- `content` (required): Text content to capture
- `title` (optional): Optional title
- `tags` (optional): Comma-separated tags

**Response:**
```json
{
  "status": "captured",
  "id": "uuid-string",
  "title": "My brilliant idea about knowledge management",
  "message": "Content queued for processing"
}
```

### Capture URL

Capture a URL for content extraction.

```bash
curl -X POST http://localhost:8000/api/capture/url \
  -F "url=https://example.com/article" \
  -F "notes=Great article about AI" \
  -F "tags=ai,reading"
```

**Form Parameters:**
- `url` (required): URL to capture
- `notes` (optional): Notes about why you saved this
- `tags` (optional): Comma-separated tags

**Response:**
```json
{
  "status": "captured",
  "id": "uuid-string",
  "title": "Page Title from URL",
  "url": "https://example.com/article",
  "message": "URL queued for content extraction"
}
```

### Capture Photo

Capture a photo for OCR processing. Supports book pages, whiteboards, and documents.

```bash
curl -X POST http://localhost:8000/api/capture/photo \
  -F "file=@page.jpg" \
  -F "capture_type=book_page" \
  -F "notes=Chapter 3 notes" \
  -F "book_title=Deep Work"
```

**Form Parameters:**
- `file` (required): Image file (JPEG, PNG, etc.)
- `capture_type` (optional): `book_page`, `whiteboard`, `document`, or `general` (default)
- `notes` (optional): Notes about the image
- `book_title` (optional): Book title if capturing book pages

**Response:**
```json
{
  "status": "captured",
  "id": "uuid-string",
  "file_path": "/uploads/photos/...",
  "capture_type": "book_page",
  "message": "Photo queued for OCR processing"
}
```

### Capture Voice

Capture a voice memo for transcription. Uses high-priority queue for faster processing.

```bash
curl -X POST http://localhost:8000/api/capture/voice \
  -F "file=@memo.m4a" \
  -F "expand=true"
```

**Form Parameters:**
- `file` (required): Audio file (mp3, m4a, wav, webm, ogg, flac)
- `expand` (optional): Expand transcript into structured note (default: true)

**Response:**
```json
{
  "status": "captured",
  "id": "uuid-string",
  "file_path": "/uploads/voice_memos/...",
  "message": "Voice memo queued for transcription (high priority)"
}
```

### Capture PDF

Upload a PDF for processing. Extracts text, highlights, and optionally handwritten annotations.

```bash
curl -X POST http://localhost:8000/api/capture/pdf \
  -F "file=@document.pdf" \
  -F "content_type_hint=paper" \
  -F "detect_handwriting=true"
```

**Form Parameters:**
- `file` (required): PDF file
- `content_type_hint` (optional): `paper`, `article`, `book`, or `general`
- `detect_handwriting` (optional): Detect handwritten annotations (default: true)

**Response:**
```json
{
  "status": "captured",
  "id": "uuid-string",
  "file_path": "/uploads/pdfs/...",
  "filename": "document.pdf",
  "message": "PDF queued for processing"
}
```

---

## Ingestion Management Endpoints

### Trigger Raindrop Sync

Sync bookmarks from Raindrop.io.

```bash
curl -X POST http://localhost:8000/api/ingestion/raindrop/sync \
  -H "Content-Type: application/json" \
  -d '{"since_days": 7, "collection_id": 0}'
```

**Request Body:**
```json
{
  "since_days": 7,
  "collection_id": 0
}
```
- `since_days`: Sync bookmarks from the last N days (default: 1)
- `collection_id`: Raindrop collection ID, 0 for all collections (default: 0)

**Response:**
```json
{
  "status": "sync_started",
  "since": "2024-01-20T00:00:00",
  "collection_id": 0,
  "message": "Raindrop sync queued"
}
```

### Trigger GitHub Sync

Sync starred repositories from GitHub.

```bash
curl -X POST http://localhost:8000/api/ingestion/github/sync \
  -H "Content-Type: application/json" \
  -d '{"limit": 50}'
```

**Request Body:**
```json
{
  "limit": 50
}
```
- `limit`: Maximum number of starred repos to sync (default: 50)

**Response:**
```json
{
  "status": "sync_started",
  "limit": 50,
  "message": "GitHub sync queued"
}
```

### Get Processing Status

Check the processing status of a captured content item.

```bash
curl http://localhost:8000/api/ingestion/status/{content_id}
```

**Response:**
```json
{
  "id": "uuid-string",
  "title": "Content title",
  "status": "processed",
  "error": null,
  "source_type": "article",
  "created_at": "2024-01-27T12:00:00",
  "obsidian_path": "Articles/content-title.md"
}
```

### Get Queue Statistics

Get processing queue statistics.

```bash
curl http://localhost:8000/api/ingestion/queue/stats
```

**Response:**
```json
{
  "status": "ok",
  "active": 2,
  "queued": 15,
  "scheduled": 3,
  "reserved": 1
}
```

### List Scheduled Jobs

List all scheduled sync jobs.

```bash
curl http://localhost:8000/api/ingestion/scheduled
```

**Response:**
```json
{
  "jobs": [
    {
      "id": "raindrop_sync",
      "name": "Raindrop Daily Sync",
      "next_run": "2024-01-28T00:00:00"
    }
  ],
  "count": 1
}
```

### Trigger Scheduled Job

Manually trigger a scheduled job immediately.

```bash
curl -X POST http://localhost:8000/api/ingestion/scheduled/raindrop_sync/trigger
```

**Response:**
```json
{
  "status": "triggered",
  "job_id": "raindrop_sync",
  "message": "Job raindrop_sync triggered for immediate execution"
}
```

### List Pending Content

List content items pending processing.

```bash
curl "http://localhost:8000/api/ingestion/pending?limit=20"
```

**Query Parameters:**
- `limit` (optional): Maximum items to return (default: 20)

**Response:**
```json
{
  "count": 5,
  "items": [
    {
      "id": "uuid-string",
      "title": "Pending item",
      "source_type": "article",
      "created_at": "2024-01-27T12:00:00"
    }
  ]
}
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

echo "=== Testing Second Brain API ==="

echo -e "\n1. Root endpoint:"
curl -s "$BASE_URL/" | jq .

echo -e "\n2. Basic health check:"
curl -s "$BASE_URL/api/health" | jq .

echo -e "\n3. Detailed health check:"
curl -s "$BASE_URL/api/health/detailed" | jq .

echo -e "\n4. Readiness probe:"
curl -s "$BASE_URL/api/health/ready" | jq .

echo -e "\n5. Get graph data:"
curl -s "$BASE_URL/graph" | jq .

echo -e "\n6. Queue statistics:"
curl -s "$BASE_URL/api/ingestion/queue/stats" | jq .

echo -e "\n7. Scheduled jobs:"
curl -s "$BASE_URL/api/ingestion/scheduled" | jq .

echo -e "\n8. Pending content:"
curl -s "$BASE_URL/api/ingestion/pending" | jq .

echo -e "\n9. Capture text:"
curl -s -X POST "$BASE_URL/api/capture/text" \
  -F "content=Test note from API test script" \
  -F "tags=test" | jq .

# Uncomment to test book capture (requires image files):
# echo -e "\n10. Capture book pages:"
# curl -s -X POST "$BASE_URL/api/capture/book" \
#   -F "files=@page1.jpg" \
#   -F "files=@page2.jpg" \
#   -F "title=Test Book" | jq .

echo -e "\n=== Done ==="
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
