# Web Ingestion Tutorial

> Capture content, upload files, and monitor the ingestion pipeline from the desktop web UI.

This tutorial covers:
1. [Getting to the Ingest Page](#getting-to-the-ingest-page)
2. [Capturing Text Notes](#capturing-text-notes)
3. [Capturing URLs](#capturing-urls)
4. [Uploading Files](#uploading-files)
5. [Monitoring the Ingestion Queue](#monitoring-the-ingestion-queue)
6. [Viewing Item Details and Errors](#viewing-item-details-and-errors)
7. [Tips and Keyboard Shortcuts](#tips-and-keyboard-shortcuts)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before using the Ingest page, ensure:

1. **Docker services are running**:
   ```bash
   cd ~/workspace/project_second_brain
   docker compose up -d
   ```

2. **Frontend is accessible**: Open http://localhost:3000 in your browser.

3. **Backend is healthy**:
   ```bash
   curl http://localhost:8000/health
   # Should return: {"status":"healthy",...}
   ```

---

## Getting to the Ingest Page

Navigate to the Ingest page using any of these methods:

- **Sidebar**: Click the upload icon (arrow pointing up into a tray) in the left navigation bar.
- **URL**: Go directly to http://localhost:3000/ingest.
- **Command Palette**: Press `Cmd+K` (or `Ctrl+K`) and type "Ingest".

The page has two main sections:
- **Capture Content** (top) -- Tabbed forms for text, URLs, and file uploads.
- **Ingestion Queue** (bottom) -- Live status of all content in the pipeline.

---

## Capturing Text Notes

1. The **Text** tab is selected by default. You'll see a text area with the prompt "What's on your mind?"
2. Type your note, idea, or any text content.
3. (Optional) Click **Options** to expand additional fields:
   - **Title** -- Give your note a custom title (otherwise one is auto-generated).
   - **Tags** -- Add comma-separated tags for categorization.
   - **Create Cards** -- Check to auto-generate spaced repetition flashcards.
   - **Create Exercises** -- Check to auto-generate practice exercises.
4. Click **Capture** or press `Cmd+Enter` (`Ctrl+Enter`) to submit.
5. A success toast confirms the capture. The note appears in the queue below.

### What happens after capture?

Your text note is saved to the database and queued for processing. The Celery background worker will:
1. Classify the content type.
2. Run LLM analysis, summarization, and extraction.
3. Create an Obsidian note in your vault.
4. Sync concepts to the Neo4j knowledge graph.
5. Optionally generate cards and exercises if you checked those options.

---

## Capturing URLs

1. Click the **URL** tab in the Capture Content panel.
2. Enter a URL starting with `http://` or `https://`. You can also click **Paste** to paste from your clipboard.
3. (Optional) Click **Options** to add:
   - **Notes** -- Why you're saving this URL, what caught your attention.
   - **Tags** -- Comma-separated tags.
4. Click **Capture** to submit.

The backend will fetch the page content, extract the article text, and process it through the full pipeline. This works well for:
- Blog posts and articles.
- Documentation pages.
- GitHub README files.
- News articles.

---

## Uploading Files

1. Click the **File** tab in the Capture Content panel.
2. **Drag and drop** a file onto the drop zone, or **click** to open a file picker.
3. Supported file types:
   | Type | Extensions | Processing |
   |------|-----------|------------|
   | PDF documents | `.pdf` | Mistral OCR, then full LLM pipeline |
   | Photos/images | `.jpg`, `.jpeg`, `.png`, `.heic` | Vision OCR for text extraction |
   | Audio/voice | `.m4a`, `.mp3`, `.wav` | Whisper transcription, then processing |
4. Once a file is selected, its name and size are shown. Click the X to remove it and pick a different file.
5. (Optional) Click **Options** to set:
   - **Content type hint** -- Help the system classify (e.g., "article", "paper", "book").
   - **Tags** -- Comma-separated tags.
6. Click **Upload** to submit.

### File size considerations

- PDFs up to ~50 pages work well. Larger documents may take several minutes.
- Image files should be reasonably clear for OCR accuracy.
- Audio files are transcribed using Whisper; keep recordings under 30 minutes for best results.

---

## Monitoring the Ingestion Queue

The bottom section of the Ingest page shows the **Ingestion Queue** -- a live view of all content items in your system.

### Status filters

Use the filter tabs to narrow the view:

| Tab | Shows |
|-----|-------|
| **All** | Every item regardless of status |
| **Pending** | Items queued but not yet being processed |
| **Processing** | Items currently being processed by the LLM pipeline |
| **Completed** | Successfully processed items with Obsidian notes |
| **Failed** | Items that encountered errors during ingestion or processing |

### Auto-refresh

The queue automatically refreshes every 10 seconds. You can also click the refresh icon (circular arrow) in the header to manually refresh.

### Queue item information

Each row in the queue shows:
- **Content type icon** -- Visual indicator of the content type (article, paper, photo, voice, etc.).
- **Title** -- The item title or "Untitled" if none was set.
- **Type and time** -- Content type and relative timestamp (e.g., "article -- 5 minutes ago").
- **Status badge** -- Color-coded status (yellow = Pending, blue = Processing, green = Completed, red = Failed).
- **Error indicator** -- Failed items show a warning triangle icon.

---

## Viewing Item Details and Errors

Click any item in the queue to open a **detail panel** on the right side.

### Detail panel contents

- **Title and metadata** -- Full title, content type, and creation timestamp.
- **Status** -- Current ingestion status with color-coded badge.
- **Source URL** -- Clickable link to the original source (for URL captures).
- **Summary** -- LLM-generated summary preview (if processing completed).
- **Processing Stages** -- Checklist showing which pipeline stages completed:
  - Content Analysis
  - Summarization
  - Extraction
  - Tagging
  - Obsidian Note
  - Knowledge Graph
- **Processing stats** -- Time taken, estimated cost, and token count.
- **Error Details** -- For failed items, shows both ingestion and processing error messages with full stack traces.
- **Metadata** -- Any additional metadata stored with the item.
- **Open in Knowledge Explorer** -- For processed items, a link to view the generated note.

### Investigating errors

When an item fails:
1. Click on the failed item (marked with a red badge and warning icon).
2. Check the **Error Details** section for the specific error message.
3. Common errors include:
   - **Connection timeout** -- The URL was unreachable or took too long.
   - **OCR failed** -- The image was too blurry or the PDF was corrupted.
   - **LLM rate limit** -- Too many concurrent requests; item will be retried.
   - **Content too large** -- The document exceeded processing limits.

To retry a failed item, use the Processing API:
```bash
curl -X POST http://localhost:8000/api/processing/reprocess \
  -H "Content-Type: application/json" \
  -d '{"content_id": "YOUR_CONTENT_UUID"}'
```

---

## Tips and Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd+Enter` / `Ctrl+Enter` | Submit the current capture form |
| `Cmd+K` / `Ctrl+K` | Open Command Palette for quick navigation |

### Best practices

1. **Tag consistently** -- Use the same tags across related captures for better organization.
2. **Add context** -- For URL captures, add a note explaining why you saved it. This helps the LLM generate better summaries.
3. **Use content type hints** -- When uploading PDFs, specifying "paper" or "book" helps the processing pipeline use the right templates.
4. **Monitor the queue** -- Check the Failed tab periodically to catch and retry failed imports.
5. **Enable learning material** -- Check "Create Cards" and "Create Exercises" for content you want to actively learn, not just archive.

---

## Troubleshooting

### Capture button stays disabled
- For text: Make sure you've typed something in the textarea.
- For URL: Ensure the URL starts with `http://` or `https://`.
- For file: Make sure a file is selected (shown in the drop zone).

### Items stuck in "Pending"
- Check that the Celery worker is running: `docker compose logs celery-worker-1 --tail=20`
- Verify Redis is accessible: `docker compose exec redis redis-cli ping`

### Items stuck in "Processing"
- Processing can take 30-60 seconds for articles, longer for PDFs.
- Check the Celery worker logs for errors: `docker compose logs celery-worker-1 -f`

### "No items in queue" even after capture
- The queue auto-refreshes every 10 seconds. Click the refresh button to update immediately.
- Check the browser console for API errors.

### File upload fails immediately
- Verify the backend is running: `curl http://localhost:8000/health`
- Check file size -- very large files may exceed upload limits.
- Ensure the file type is supported (PDF, JPG, PNG, HEIC, M4A, MP3, WAV).

---

## Related

- [Mobile Capture PWA Tutorial](mobile-capture-pwa.md) -- For mobile/on-the-go capture
- [Processing Pipeline](../design_docs/02_llm_processing_layer.md) -- How content is processed after capture
- [Ingestion Layer](../design_docs/01_ingestion_layer.md) -- Architecture of the ingestion system
