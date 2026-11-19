# 🎬 Deployment-Readiness Audit & Production Plan
**Project:** Viral Shorts Studio (AI Video Clipping & 9:16 Shorts Generator)  
**Date of Audit:** November 19, 2026  
**Auditor:** Antigravity AI Deployment Specialist  
**Status:** ⚠️ **Not Production-Ready (Critical Architectural & OS Blockers Identified)**

---

## 1. Executive Summary

Viral Shorts Studio is currently configured and operating as a **local Windows desktop-backed web application**. It combines a clean, modern, glassmorphic single-page frontend (HTML5/CSS3/Vanilla JS) with a multi-threaded Python standard library backend (`http.server.ThreadingHTTPServer`), local `faster-whisper` AI transcription, `yt-dlp` for YouTube extraction, and FFmpeg for complex 9:16 portrait video compositing and audio mastering.

While the core clipping and styling functionality works effectively on a local Windows PC, deploying it to a public cloud environment as a multi-user web application currently faces **critical architectural blockers**:
1. **Windows-dependent binaries and calls** (e.g., bundled `ffmpeg.exe`, `os.startfile`, `webbrowser.open`).
2. **Synchronous request blocking** (a single batch render takes 2–5+ minutes, immediately exceeding cloud HTTP gateway timeouts).
3. **Heavy CPU/RAM resource consumption** (exceeds serverless and free-tier cloud limits).
4. **Ephemeral storage** (generated MP4s and uploads are saved to local disk, which resets on container restarts).
5. **YouTube datacenter IP blocking** (`yt-dlp` requests from cloud hosting IPs are frequently flagged as bots).

---

## 2. Existing Technology Stack

| Layer | Current Implementation | Production Assessment |
|---|---|---|
| **Frontend Framework** | Vanilla JavaScript (ES6+), Semantic HTML5, CSS3 Glassmorphism | ✅ Lightweight, responsive, zero dependencies, no build step required. Works in all modern browsers. |
| **Frontend Bundler / Build Tool** | None (`index.html`, `client.js`, `styles.css` served directly) | ✅ No npm/build step needed; static assets can be served directly or via CDN. |
| **Backend Framework** | Python standard library `http.server` (`ThreadingHTTPServer`, `BaseHTTPRequestHandler`) | ⚠️ Not production-grade. Lacks async event loop, connection pooling, graceful shutdown, request validation, and ASGI/WSGI compliance. |
| **Backend Runtime** | Python 3.10+ (tested with 3.12/3.13) | ✅ Standard Python environment. |
| **AI Speech Recognition** | `faster-whisper` (CTranslate2, `tiny` model, `int8` CPU quantization) | ⚠️ Model downloads (~75MB) on first execution. Consumes significant CPU/RAM during inference. |
| **Video Extraction** | `yt-dlp` (direct YouTube scraping, retention heatmaps, chapters, captions) | ⚠️ Requires a JavaScript runtime (Node.js) on the system. Datacenter IPs are often blocked by YouTube. |
| **Video & Audio Processing** | FFmpeg (CLI subprocess with complex multi-stream filtergraphs) | 🚨 Uses bundled Windows `ffmpeg.exe` (87.6 MB). Incompatible with Linux cloud containers. |
| **System Dependencies** | Node.js (for yt-dlp JS signature engine), Windows system fonts (`Impact`, `Arial Black`) | ⚠️ Linux environments lack these fonts by default, causing FFmpeg subtitle rendering failures. |
| **State & Storage** | Local filesystem (`uploads/`, `output/`, `assets/sfx/`) | 🚨 Ephemeral cloud containers will wipe files on restart/scale. |
| **Database & Auth** | None (Stateless / In-memory during request turn) | 🚨 No user authentication, job queues, or rate limiting; vulnerable to resource exhaustion. |

---

## 3. Detailed Component Audit

### 3.1 Video Upload & File Ingestion
- **Current Behavior**:
  - Direct binary upload to `/api/upload` with an `X-Filename` header, streaming chunks directly into the local `uploads/` folder.
  - PC local path loading via `/api/check-local`: Allows users to supply absolute paths (e.g. `C:\Users\...`).
- **Production Assessment**:
  - The local path feature (`/api/check-local`) **only works on the host machine** and exposes a local path probing security issue. In production, this must be disabled or strictly repurposed.
  - Uploading large video files (100MB–2GB) directly through a synchronous web worker locks up memory and worker threads. Cloud hosting platforms enforce upload body size limits (e.g., Vercel: 4.5MB; Cloudflare: 100MB). Direct-to-object-storage pre-signed uploads are standard for production.

