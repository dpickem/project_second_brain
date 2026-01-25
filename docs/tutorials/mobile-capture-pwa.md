# Mobile Capture PWA Tutorial

> Quick knowledge capture from your Mac, iPhone, or any device with a browser.

This tutorial covers:
1. [Quick Start - Mac Terminal](#quick-start---mac-terminal)
2. [Using the Web Interface](#using-the-web-interface)
3. [Installing on iPhone](#installing-on-iphone)
4. [Installing on Android](#installing-on-android)
5. [Sharing Content to the PWA (iPhone)](#sharing-content-to-the-pwa-iphone)
6. [Capture Types](#capture-types)
7. [Offline Support](#offline-support)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before using the capture system, ensure:

1. **Docker services are running**:
   ```bash
   cd ~/workspace/project_second_brain
   docker compose up -d
   ```

2. **API key is configured** in `.env`:
   ```bash
   CAPTURE_API_KEY=your_secure_key_here
   VITE_CAPTURE_API_KEY=your_secure_key_here  # Same key for frontend
   ```

3. **Backend is accessible**:
   ```bash
   curl http://localhost:8000/health
   # Should return: {"status":"healthy",...}
   ```

---

## Quick Start - Mac Terminal

### Get Your API Key

Your API key is in the `.env` file:
```bash
grep CAPTURE_API_KEY ~/workspace/project_second_brain/.env
```

### Set Up a Shell Alias (Recommended)

Add these to your `~/.zshrc` or `~/.bashrc`:

```bash
# Second Brain Capture aliases
export SB_API_KEY="your_capture_api_key_here"
export SB_API_URL="http://localhost:8000"

# Quick note capture
sb-note() {
  curl -s -X POST "$SB_API_URL/api/capture/text" \
    -H "X-API-Key: $SB_API_KEY" \
    -F "content=$1" \
    -F "title=${2:-}" | python3 -m json.tool
}

# URL capture
sb-url() {
  curl -s -X POST "$SB_API_URL/api/capture/url" \
    -H "X-API-Key: $SB_API_KEY" \
    -F "url=$1" \
    -F "notes=${2:-}" | python3 -m json.tool
}

# Voice memo capture
sb-voice() {
  curl -s -X POST "$SB_API_URL/api/capture/voice" \
    -H "X-API-Key: $SB_API_KEY" \
    -F "file=@$1" | python3 -m json.tool
}

# PDF capture
sb-pdf() {
  curl -s -X POST "$SB_API_URL/api/capture/pdf" \
    -H "X-API-Key: $SB_API_KEY" \
    -F "file=@$1" | python3 -m json.tool
}

# Photo capture
sb-photo() {
  curl -s -X POST "$SB_API_URL/api/capture/photo" \
    -H "X-API-Key: $SB_API_KEY" \
    -F "file=@$1" \
    -F "capture_type=${2:-general}" | python3 -m json.tool
}
```

Reload your shell:
```bash
source ~/.zshrc
```

### Usage Examples

```bash
# Capture a quick note
sb-note "Remember to review spaced repetition algorithm" "Study Note"

# Capture a URL
sb-url "https://arxiv.org/abs/2301.00001" "Interesting AI paper"

# Capture a voice memo
sb-voice ~/Downloads/meeting-notes.m4a

# Capture a PDF
sb-pdf ~/Documents/research-paper.pdf

# Capture a book page photo
sb-photo ~/Desktop/book-page.jpg "book_page"
```

### Raw curl Commands

If you prefer direct curl commands:

```bash
# Text capture
curl -X POST http://localhost:8000/api/capture/text \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "content=My idea or note" \
  -F "title=Optional title" \
  -F "tags=tag1,tag2"

# URL capture
curl -X POST http://localhost:8000/api/capture/url \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "url=https://example.com/article" \
  -F "notes=Why this is interesting"

# Voice memo
curl -X POST http://localhost:8000/api/capture/voice \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "file=@/path/to/audio.m4a" \
  -F "expand=true"

# PDF document
curl -X POST http://localhost:8000/api/capture/pdf \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "file=@/path/to/document.pdf"

# Photo (book page, whiteboard, document)
curl -X POST http://localhost:8000/api/capture/photo \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "file=@/path/to/image.jpg" \
  -F "capture_type=book_page"

# Multiple book pages (batch)
curl -X POST http://localhost:8000/api/capture/book \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "files=@page1.jpg" \
  -F "files=@page2.jpg" \
  -F "files=@page3.jpg" \
  -F "title=Deep Work by Cal Newport"
```

---

## Using the Web Interface

### Start the Capture PWA Dev Server

```bash
cd ~/workspace/project_second_brain/frontend
npm run dev:capture
```

The PWA will be available at: **http://localhost:5174/capture/**

### Features

- **Note** - Quick text capture with optional title and tags
- **URL** - Save links for later processing (auto-fetches page title)
- **Photo** - Camera capture or photo upload with OCR
- **Voice** - Record voice memos for transcription

---

## Installing on iPhone

### Step 1: Make Your Server Accessible

Your iPhone needs to reach the server. Options:

#### Option A: Same Wi-Fi Network (Recommended for home use)

1. Find your Mac's IP address:
   ```bash
   ipconfig getifaddr en0
   # Example output: 192.168.1.100
   ```

2. Update your `.env` to allow external connections:
   ```bash
   # In docker-compose.yml, backend already exposes port 8000
   # Just need to access via your Mac's IP
   ```

3. Test from iPhone Safari:
   ```
   http://192.168.1.100:8000/health
   ```

#### Option B: Tailscale/ZeroTier (Recommended for anywhere access)

1. Install [Tailscale](https://tailscale.com/) on both Mac and iPhone
2. Use your Tailscale IP (e.g., `100.x.x.x`)
3. Access: `http://100.x.x.x:8000`

#### Option C: Cloudflare Tunnel (For public access)

```bash
# Install cloudflared
brew install cloudflare/cloudflare/cloudflared

# Create a tunnel
cloudflared tunnel create second-brain
cloudflared tunnel route dns second-brain capture.yourdomain.com
cloudflared tunnel run second-brain
```

### Step 2: Start the Capture PWA

On your Mac:
```bash
cd ~/workspace/project_second_brain/frontend

# Start with network access (replace with your IP)
VITE_API_URL=http://192.168.1.100:8000 npm run dev:capture -- --host
```

The PWA will now be accessible at: `http://192.168.1.100:5174/capture/`

### Step 3: Install PWA on iPhone

1. **Open Safari** on your iPhone (must be Safari, not Chrome)

2. **Navigate to** `http://YOUR_MAC_IP:5174/capture/`

3. **Tap the Share button** (square with arrow pointing up)

4. **Scroll down and tap "Add to Home Screen"**

5. **Name it** "Capture" or "Second Brain"

6. **Tap "Add"**

The PWA is now installed and will appear on your home screen with an app icon.

### Step 4: Configure API Key

The PWA reads the API key from `VITE_CAPTURE_API_KEY` at build time. For development:

1. Ensure `.env` has:
   ```bash
   VITE_CAPTURE_API_KEY=your_capture_api_key
   ```

2. Restart the dev server after changing `.env`

For production builds:
```bash
cd frontend
npm run build:capture
# Deploy dist/capture/ to your web server
```

---

## Installing on Android

### Step 1: Access the PWA

1. Open **Chrome** on your Android device
2. Navigate to `http://YOUR_MAC_IP:5174/capture/`

### Step 2: Install

1. Chrome will show an **"Add to Home screen"** banner, or
2. Tap the **three-dot menu** → **"Add to Home screen"** or **"Install app"**
3. Confirm the installation

---

## Capture Types

| Type | Endpoint | Use Case |
|------|----------|----------|
| **Text** | `/api/capture/text` | Quick notes, ideas, quotes |
| **URL** | `/api/capture/url` | Articles, blog posts, papers |
| **Photo** | `/api/capture/photo` | Book pages, whiteboards, documents |
| **Voice** | `/api/capture/voice` | Voice memos, meeting notes |
| **PDF** | `/api/capture/pdf` | Research papers, ebooks, annotated documents |
| **Book** | `/api/capture/book` | Multiple book page photos |

---

## Sharing Content to the PWA (iPhone)

The capture PWA supports the **Web Share Target API**, allowing you to share content directly from other apps. This is the fastest way to capture content on iPhone.

> **Requirement**: The PWA must be installed on your home screen for sharing to work. See [Installing on iPhone](#installing-on-iphone).

### Sharing URLs from Safari

This is perfect for capturing articles, blog posts, documentation, or any web page.

1. **Open any webpage** in Safari
2. **Tap the Share button** (square with arrow pointing up)
3. **Scroll the app row** and tap **"Capture"** (or your PWA name)
4. The URL capture form opens with:
   - URL pre-filled
   - Page title auto-detected
5. **Add optional notes** about why this is interesting
6. **Tap "Capture"**

The article will be:
- Saved to your database
- Content fetched and extracted
- LLM-processed for summary and tags
- Added to your Obsidian vault

### Sharing URLs from Other Apps

Works the same way from any app with share functionality:

- **Twitter/X** - Share a tweet or article link
- **Reddit** - Share a post or link
- **News apps** - Share articles
- **Email** - Share links from emails
- **Slack/Discord** - Share message links

### Sharing PDFs

> ⚠️ **iOS Limitation**: Safari's Web Share Target API has limited support for receiving files. The PWA may not appear in the share sheet for PDFs. Use the workarounds below.

#### Recommended: Use the PWA Directly

The most reliable method on iPhone:

1. **Open the Capture PWA** from your home screen
2. **Tap "PDF"**
3. **Tap "Choose File"**
4. **Select your PDF** from Files, iCloud, or other locations
5. **Select content type** and tap **Capture**

#### Alternative: Save to Files First

1. **Share the PDF** to **"Save to Files"**
2. **Open the Capture PWA**
3. **Tap "PDF"** → **"Choose File"**
4. **Navigate to the saved PDF**

#### iOS Shortcut Method (Advanced)

Create a Shortcut that sends PDFs directly to the API:

1. **Open the Shortcuts app**
2. **Create new Shortcut**
3. **Add action**: "Get File"
4. **Add action**: "Get Contents of URL"
   - URL: `http://YOUR_MAC_IP:8000/api/capture/pdf`
   - Method: POST
   - Headers: `X-API-Key: YOUR_API_KEY`
   - Request Body: Form
   - Add field: `file` = Shortcut Input
5. **Save as "Capture PDF"**
6. **Enable "Show in Share Sheet"** in shortcut settings

Now you can share PDFs via the Shortcut.

#### On Android (Full Support)

Android fully supports Web Share Target for files:

1. **Open any PDF** in any app
2. **Tap Share**
3. **Select "Capture"** - it will appear in the share sheet
4. **PDF opens in the PWA** ready to submit

### Sharing Images/Photos

> ⚠️ **iOS Limitation**: Like PDFs, image file sharing via the share sheet has limited support. Use the PWA directly for the best experience.

#### Recommended: Use the PWA Camera/Upload

1. **Open the Capture PWA** from your home screen
2. **Tap "Photo"**
3. Either:
   - **Tap "Take Photo"** to use the camera
   - **Tap "Choose Photo"** to select from your library
4. **Select capture type**:
   - `Book Page` - For book photos with potential margin notes
   - `Whiteboard` - Whiteboard or presentation slides
   - `Document` - Printed documents, forms
   - `General` - Any other image
5. **Tap "Capture"**

#### From Photos App (if share works)

On some iOS versions, image sharing may work:

1. **Open the Photos app**
2. **Select a photo**
3. **Tap Share** → look for **"Capture"**
4. If it appears, the photo capture form opens
5. If not, use the PWA directly as described above

### Sharing Audio Files

> ⚠️ **iOS Limitation**: Audio file sharing via share sheet has limited support. Use the PWA's voice recording feature instead.

#### Recommended: Record in PWA

1. **Open the Capture PWA**
2. **Tap "Voice"**
3. **Tap "Start Recording"** (grant microphone permission)
4. **Speak your note**
5. **Tap "Stop"**
6. **Toggle "Expand into structured note"** if desired
7. **Tap "Capture"**

#### Alternative: Share Voice Memo File

If you have an existing voice memo:

1. **Open Voice Memos** app
2. **Tap the recording** → tap **"..."** → **"Save to Files"**
3. **Open Capture PWA** 
4. Use the **Mac terminal** to upload:
   ```bash
   sb-voice ~/path/to/memo.m4a
   ```

Or use an iOS Shortcut to POST the file to the API (see PDF section for setup).

### Share Troubleshooting

#### "Capture" Not Appearing in Share Sheet

**For URLs (should work):**
1. **PWA must be installed** - Add to Home Screen first
2. **Scroll the app row** - It may be off-screen to the right
3. **Tap "More"** or **"Edit Actions"** to find and enable it
4. **Reinstall the PWA** if still not showing

**For Files (PDFs, Images, Audio):**
- ⚠️ **This is an iOS limitation** - Safari's Web Share Target API has poor support for file sharing
- **Workaround**: Open the Capture PWA directly and use "Choose File" to select your content
- **Android works fine** - File sharing shows the PWA correctly

#### Share Opens But Nothing Happens

1. **Check network connection** - Must reach the PWA server
2. **Hard refresh the PWA** - Close and reopen from home screen
3. **Clear PWA data** - Settings → Safari → Advanced → Website Data → find your PWA

#### "Load Failed" Error When Sharing

This means the PWA can't reach the backend API:

1. **Check your Mac and iPhone are on the same network**
2. **Verify the backend is running**:
   ```bash
   docker compose ps
   curl http://YOUR_MAC_IP:8000/health
   ```
3. **Check firewall settings** on your Mac

#### Shared Content Shows "Pending Sync"

The content was captured but couldn't sync to the backend:

1. **Tap "Sync"** button in the PWA to retry
2. **Check API key** is configured correctly
3. **Verify backend is accessible**

### Supported Share Types

| Content | iOS Share Sheet | Android Share Sheet | PWA Direct |
|---------|-----------------|---------------------|------------|
| **URLs** | ✅ Works | ✅ Works | ✅ Works |
| **PDFs** | ⚠️ Limited | ✅ Works | ✅ Works |
| **Images** | ⚠️ Limited | ✅ Works | ✅ Works |
| **Audio** | ⚠️ Limited | ✅ Works | ✅ Record in PWA |
| **Text** | ✅ Works | ✅ Works | ✅ Works |

**Legend:**
- ✅ Works - Fully supported
- ⚠️ Limited - May not appear in share sheet; use PWA directly instead

---

### Photo Capture Types

When capturing photos, specify the type for optimized OCR:

| Type | Description |
|------|-------------|
| `book_page` | Physical book with potential margin notes |
| `whiteboard` | Whiteboard or blackboard |
| `document` | Printed document or form |
| `general` | General photo with text |

---

## Offline Support

The PWA works offline:

1. **Captures are queued** in IndexedDB when offline
2. **Automatic sync** when connection is restored
3. **Pending indicator** shows queued captures
4. **No data loss** - captures are preserved until synced

### How It Works

```
[Capture] → [Online?] → Yes → [Send to API] → [Done]
                ↓
               No
                ↓
         [Queue in IndexedDB]
                ↓
         [Show "Pending" badge]
                ↓
         [Connection restored]
                ↓
         [Background sync sends queued items]
```

---

## Troubleshooting

### "Missing API key" Error

```bash
# Check your API key is set
grep CAPTURE_API_KEY ~/workspace/project_second_brain/.env

# Ensure docker has the latest env vars
docker compose up -d backend
```

### iPhone Can't Connect

1. **Check firewall** - Allow incoming connections on port 8000 and 5174
   ```bash
   # macOS: System Preferences → Security & Privacy → Firewall → Options
   ```

2. **Verify IP address**:
   ```bash
   # On Mac
   ipconfig getifaddr en0
   
   # Test from iPhone Safari
   http://YOUR_IP:8000/health
   ```

3. **Check both devices on same network**

### PWA Not Installing on iPhone

- Must use **Safari** (not Chrome or other browsers)
- URL must be **HTTP or HTTPS** (not localhost)
- Page must have a valid **manifest.json**

### Voice Recording Not Working

- Grant **microphone permission** when prompted
- iOS requires **HTTPS** for microphone access in production
- Development over HTTP works on same device only

### Captures Not Processing

Check Celery workers are running:
```bash
docker compose logs celery-worker-1 --tail 50
docker compose logs celery-worker-2 --tail 50
```

Restart workers if needed:
```bash
docker compose restart celery-worker-1 celery-worker-2
```

---

## Security Notes

1. **API Key** - Keep your `CAPTURE_API_KEY` secret. Don't share it or commit it to git.

2. **Network Access** - When exposing your server:
   - Use a VPN (Tailscale) for remote access
   - Or use HTTPS with proper certificates for production

3. **Firewall** - Only open necessary ports (8000, 5174) to trusted networks

---

## Next Steps

After capturing content:

1. **View in Obsidian** - Processed notes appear in your vault
2. **Check the Dashboard** - See capture status at `http://localhost:3000`
3. **Review Knowledge Graph** - Explore connections in Neo4j browser at `http://localhost:7474`

---

## Related Documentation

- [Design Doc: Mobile Capture](../design_docs/08_mobile_capture.md)
- [Implementation Plan](../implementation_plan/08_mobile_capture_implementation.md)
- [API Reference](../design_docs/06_backend_api.md)
