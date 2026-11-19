# Production Security Audit & Vulnerability Assessment: Viral Shorts Studio

**Application:** Viral Shorts Studio  
**Audit Phase:** Phase 3 — Production Deployment Preparation  
**Auditor:** Senior DevOps & Application Security Engineer  

---

## 1. Executive Security Summary

A comprehensive security audit of the Viral Shorts Studio codebase was performed across authentication, authorization, filesystem isolation, network exposure, request sizing, and process execution vectors.

The application has been hardened against common cloud deployment attack vectors:
- Path traversal attacks are systematically blocked across static file serving, local video resolution, and output file downloads.
- Upload sizing limits (500MB) and JSON body caps (2MB) prevent disk exhaustion and memory exhaustion (OOM) Denial-of-Service attacks.
- Sensitive files (`.env`, `jobs.db`, source code, git metadata) are blocked from HTTP static retrieval.
- Internal server filesystem paths (`C:\...` or `/app/...`) are redacted from all user-facing JSON responses.

---

## 2. Threat Vector Analysis & Hardening Status

### 2.1 Authentication & Authorization
- **Current State:** The application is architecturally designed as a single-tenant studio tool. In its default state, any visitor to the public URL can submit rendering jobs, view existing jobs via `GET /api/jobs`, or trigger cancellations.
- **Implemented Mitigation:** Added optional **`STUDIO_API_KEY`** support in [server.py](file:///c:/Users/Anuditya%20Gautam/OneDrive/Documents/TOOLS/ClippingVideos/server.py).
  - When `STUDIO_API_KEY` is set in environment variables, all `/api/` endpoints (except `/api/health` and `/healthz`) enforce `HTTP 401 Unauthorized` unless a valid `X-API-Key: <token>` header or `?api_key=<token>` query parameter is supplied.
  - If deploying as a completely public web service without an API key, we recommend placing Cloudflare Access, basic HTTP auth, or an authentication proxy (such as OAuth2 Proxy or Render Private Services) in front of the application.

### 2.2 Upload Sizing & Denial-of-Service (DoS) Protection
- **Vulnerability Identified:** Previously, `/api/upload` accepted arbitrary streaming binary uploads without enforcing an upper bound on `Content-Length` or total bytes written to disk, creating a vulnerability where an attacker could flood the server disk with 100GB of garbage data.
- **Implemented Fix:**
  - Configured `MAX_UPLOAD_SIZE_MB = 500` (configurable via environment variable).
  - Pre-flight check rejects requests with `Content-Length > MAX_UPLOAD_BYTES` immediately with `HTTP 413 Payload Too Large`.
  - In-flight check tracks bytes written and terminates the stream, deleting the partial file if `MAX_UPLOAD_BYTES` is exceeded.
  - JSON requests are capped at `MAX_JSON_BODY_SIZE = 2 MB` to prevent in-memory buffer exhaustion.

### 2.3 Path Traversal & Arbitrary File Access
- **Defenses Evaluated:**
  - `is_safe_path(base_dir, path)` uses `os.path.commonpath([base_dir_abs, target_abs]) == base_dir_abs` to ensure requested paths cannot escape `BASE_DIR`, `UPLOADS_DIR`, or `OUTPUT_DIR`.
  - `is_safe_media_source(target)` restricts FFmpeg media cutting in production strictly to files residing inside `UPLOADS_DIR` or `OUTPUT_DIR`.
  - Static file handler explicitly blocks:
    - Blocked prefixes: `.git`, `.env`, `__pycache__`, `.dist`, `.venv`, `venv`
    - Blocked extensions: `.py`, `.pyc`, `.bat`, `.sh`, `.env`, `.md`, `.bak`, `.dockerignore`, `.db`, `.sqlite`, `.sqlite3`
  - Automated test `test_05_download_file_endpoint_security` and `test_06_database_file_protection` passed.

### 2.4 Internal Path Redaction (Information Disclosure)
- **Defenses Evaluated:**
  - In [job_manager.py](file:///c:/Users/Anuditya%20Gautam/OneDrive/Documents/TOOLS/ClippingVideos/job_manager.py), `_format_job_row` redacts absolute filesystem paths from `params["file_path"]` and `input_ref` down to bare filenames (e.g. `interview.mp4` instead of `/app/uploads/interview.mp4`).
  - Output records expose clean download URLs (`/output/clip.mp4` and `/api/jobs/{id}/download?file=clip.mp4`) rather than host filesystem paths.

### 2.5 Public Download Security & Object Enumeration
- **Defenses Evaluated:**
  - `GET /api/jobs/{job_id}/download?file=...` uses `job_mgr.get_job_file_path(job_id, filename)`:
    - Looks up the job record by UUID.
    - Ensures the job status is `completed`.
    - Cross-references the requested filename against the registered `video_filename` entries in `outputs` or the job's `zip_filename`.
    - If a user requests a file produced by another job, or an arbitrary server file (e.g. `/etc/passwd` or `jobs.db`), the endpoint returns `HTTP 404 Not Found`.

### 2.6 Subprocess Execution & Command Injection
- **Defenses Evaluated:**
  - Subprocess commands for `FFMPEG` and `yt-dlp` in [clipper_core.py](file:///c:/Users/Anuditya%20Gautam/OneDrive/Documents/TOOLS/ClippingVideos/clipper_core.py) are passed as argument arrays (`list`), never as raw strings through `shell=True`.
  - Process execution uses `run_cancellable_subprocess` which actively checks for cancellation and calls `proc.terminate()` / `proc.kill()` immediately when requested, preventing zombie processes.

---

## 3. Residual Risks & Production Recommendations

| Risk | Severity | Description | Recommended Remediation |
|---|---|---|---|
| **Public Multi-User Access** | Medium | No per-user job isolation; anyone who lists `/api/jobs` can see active rendering tasks. | Enable `STUDIO_API_KEY` for private access, or implement session-based authentication in a future phase. |
| **API Rate Limiting** | Low-Medium | In-process queue serializes work, but queue depth could be flooded by malicious bots. | Place a Cloudflare proxy or Render DDoS/WAF rule in front of the public URL. |
| **YouTube Cloud IP Challenges** | Low (Operational) | Cloud provider datacenter IPs are often blocked by YouTube. | Advise users to use the direct Video Upload tab, or configure `YTDLP_PROXY` with a residential proxy. |
