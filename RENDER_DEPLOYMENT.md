# Render Production Deployment Guide: Viral Shorts Studio

**Application:** Viral Shorts Studio (AI Clipping Tool)  
**Host:** Render Cloud Platform (https://render.com)  
**Deployment Type:** Docker Web Service with Attached Persistent Disk  
**Blueprint File:** [render.yaml](file:///c:/Users/Anuditya%20Gautam/OneDrive/Documents/TOOLS/ClippingVideos/render.yaml)  

---

## 1. Architectural Evaluation: Background Worker on Render

### The Core Architectural Question
Can the existing SQLite-backed persistent queue run across two separate Render services (e.g. Web Service + Background Worker Service)?

### The DevOps Finding
**NO. Deploying as two separate Render services with the current SQLite architecture is strictly NOT recommended and will fail in production.**

### Technical Explanation
1. **Render Persistent Disk Isolation:**
   Render disks can only be attached to **a single service at a time**. Render does not support shared network block storage (NFS / EFS / Ceph) across multiple containers.
2. **SQLite Locking Limitations:**
   SQLite is an in-process, file-locking database. If two independent containers attempt to access the same SQLite database file across network mounts, database corruption or permanent deadlocks occur.
3. **Media File Isolation:**
   If Service A (Web) receives a video upload, that video is stored on Service A's local disk. Service B (Worker) running in a separate container has no access to Service A's filesystem.

### The Production Solution: Single-Container In-Process Worker Architecture
Instead of splitting into two services, we deploy the system as **one Render Docker Web Service** where:
- The HTTP server (`server.py`) handles incoming web traffic and API routes.
- The background worker thread pool (`job_manager.py`) runs in the same container.
- Both share the mounted Persistent Disk (`/app/output`), where `jobs.db`, uploaded files, and rendered MP4 clips reside.
- Rendering requests return immediately (`HTTP 202 Accepted`), and the client polls progress asynchronously every 2 seconds. This completely eliminates Render's 100-second HTTP gateway timeout while avoiding cross-container storage synchronization complexities.

---

## 2. Step-by-Step Deployment Instructions

### Method A: Deploy via Blueprint (Recommended)
1. Commit all files (including `Dockerfile`, `render.yaml`, `server.py`, `job_manager.py`, and `clipper_core.py`) to your GitHub or GitLab repository.
2. Log in to the [Render Dashboard](https://dashboard.render.com).
3. Click **New +** -> **Blueprint**.
4. Connect your repository.
5. Render will automatically parse `render.yaml`, detect the Docker service, configure the 10GB persistent disk, and stage environment variables.
6. Click **Apply**.

---

### Method B: Manual Dashboard Setup
If deploying manually without Blueprint:
1. Click **New +** -> **Web Service**.
2. Connect your Git repository.
3. Select runtime: **Docker**.
4. Set Dockerfile Path: `./Dockerfile`.
5. Under **Instance Type**, select:
   - **Starter** (512MB RAM, 1 CPU) — Minimum ($7/mo).
   - **Standard** (2GB RAM, 1 CPU) — Recommended ($25/mo) for fast rendering.
6. Under **Advanced Settings**:
   - Add **Persistent Disk**:
     - Name: `shorts-studio-data`
     - Mount Path: `/app/output`
     - Size: `10 GB` (or larger)
   - Add **Health Check Path**: `/api/health`
7. Add Environment Variables (see Section 3).
8. Click **Create Web Service**.

---

## 3. Environment Variables Reference

| Variable | Recommended Production Value | Description |
|---|---|---|
| `ENVIRONMENT` | `production` | Enforces production security rules (disables path probing). |
| `HOST` | `0.0.0.0` | Binds server to all network interfaces inside container. |
| `PORT` | `5000` | Port container listens on (Render automatically maps this). |
| `OPEN_BROWSER` | `0` | Disables desktop browser popup on server launch. |
| `ALLOW_LOCAL_PATH_CHECK` | `0` | Blocks local server filesystem traversal attempts. |
| `DATA_DIR` | `/app/output` | Directory where `jobs.db` and rendered outputs reside. |
| `MAX_CONCURRENT_RENDERS` | `1` | Renders 1 video at a time to prevent CPU/memory exhaustion. |
| `JOB_RETENTION_HOURS` | `72` | Automatically purges completed/failed jobs older than 72h. |
| `MAX_UPLOAD_SIZE_MB` | `500` | Rejects uploads larger than 500MB with `HTTP 413`. |
| `WHISPER_MODEL` | `tiny` | Fastest speech recognition model (~75MB, CPU optimized). |
| `WHISPER_DEVICE` | `cpu` | Uses CPU for AI speech transcription. |
| `WHISPER_COMPUTE_TYPE` | `int8` | 8-bit quantized integer execution for lowest RAM usage. |
| `STUDIO_API_KEY` | *(Optional Secret)* | If set, requires `X-API-Key` on `/api/` endpoints. |
| `YTDLP_PROXY` | *(Optional Secret)* | HTTP/SOCKS5 proxy for YouTube video downloads. |
| `YTDLP_COOKIES_FILE` | *(Optional Path)* | Path to exported YouTube `cookies.txt` file. |

---

## 4. Resource Sizing & Capacity Planning

| Metric | Render Free Tier (Do Not Use) | Render Starter ($7/mo) | Render Standard ($25/mo) [Recommended] |
|---|---|---|---|
| **RAM** | 512 MB | 512 MB | 2 GB |
| **CPU** | 0.1 vCPU shared | 0.5 vCPU shared | 1 vCPU dedicated |
| **Idle Spin-Down** | Spins down after 15 min (aborts jobs!) | Never spins down | Never spins down |
| **Persistent Disk** | Not supported | Supported ($1/mo for 10GB) | Supported ($1/mo for 10GB) |
| **Whisper Run Time** | ~12–20s | ~4–8s | ~2–4s |
| **FFmpeg 35s Render** | ~90–180s (high OOM risk) | ~35–60s | ~18–30s |
| **Batch 5 Clips** | Aborts / OOM-killed | ~3.5–5 min | ~1.5–2.5 min |
| **Production Verdict**| **UNSUITABLE** | **ACCEPTABLE (Single Renders)** | **OPTIMAL (Production)** |

---

## 5. Mitigating YouTube Cloud IP Blocks

When running on major cloud hosting providers (Render, AWS, GCP, DigitalOcean), YouTube's bot detection system occasionally flags requests with `HTTP 429` or `"Sign in to confirm you're not a bot"`.

### Strategies:
1. **Primary Recommended Workflow: Direct Video Upload**
   The studio includes a full file upload tab (`/api/upload`) supporting drag-and-drop and binary streaming up to 500MB. Uploading a video bypasses YouTube entirely and runs with 100% reliability.
2. **Residential Proxy (`YTDLP_PROXY`):**
   If YouTube URL clipping is critical in production, configure a residential proxy service (e.g. BrightData, Webshare, Oxylabs) by setting:
   ```
   YTDLP_PROXY=http://user:pass@proxy.example.com:8080
   ```
3. **Exported Cookies File (`YTDLP_COOKIES_FILE`):**
   Export your browser YouTube cookies using an extension ("Get cookies.txt locally") and upload to the persistent disk at `/app/output/cookies.txt`, then set `YTDLP_COOKIES_FILE=/app/output/cookies.txt`.

---

## 6. Troubleshooting & Operational Commands

### Check Live Health
```bash
curl https://<app-name>.onrender.com/api/health
```

### Inspect Container Logs
In the Render Dashboard, navigate to **Logs** to view:
- Background worker startup messages: `[JobQueue] Started 1 background rendering worker(s).`
- Job enqueuing: `[JobQueue] Enqueued single job: <uuid>`
- FFmpeg encoding progress: `[Worker] Starting single job <uuid>...`
- Auto-recovery notices: `[JobQueue] Recovered X interrupted job(s) from previous run.`
