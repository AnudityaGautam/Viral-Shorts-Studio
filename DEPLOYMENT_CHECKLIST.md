# Production Deployment Checklist: Viral Shorts Studio

**Target Platform:** Render Docker Web Service  
**Engine:** Python 3.11 / FFmpeg Hardware-Accelerated Filtergraph / Faster-Whisper CPU int8  
**Architecture:** Single-Container Persistent SQLite Background Worker Engine  

---

## 1. Pre-Deployment Configuration Checklist

| Area | Item | Verified | Status / Notes |
|---|---|---|---|
| **Runtime** | Python 3.11 Slim Debian Bookworm Base | [x] | Defined in `Dockerfile` line 5 |
| **System Tools** | FFmpeg with `libass` subtitle burn-in | [x] | `apt-get install -y ffmpeg libass9 libass-dev` in `Dockerfile` |
| **JS Decryption** | Node.js installed for yt-dlp signatures | [x] | `nodejs` included in `Dockerfile` package manifest |
| **Font Rendering**| Subtitle fonts (`DejaVu Sans`, `Liberation`) | [x] | Font aliases for `Impact` and `Arial Black` verified in fontconfig |
| **Model Caching** | Faster-Whisper `tiny` pre-downloaded | [x] | Baked into Docker image to eliminate first-render cold-start delay |
| **Security User** | Non-root `appuser` (UID 1000) execution | [x] | Runs under non-root user; owns `/app` and `/home/appuser/.cache` |
| **Health Check** | Dedicated `/api/health` and `/healthz` | [x] | Returns JSON status `200` without static file or disk overhead |
| **Persistence** | SQLite `jobs.db` on persistent disk | [x] | Configured via `DATA_DIR=/app/output` |
| **Concurrency** | `MAX_CONCURRENT_RENDERS=1` | [x] | Prevents CPU starvation and OOM-kill on cloud containers |
| **Crash Recovery**| Startup interrupted job recovery | [x] | Recovers interrupted jobs on container restart |
| **Cancellation** | Active subprocess termination | [x] | `proc.terminate()` kills FFmpeg process immediately on cancel |
| **Upload Limits** | `MAX_UPLOAD_SIZE_MB=500` | [x] | Rejects files > 500MB with `HTTP 413 Payload Too Large` |
| **JSON Limits** | `MAX_JSON_BODY_SIZE=2MB` | [x] | Rejects oversized JSON request bodies with `HTTP 413` |
| **Path Security** | Path traversal shields & DB blocking | [x] | Blocks `.db`, `.sqlite`, `.py`, `.env` and rejects traversal attempts |
| **Optional Auth** | `STUDIO_API_KEY` header/query validation | [x] | Built-in token gate for public deployments |

---

## 2. Platform & Infrastructure Requirements (Render)

- [ ] **Render Blueprint Deployment:** Deploy using the provided [render.yaml](file:///c:/Users/Anuditya%20Gautam/OneDrive/Documents/TOOLS/ClippingVideos/render.yaml).
- [ ] **Instance Tier:** Select **Starter** (512MB RAM minimum for light use) or **Standard** (2GB RAM recommended for full-resolution batch renders).
- [ ] **Instance Count:** Keep `numInstances: 1`. *Never scale horizontally across multiple instances when using local SQLite and persistent disks.*
- [ ] **Persistent Disk Mount:** Verify disk `shorts-studio-data` (10 GB) is mounted at `/app/output`.
- [ ] **Health Check URL:** Ensure health check path is configured to `/api/health` with a 15-second grace period.
- [ ] **Proxy Configuration:** If deploying in cloud regions where YouTube blocks datacenter IPs, configure `YTDLP_PROXY` in Render dashboard environment settings.

---

## 3. Post-Deployment Smoke Test Protocol

After pushing to Render, execute these verification checks in order:

1. **Service Liveness:**
   ```bash
   curl -I https://<your-render-app>.onrender.com/api/health
   # Expected: HTTP/1.1 200 OK
   # Content-Type: application/json
   # {"status": "healthy", "service": "viral-shorts-studio", ...}
   ```
2. **Web Interface Load:**
   - Open `https://<your-render-app>.onrender.com/` in browser.
   - Verify glassmorphic interface renders, fonts display cleanly, and SFX test audio plays.
3. **Upload Tab Verification:**
   - Upload a small MP4 video (10–30 MB).
   - Verify upload progress bar updates and thumbnail generates.
4. **Single Short Generation:**
   - Click "🎯 Generate Selected Single Short Only".
   - Verify UI switches to progress card, shows real percentages (`15%`, `40%`, `65%`, `95%`), and elapsed time.
   - Verify video player displays the 9:16 vertical render upon completion.
5. **Download Verification:**
   - Click "⬇️ Download Active Short". Verify MP4 file downloads properly.
6. **Cancellation Verification:**
   - Start a render and click "✖ Cancel Job".
   - Verify job halts immediately and status changes to `Cancelled`.
7. **Restart & Recovery Check:**
   - Trigger a manual deploy or restart on Render while a job is running.
   - Check `GET /api/jobs`. Verify previous interrupted job is marked as `failed` with `"Job was interrupted by server restart"`.
