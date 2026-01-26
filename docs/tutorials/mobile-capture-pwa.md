# Mobile Capture PWA Tutorial

> Quick knowledge capture from your Mac, iPhone, or any device with a browser.

This tutorial covers:
1. [Quick Start - Mac Terminal](#quick-start---mac-terminal)
2. [Using the Web Interface](#using-the-web-interface)
3. [Installing on iPhone](#installing-on-iphone)
4. [Installing on Android](#installing-on-android)
5. [Capturing Content on iPhone](#capturing-content-on-iphone) (includes iOS limitations)
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

> **Note**: Due to iOS limitations, the PWA will **not** appear in Safari's share sheet. See [Capturing Content on iPhone](#capturing-content-on-iphone) for how to use the app.

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

## Capturing Content on iPhone

> ⚠️ **Important iOS Limitation**: iOS Safari **does not support the Web Share Target API**. This means the Capture PWA will **not appear in your iPhone's share sheet** when you try to share content from Safari or other apps. This is a [known WebKit limitation](https://bugs.webkit.org/show_bug.cgi?id=194593) that has been open since 2019 with no implementation timeline.
>
> **Android users**: Share Target works fully on Android with Chrome. See [Sharing on Android](#sharing-on-android-full-support).

### Your Options on iPhone

| Option | Pros | Cons |
|--------|------|------|
| **Use PWA Directly** | No setup, works now | Manual copy/paste for URLs |
| **Native App Wrapper** | Appears in share sheet | Requires Apple Developer account ($99/yr) |

---

### Option 1: Use the PWA Directly (Recommended)

The simplest approach is to open the Capture PWA from your home screen and manually enter content. This works reliably for all content types.

#### Capturing URLs

1. **Copy the URL** from Safari (tap the address bar → Copy)
2. **Open the Capture PWA** from your home screen
3. **Tap "URL"**
4. **Paste the URL** (tap the field → Paste)
5. **Add optional notes** about why this is interesting
6. **Tap "Capture"**

The article will be:
- Saved to your database
- Content fetched and extracted
- LLM-processed for summary and tags
- Added to your Obsidian vault

> **Tip**: Keep the Capture PWA in your iPhone dock for quick access.

#### Capturing Photos

1. **Open the Capture PWA** from your home screen
2. **Tap "Photo"**
3. Either:
   - **Tap "Take Photo"** to use the camera directly
   - **Tap "Choose Photo"** to select from your library
4. **Select capture type**:
   - `Book Page` - For book photos with potential margin notes
   - `Whiteboard` - Whiteboard or presentation slides
   - `Document` - Printed documents, forms
   - `General` - Any other image
5. **Tap "Capture"**

#### Capturing PDFs

1. **Open the Capture PWA** from your home screen
2. **Tap "PDF"**
3. **Tap "Choose File"**
4. **Select your PDF** from Files, iCloud, or other locations
5. **Select content type** and tap **Capture**

#### Recording Voice Memos

1. **Open the Capture PWA**
2. **Tap "Voice"**
3. **Tap "Start Recording"** (grant microphone permission if prompted)
4. **Speak your note**
5. **Tap "Stop"**
6. **Toggle "Expand into structured note"** if desired
7. **Tap "Capture"**

#### Capturing Text Notes

1. **Open the Capture PWA**
2. **Tap "Note"**
3. **Type or paste your content**
4. **Add optional title and tags**
5. **Tap "Capture"**

---

### Option 2: Native App Wrapper with PWABuilder (For Share Sheet Access)

If you need the Capture app to appear in the iOS share sheet, you can wrap the PWA in a native iOS app shell using [PWABuilder](https://www.pwabuilder.com/). This creates a real iOS app that can include a Share Extension.

You have two sub-options:
- **Option 2A**: Sideload for local testing (free, no App Store)
- **Option 2B**: Publish to App Store (requires $99/year developer account)

---

#### Option 2A: Sideload via Xcode (Free, Local Testing)

You can install a native wrapper directly onto your iPhone without the App Store by using Xcode to "sideload" the app. This is the only way to get a web-based app into the iOS share menu without paying for a developer account.

##### Requirements

- macOS with Xcode installed (free from the App Store)
- iPhone connected via USB
- Free Apple ID (any Apple account works)
- Your PWA running on your Mac's local network

##### Step 1: Set Up Your Local Connection

Your iPhone cannot see `localhost` on your Mac directly. You must use your Mac's local IP address.

1. **Find your Mac's IP address**:
   ```bash
   ipconfig getifaddr en0
   # Example output: 192.168.1.100
   ```

2. **Start your PWA** with network access:
   ```bash
   cd ~/workspace/project_second_brain/frontend
   VITE_API_URL=http://192.168.1.100:8000 npm run dev:capture -- --host
   ```

3. **Verify from iPhone**: Open `http://192.168.1.100:5174/capture/` in Safari on your iPhone to confirm it loads.

##### Step 2: Create the iOS Wrapper Project

You have two options to create the Xcode project:

**Option A: Use PWABuilder with a Temporary Public URL**

PWABuilder runs on remote servers and cannot access your local IP. You need to temporarily expose your PWA:

1. **Create a temporary tunnel** using ngrok or Cloudflare:
   ```bash
   # Using ngrok (install from https://ngrok.com)
   ngrok http 5174
   # This gives you a URL like https://abc123.ngrok.io
   ```

2. **Go to [PWABuilder.com](https://www.pwabuilder.com/)** and enter your ngrok URL

3. **Click "Package for stores"** → **iOS**

4. **Download the ZIP file** containing the Xcode project

5. **Modify the project** to use your local IP instead of the ngrok URL (we'll do this in Step 3)

**Option B: Create a Simple Wrapper Manually (No PWABuilder)**

Create a minimal iOS app from scratch - it's simpler than you might think:

1. **Open Xcode** → File → New → Project → App

2. **Configure the project**:
   - Product Name: "Capture"
   - Interface: SwiftUI
   - Language: Swift

3. **Replace the contents of `ContentView.swift`** with a WebView wrapper:

```swift
import SwiftUI
import WebKit

struct ContentView: View {
    // IMPORTANT: Replace with your Mac's local IP
    let captureURL = URL(string: "http://192.168.1.100:5174/capture/")!
    
    var body: some View {
        WebView(url: captureURL)
            .edgesIgnoringSafeArea(.all)
    }
}

struct WebView: UIViewRepresentable {
    let url: URL
    
    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.allowsInlineMediaPlayback = true
        
        let webView = WKWebView(frame: .zero, configuration: config)
        webView.allowsBackForwardNavigationGestures = true
        return webView
    }
    
    func updateUIView(_ webView: WKWebView, context: Context) {
        webView.load(URLRequest(url: url))
    }
}

#Preview {
    ContentView()
}
```

4. **Enable local network access** - Edit `Info.plist` and add:
   - `App Transport Security Settings` → `Allow Arbitrary Loads` → `YES`
   - This allows HTTP connections to your local network (required for development)

Now continue to Step 3 to add the Share Extension.

##### Step 3: Add the Share Extension in Xcode

Since standard PWAs don't support being a "share target," you must add a native Share Extension:

1. **Open your project** in Xcode (either the PWABuilder download or your manually created project)

2. **If you used PWABuilder**: Find where the app loads its URL and change it from the ngrok URL to your local IP (e.g., `http://192.168.1.100:5174/capture/`)

3. **Add a Share Extension**:
   - File → New → Target → Share Extension
   - Name it "CaptureShare" or similar
   - This adds a native "layer" that will appear in your iPhone's share menu

4. **Configure the Share Extension** to accept the content types you want:
   - Edit the extension's `Info.plist` to accept URLs, text, images, etc.

5. **Write the Share Extension logic** in `ShareViewController.swift`:

```swift
import UIKit
import Social
import MobileCoreServices
import UniformTypeIdentifiers

class ShareViewController: SLComposeServiceViewController {
    
    // IMPORTANT: Replace with your Mac's local IP
    let baseURL = "http://192.168.1.100:5174/capture/share"
    
    override func isContentValid() -> Bool {
        return true
    }
    
    override func didSelectPost() {
        guard let item = extensionContext?.inputItems.first as? NSExtensionItem,
              let attachments = item.attachments else {
            self.extensionContext?.completeRequest(returningItems: [], completionHandler: nil)
            return
        }
        
        for attachment in attachments {
            // Handle URLs
            if attachment.hasItemConformingToTypeIdentifier(UTType.url.identifier) {
                attachment.loadItem(forTypeIdentifier: UTType.url.identifier) { (data, error) in
                    if let url = data as? URL {
                        self.openCaptureApp(with: "url=\(url.absoluteString.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")")
                    }
                }
                return
            }
            
            // Handle plain text
            if attachment.hasItemConformingToTypeIdentifier(UTType.plainText.identifier) {
                attachment.loadItem(forTypeIdentifier: UTType.plainText.identifier) { (data, error) in
                    if let text = data as? String {
                        self.openCaptureApp(with: "text=\(text.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")")
                    }
                }
                return
            }
        }
        
        self.extensionContext?.completeRequest(returningItems: [], completionHandler: nil)
    }
    
    private func openCaptureApp(with queryParams: String) {
        let urlString = "\(baseURL)?\(queryParams)"
        guard let url = URL(string: urlString) else { return }
        
        // Open the main app with the shared data
        var responder: UIResponder? = self
        while responder != nil {
            if let application = responder as? UIApplication {
                application.open(url, options: [:], completionHandler: nil)
                break
            }
            responder = responder?.next
        }
        
        self.extensionContext?.completeRequest(returningItems: [], completionHandler: nil)
    }
    
    override func configurationItems() -> [Any]! {
        return []
    }
}
```

##### Step 4: Sideload to Your iPhone (No App Store)

You can install directly onto your iPhone for free:

1. **Connect your iPhone** to your Mac via USB

2. **Trust the computer** on your iPhone when prompted

3. **Select your iPhone** as the build destination in Xcode (top toolbar)

4. **Sign with your Apple ID**:
   - Go to the project settings (click the project name in the left sidebar)
   - Select "Signing & Capabilities" tab
   - Under "Team", sign in with your Apple ID
   - Xcode will create a "Personal Team" provisioning profile

5. **Click the Play button** (or Cmd+R) to build and install

6. **Trust the developer profile** on your iPhone:
   - Go to Settings → General → VPN & Device Management
   - Find your Apple ID under "Developer App"
   - Tap "Trust [your email]"

7. **Test it**: Open Safari, navigate to any webpage, tap Share, and look for your app!

##### Important Limitations

| Limitation | Details |
|------------|---------|
| **7-Day Expiry** | Apps installed with a free Apple ID expire after 7 days. You'll need to reconnect your phone and click "Run" in Xcode again to renew. |
| **Local Network Only** | Since your PWA runs on your Mac's local IP, it only works when your iPhone is on the same Wi-Fi network. |
| **3 App Limit** | Free Apple IDs can only have 3 sideloaded apps at a time. |
| **Device Must Be Connected** | You need to connect via USB to install/renew (or use wireless debugging in Xcode). |

> **Tip**: For a more permanent solution without the 7-day limit, consider Option 2B (App Store) or use a service like Tailscale to make your server accessible from anywhere.

---

#### Option 2B: Publish to App Store (Permanent Solution)

For a permanent solution without expiry limits, you can publish to the App Store or use TestFlight.

##### Requirements

- Apple Developer account ($99/year)
- macOS with Xcode installed
- Your PWA deployed to a **public HTTPS URL**

##### Steps

1. **Deploy your PWA** to a public URL with HTTPS:
   - Option: Use Cloudflare Tunnel for free HTTPS
   - Option: Deploy to Vercel, Netlify, or similar

2. **Go to [PWABuilder.com](https://www.pwabuilder.com/)**

3. **Enter your public PWA URL** and let it analyze your manifest

4. **Click "Package for stores"** → **iOS**

5. **Download the Xcode project**

6. **Add a Share Extension** (same steps as Option 2A, Step 3)
   - Update the `baseURL` to your public HTTPS URL

7. **Build and submit**:
   - For personal use: Upload to TestFlight
   - For public distribution: Submit to App Store review

> **Note**: These are advanced options that require iOS development knowledge. For most users, Option 1 (using the PWA directly) is recommended.

---

### Sharing on Android (Full Support)

Android fully supports the Web Share Target API. The Capture PWA will appear in your share sheet after installation.

#### Sharing URLs

1. **Open any webpage** in Chrome
2. **Tap the Share button**
3. **Select "Capture"** from the app list
4. The URL capture form opens with the URL pre-filled
5. **Add optional notes** and tap **Capture**

#### Sharing Files

1. **Open any PDF, image, or audio file**
2. **Tap Share**
3. **Select "Capture"** - it will appear in the share sheet
4. The appropriate capture form opens with the file ready
5. **Tap Capture**

### Supported Capture Methods by Platform

| Content | iOS | Android |
|---------|-----|---------|
| **URLs** | PWA direct (copy/paste) | Share sheet ✅ |
| **PDFs** | PWA direct (file picker) | Share sheet ✅ |
| **Images** | PWA direct (camera/picker) | Share sheet ✅ |
| **Audio** | PWA direct (record/picker) | Share sheet ✅ |
| **Text** | PWA direct (type/paste) | Share sheet ✅ |

---

### Why iOS Doesn't Support Share Target

The Web Share Target API allows PWAs to register as share destinations in the operating system's share sheet. While this works on Android (Chrome), Apple has not implemented this feature in Safari/WebKit.

- **WebKit Bug**: [Bug 194593 - Add support for Web Share Target API](https://bugs.webkit.org/show_bug.cgi?id=194593)
- **Filed**: February 2019
- **Status**: NEW (not assigned, no implementation timeline)
- **Browser Support**: [Can I Use - share_target](https://caniuse.com/mdn-html_manifest_share_target)

This is separate from the **Web Share API** (which iOS *does* support), which allows web pages to *send* content to the share sheet. The limitation is specifically about *receiving* shared content.

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
- **Icons must be PNG format** - iOS Safari does not support SVG icons for PWAs
- Clear Safari cache before reinstalling if you had an older version

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