### 3.2 Video Processing, AI Clipping & Rendering
- **Current Behavior**:
  - **Analysis**: `yt-dlp` extracts metadata, chapters, and the YouTube retention heatmap curve. It computes sliding-window retention averages to identify 4–6 peak engagement moments (15–60s). For local files, it segments by duration intervals.
  - **Subtitles**: `faster-whisper` transcribes audio from the cut segment locally to extract word-level timestamps. Subtitles are compiled into an Advanced SubStation Alpha (`.ass`) file with 3D drop-shadows, bevels, and kinetic scale animations (`\fscx125\fscy125`).
  - **Compositing**: FFmpeg builds a 9:16 canvas (blurred background, center crop, or split screen), applies dynamic camera zoom punch-ins (`crop=w='if(...)':h='if(...)'`), copyright shield color grading, burns in `.ass` subtitles, mixes sound effects (`assets/sfx/*.wav`), and normalizes audio via EBU R128 (`loudnorm=-14 LUFS`).
- **Production Assessment**:
  - FFmpeg execution and Whisper transcription take **30 to 90 seconds per single clip**, and **2 to 6+ minutes for a 5-clip batch**.
  - Because `server.py` processes jobs synchronously within the HTTP handler, requests will encounter **HTTP 504 / 502 Gateway Timeouts** on nearly all public cloud providers.

### 3.3 Download & File Serving
- **Current Behavior**:
  - Serves MP4s, thumbnails, and ZIP archives directly from `/output/<filename>` using custom HTTP Range parsing in Python.
  - Features an `/api/open-folder` endpoint that calls `os.startfile(OUTPUT_DIR)`.
- **Production Assessment**:
  - `os.startfile` is a **Windows-only API** that immediately crashes on Linux (`AttributeError`).
  - Serving large video files through Python standard library handlers is inefficient and consumes worker bandwidth. Static file delivery in production should be handled by a reverse proxy (Nginx), CDN, or direct S3/R2 signed URLs.

---

## 4. Hosting Compatibility Analysis

### 4.1 Vercel
- **Compatibility:** ❌ **Incompatible for Full-Stack / Backend** | ⚠️ **Frontend Only**
- **Blockers:**
  1. **Execution Timeout**: Vercel Serverless Functions have hard timeouts (10s default, 60s max on Hobby, 300s on Pro). Single clip rendering frequently exceeds 60s; batch rendering (2–5 min) will fail.
  2. **Read-Only Filesystem**: Vercel functions cannot write to disk (only `/tmp` is writable, capped at 500MB). A single raw video + 5 rendered 1080x1920 MP4s easily exceeds 500MB.
  3. **Binary Dependencies**: Vercel does not provide system FFmpeg compiled with `libass` and standard Windows fonts.
  4. **Architecture**: `server.py` is written as a long-running daemon (`serve_forever()`), which cannot run in Vercel's event-driven serverless architecture.
- **Feasible Hybrid Role**: Vercel can host the static frontend (`index.html`, `client.js`, `styles.css`, `assets/`) if the backend is hosted on a containerized service.

### 4.2 Render
- **Compatibility:** ✅ **Compatible via Docker Web Service + Background Worker**
- **Recommended Setup:**
  - **Web Service (API & UI)**: Docker container running a FastAPI/Uvicorn or Python service with FFmpeg, Node.js, and font packages installed.
  - **Compute Plan**: Requires at least the **Starter** (512MB–1GB RAM minimum, 2GB recommended) or **Standard** plan. The free tier (512MB) will crash with Out-Of-Memory (OOM) errors during Whisper and FFmpeg execution.
  - **Storage**: Requires an attached Persistent Disk (e.g., 10GB–50GB) or cloud object storage (Cloudflare R2 / AWS S3) to preserve uploaded and generated videos across container restarts.
  - **Worker Requirement**: Because Render web services have an HTTP proxy timeout (~100 seconds), long-running batch jobs must be handled asynchronously via background tasks or a task queue.

### 4.3 Alternative Cloud Hosts
- **Railway**: Excellent fit. Provides native Dockerfile deployment, persistent volumes, background workers, and customizable memory/CPU.
- **Fly.io**: Excellent fit. True Linux microVMs with dedicated CPU/RAM, persistent storage volumes, and no arbitrary HTTP proxy timeouts.
- **Dedicated Cloud VPS (Hetzner / DigitalOcean / AWS EC2)**: **Most cost-effective**. For CPU/GPU-heavy video transcoding, a $10–$25/mo VPS provides dedicated multi-core CPUs, persistent SSDs, and zero timeout constraints.

---

## 5. Security & Production Failure Risks

| Risk Area | Severity | Root Cause | Impact | Required Remediation |
|---|---|---|---|---|
| **Local OS Function Calls** | 🚨 Critical | `os.startfile()` in `/api/open-folder` & `webbrowser.open()` | Crashes the server with `AttributeError` on Linux/cloud containers. | Remove or guard with `if sys.platform == 'win32'`. In web apps, replace folder opening with in-browser file management. |
| **Path Traversal Vulnerability** | 🚨 High | Direct concatenation in `serve_file`: `os.path.join(OUTPUT_DIR, rel_file)` | A malicious user could request `/output/../../etc/passwd`. | Sanitize paths using `os.path.commonpath` or `pathlib.Path.resolve()`. |
| **Local File Path Exposure** | 🚨 High | `/api/check-local` endpoint accepts raw paths from user | Users could probe server filesystem structure or read internal files. | Disable or restrict to authenticated admin debug mode. |
| **Denial of Service (DoS)** | 🚨 High | Unauthenticated public endpoints with synchronous FFmpeg processing | 2–3 concurrent batch requests will lock all CPU cores and exhaust RAM (OOM crash). | Add user authentication, request queuing (max concurrent jobs), and rate limiting. |
| **YouTube Bot Detection** | ⚠️ High | `yt-dlp` scraping YouTube directly from datacenter IP addresses | Cloud provider IPs (AWS, Render, GCP) receive HTTP 429 / "Sign in to confirm you're not a bot". | Configure residential proxies or inject exported YouTube cookies via environment variables. |
| **Missing Fonts on Linux** | ⚠️ Medium | `.ass` generator specifies `Impact` and `Arial Black` | Default headless Linux distributions lack MS TrueType fonts; FFmpeg falls back to generic fonts, breaking 3D formatting. | Install `msttcorefonts` and `fonts-liberation` in the Dockerfile. |
| **Ephemeral Data Loss** | ⚠️ Medium | Outputs saved to local `./output` directory | Redeploying or restarting the container wipes all generated videos and active download links. | Offload files to Cloudflare R2 / AWS S3, or mount a persistent volume. |

---

## 6. Required Environment Variables

For a secure and stable production deployment, the following environment variables must be defined. **Never commit actual values or secrets to git.**

```bash
# Server & Environment Configuration
ENVIRONMENT=production                 # production | development
PORT=5000                              # Assigned dynamically by Render / Railway
HOST=0.0.0.0                           # Bind address
SECRET_KEY=change-this-to-a-random-32-char-secret
CORS_ALLOWED_ORIGINS=https://yourdomain.com

# Storage Configuration (Local Persistent Disk or Cloud Object Storage)
STORAGE_TYPE=s3                        # local | s3
S3_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com  # (If using Cloudflare R2)
S3_BUCKET_NAME=viral-shorts-production
S3_REGION=auto
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
S3_PUBLIC_BASE_URL=https://cdn.yourdomain.com

# Processing & Resource Limits
MAX_UPLOAD_SIZE_MB=500                 # Maximum upload size in megabytes
MAX_CONCURRENT_RENDERS=2               # Max simultaneous FFmpeg jobs to prevent OOM
WHISPER_DEVICE=cpu                     # cpu | cuda
WHISPER_MODEL=tiny                     # tiny | base

# Anti-Bot & Proxy Configuration (For YouTube Extraction)
YTDLP_PROXY_URL=                       # Optional: http://user:pass@proxy.service.com:8080
YTDLP_COOKIES_BASE64=                  # Optional: Base64 encoded cookies.txt for YouTube auth
```

---

## 7. Database & Storage Architecture

### 7.1 Database Setup (Recommended for Multi-User Production)
In its current state, the app is stateless in-memory. For a robust production service with multiple concurrent users:
- **Recommended Database**: PostgreSQL (via Supabase, Neon, or Render Managed PostgreSQL) or SQLite (with a persistent disk volume).
- **Required Tables**:
  1. `jobs`: `id` (UUID), `status` (`queued`, `analyzing`, `rendering`, `completed`, `failed`), `progress_pct` (INT), `source_type` (`url`, `upload`), `source_url`, `created_at`, `updated_at`.
  2. `clips`: `id` (UUID), `job_id` (FK), `title`, `start_time`, `end_time`, `virality_score`, `layout`, `subtitle_style`, `video_s3_url`, `file_size_mb`, `suggested_title`, `suggested_description`, `suggested_tags`.

### 7.2 Storage Setup
- **Development**: Local directories `./uploads` and `./output`.
- **Production**:
  - **Cloudflare R2** (Zero egress fees, high performance) or **AWS S3**.
  - Generated clips and ZIP archives are uploaded directly to the bucket upon completion.
  - Video previews and downloads are served via signed URLs or public CDN URLs (`https://cdn.yourdomain.com/output/short_123.mp4`).

---

## 8. Build & Deployment Specifications

### 8.1 Docker Containerization (The Industry Standard for FFmpeg/Python Apps)
Because this application depends on system packages (`ffmpeg`, `libass`, `nodejs`, `fonts`), containerization using Docker is the most reliable deployment method for Render, Railway, or VPS.

#### Recommended `Dockerfile`:
```dockerfile
# Use official lightweight Python image
FROM python:3.11-slim

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies: FFmpeg (with libass), Node.js, and font libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libass-dev \
    nodejs \
    fonts-liberation \
    fonts-freefont-ttf \
    fontconfig \
    wget \
    curl \
    && fc-cache -fv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and assets
COPY . .

# Ensure Windows binary is removed from container
RUN rm -f ffmpeg.exe

# Ensure storage directories exist
RUN mkdir -p uploads output assets/sfx

EXPOSE 5000

# Start production server
CMD ["python", "server.py"]
```

### 8.2 Build & Run Commands
- **Local Test (Docker):**
  ```bash
  docker build -t viral-shorts-studio .
  docker run -p 5000:5000 -v $(pwd)/output:/app/output viral-shorts-studio
  ```
- **Render Deployment Command:**
  - Runtime: `Docker`
  - Instance Type: `Starter` (1 CPU, 2 GB RAM minimum)
  - Health Check Path: `/`

---

## 9. Pre-Deployment Remediation Checklist

Before this repository can be deployed live to a public URL, the following issues must be resolved:

- [ ] **1. OS Hardcoding Removal:**
  - Remove/deactivate the Windows-only `os.startfile(OUTPUT_DIR)` in `server.py` (`/api/open-folder`).
  - Disable automatic browser opening (`webbrowser.open(url)`) when running in production/headless mode.
  - Remove hardcoded Windows paths (`C:\Program Files\nodejs`, `ffmpeg.exe`) in `clipper_core.py`; dynamically detect system binaries via `shutil.which("ffmpeg")` and `shutil.which("node")`.
- [ ] **2. Async Job Handling (Fix Request Timeout):**
  - Implement asynchronous processing for `/api/generate` and `/api/generate-batch`.
  - Store job progress state and return an immediate Job ID to the browser.
  - Implement a polling endpoint (e.g., `GET /api/jobs/:id`) or Server-Sent Events (SSE) so the frontend progress bar updates smoothly without HTTP connection drops.
- [ ] **3. Security & Input Sanitization:**
  - Restrict or disable `/api/check-local` so clients cannot probe paths on the server's filesystem.
  - Implement strict path traversal validation in static and output file serving.
  - Add request rate-limiting and maximum file size verification.
- [ ] **4. Containerization & Dependencies:**
  - Add the Linux `Dockerfile` to the repository root.
  - Ensure system fonts (`fonts-liberation`, `fontconfig`) are installed in the container image.
  - Update `.gitignore` and `git` to ensure the 87MB Windows `ffmpeg.exe` is excluded from cloud deployments.
- [ ] **5. Cloud Storage Integration:**
  - Implement S3/R2 upload functionality so generated videos persist across deployments and container restarts.
- [ ] **6. YouTube Anti-Bot Readiness:**
  - Add optional support for proxy configuration or cookie injection in `yt_dlp` options to mitigate cloud IP blocking.

---

## 10. Recommended Next Steps

1. **Review and approve this audit report.**
2. **Phase 1: Code Remediation (Non-Breaking)**:
   - Make `clipper_core.py` and `server.py` cross-platform (Linux & Windows compatible).
   - Guard desktop-only commands behind an `if sys.platform == "win32"` check so the local Windows launcher continues to function identically.
   - Add the production `Dockerfile` and `.dockerignore`.
3. **Phase 2: Timeout-Resistant Job Handling**:
   - Introduce lightweight background job tracking so requests never time out on public hosts.
4. **Phase 3: Deploy to Render / Railway / Cloud VPS**:
   - Connect repository to hosting provider, configure environment variables, and perform live end-to-end testing with a real video clip.
