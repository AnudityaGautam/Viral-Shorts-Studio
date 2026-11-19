import os
import sys
import json
import urllib.parse
import mimetypes
import traceback
import signal
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import threading
import webbrowser
import clipper_core
import job_manager

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        pass

DEFAULT_PORT = 5000
DEFAULT_HOST = "0.0.0.0"

try:
    PORT = int(os.environ.get("PORT", DEFAULT_PORT))
except ValueError:
    PORT = DEFAULT_PORT

HOST = os.environ.get("HOST", DEFAULT_HOST).strip() or DEFAULT_HOST
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development").strip().lower()
IS_PRODUCTION = ENVIRONMENT in ("production", "prod")
AUTO_OPEN_BROWSER = os.environ.get("OPEN_BROWSER", "auto").strip().lower()
ALLOW_LOCAL_PATH_CHECK = os.environ.get("ALLOW_LOCAL_PATH_CHECK", "").strip().lower() in ("1", "true", "yes")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.environ.get("OUTPUT_DIR") or os.path.join(BASE_DIR, "output")
DATA_DIR = os.environ.get("DATA_DIR") or OUTPUT_DIR
# In production, default uploads to live under the persistent DATA_DIR so they survive restarts
UPLOADS_DIR = os.environ.get("UPLOADS_DIR") or (os.path.join(DATA_DIR, "uploads") if IS_PRODUCTION else os.path.join(BASE_DIR, "uploads"))
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Production Security & Resource Limits
MAX_UPLOAD_SIZE_MB = max(10, int(os.environ.get("MAX_UPLOAD_SIZE_MB", "500")))
MAX_UPLOAD_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
MAX_JSON_BODY_SIZE = max(65536, int(os.environ.get("MAX_JSON_BODY_SIZE", str(2 * 1024 * 1024))))
STUDIO_API_KEY = os.environ.get("STUDIO_API_KEY", "").strip()
CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ALLOWED_ORIGINS", "*").strip() or "*"

# Initialize background job queue manager
MAX_CONCURRENT_RENDERS = max(1, int(os.environ.get("MAX_CONCURRENT_RENDERS", "1")))
job_mgr = job_manager.JobManager(output_dir=OUTPUT_DIR, db_path=os.path.join(DATA_DIR, "jobs.db"), max_concurrency=MAX_CONCURRENT_RENDERS)

def is_safe_path(base_dir, path):
    """
    Ensure the resolved target path is strictly within base_dir to prevent path traversal attacks.
    """
    try:
        base_dir_abs = os.path.abspath(base_dir)
        if os.path.isabs(path) or (sys.platform == 'win32' and len(path) > 1 and path[1] == ':'):
            target_abs = os.path.abspath(path)
        else:
            target_abs = os.path.abspath(os.path.join(base_dir_abs, path))
        return os.path.commonpath([base_dir_abs, target_abs]) == base_dir_abs
    except Exception:
        return False

def is_safe_media_source(target):
    """
    In production, ensure local media paths processed by FFmpeg/yt-dlp are confined to
    the designated uploads or output directories to prevent reading sensitive host files.
    """
    if not IS_PRODUCTION:
        return True
    try:
        resolved = clipper_core.resolve_local_path(target)
        resolved_abs = os.path.abspath(resolved)
        for allowed in (UPLOADS_DIR, OUTPUT_DIR):
            allowed_abs = os.path.abspath(allowed)
            if os.path.commonpath([allowed_abs, resolved_abs]) == allowed_abs:
                return True
        return False
    except Exception:
        return False

class ShortsStudioHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        # Enable CORS and disable aggressive caching for local dev
        self.send_header("Access-Control-Allow-Origin", CORS_ALLOWED_ORIGINS)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Range, X-Filename, X-API-Key, Authorization")
        super().end_headers()

    def is_authorized(self):
        """
        Verify optional API key for protected API endpoints.
        Headers only (X-API-Key or Authorization: Bearer).
        Query parameter tokens are strictly prohibited to prevent secret leakage in access logs.
        """
        if not STUDIO_API_KEY:
            return True
        header_key = self.headers.get("X-API-Key")
        if header_key and header_key == STUDIO_API_KEY:
            return True
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer ") and auth_header[7:].strip() == STUDIO_API_KEY:
            return True
        return False

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_HEAD(self):
        self.do_GET(head_only=True)

    def do_GET(self, head_only=False):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        
        # Route: Health check for Docker / Render / Kubernetes
        if path in ("/healthz", "/api/health"):
            self.send_json_response({
                "status": "healthy",
                "service": "viral-shorts-studio",
                "environment": ENVIRONMENT,
                "workers_running": len(job_mgr.workers),
                "active_jobs": len(job_mgr.running_jobs),
                "timestamp": job_manager.utc_now_iso()
            })
            return

        # Enforce API key authentication if configured
        if path.startswith("/api/") and not self.is_authorized():
            self.send_json_response({"error": "Unauthorized: Invalid or missing API key"}, status=401)
            return

        # Route: Serve root
        if path == "/" or path == "":
            path = "/index.html"

        # API Route: List jobs
        if path in ("/api/jobs", "/api/jobs/"):
            query_params = urllib.parse.parse_qs(parsed.query)
            try:
                limit = int(query_params.get("limit", [50])[0])
            except ValueError:
                limit = 50
            jobs = job_mgr.list_jobs(limit=limit)
            self.send_json_response({"jobs": jobs})
            return

        # API Route: Job status & secure download
        if path.startswith("/api/jobs/"):
            subpath = path[len("/api/jobs/"):].strip("/")
            parts = subpath.split("/")
            job_id = parts[0]
            if len(parts) == 1:
                job = job_mgr.get_job(job_id)
                if not job:
                    self.send_json_response({"error": f"Job not found: {job_id}"}, status=404)
                    return
                self.send_json_response(job)
                return
            elif len(parts) == 2 and parts[1] == "download":
                query_params = urllib.parse.parse_qs(parsed.query)
                req_file = query_params.get("file", [None])[0]
                file_path = job_mgr.get_job_file_path(job_id, req_file)
                if not file_path or not os.path.exists(file_path):
                    self.send_json_response({"error": "Requested output file not found or job not completed"}, status=404)
                    return
                ctype, _ = mimetypes.guess_type(file_path)
                if not ctype:
                    ctype = "video/mp4" if file_path.endswith(".mp4") else ("application/zip" if file_path.endswith(".zip") else "application/octet-stream")
                self.serve_file(file_path, ctype, head_only=head_only)
                return
            else:
                self.send_json_response({"error": "Endpoint not found"}, status=404)
                return
            
        # Route: Serve output videos, thumbnails and zip bundles
        if path.startswith("/output/"):
            rel_file = urllib.parse.unquote(path[len("/output/"):])
            if not is_safe_path(OUTPUT_DIR, rel_file):
                self.send_error(403, "Access Denied: Invalid path")
                return
            file_path = os.path.join(OUTPUT_DIR, rel_file.lstrip("/\\"))
            if os.path.exists(file_path) and os.path.isfile(file_path):
                ctype, _ = mimetypes.guess_type(file_path)
                self.serve_file(file_path, ctype or ("video/mp4" if file_path.endswith(".mp4") else "application/octet-stream"), head_only=head_only)
                return
            else:
                self.send_error(404, "File Not Found")
                return

        # Route: Serve uploaded local videos and assets
        if path.startswith("/uploads/"):
            rel_file = urllib.parse.unquote(path[len("/uploads/"):])
            if not is_safe_path(UPLOADS_DIR, rel_file):
                self.send_error(403, "Access Denied: Invalid path")
                return
            file_path = os.path.join(UPLOADS_DIR, rel_file.lstrip("/\\"))
            if os.path.exists(file_path) and os.path.isfile(file_path):
                ctype, _ = mimetypes.guess_type(file_path)
                self.serve_file(file_path, ctype or ("video/mp4" if file_path.endswith(".mp4") else "application/octet-stream"), head_only=head_only)
                return
            else:
                self.send_error(404, "File Not Found")
                return
                
        # Route: Serve static local files (HTML, CSS, JS, SFX audio assets)
        clean_rel = path.lstrip("/\\")
        
        # Block access to source code, environment files, git repository, or internal directories
        blocked_prefixes = (".git", ".env", "__pycache__", ".dist", ".venv", "venv")
        blocked_extensions = (".py", ".pyc", ".bat", ".sh", ".env", ".md", ".bak", ".dockerignore", ".db", ".sqlite", ".sqlite3")
        _, ext = os.path.splitext(clean_rel.lower())
        
        if any(clean_rel.startswith(bp) for bp in blocked_prefixes) or ext in blocked_extensions or clean_rel == "Dockerfile":
            self.send_error(403, "Access Denied")
            return

        if not is_safe_path(BASE_DIR, clean_rel):
            self.send_error(403, "Access Denied: Invalid path")
            return

        file_path = os.path.join(BASE_DIR, clean_rel)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            ctype, _ = mimetypes.guess_type(file_path)
            self.serve_file(file_path, ctype or "application/octet-stream", head_only=head_only)
            return
            
        self.send_error(404, "File Not Found")

    def serve_file(self, file_path, content_type, head_only=False):
        try:
            file_size = os.path.getsize(file_path)
            
            # Handle HTTP Range requests for video seeking in browser
            range_header = self.headers.get("Range")
            if range_header and content_type.startswith("video/"):
                range_match = range_header.strip().replace("bytes=", "").split("-")
                start = int(range_match[0]) if range_match[0] else 0
                end = int(range_match[1]) if len(range_match) > 1 and range_match[1] else file_size - 1
                length = end - start + 1
                
                self.send_response(206)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Content-Length", str(length))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                
                if not head_only:
                    with open(file_path, "rb") as f:
                        f.seek(start)
                        self.wfile.write(f.read(length))
                return

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(file_size))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            
            if not head_only:
                with open(file_path, "rb") as f:
                    while chunk := f.read(64 * 1024):
                        self.wfile.write(chunk)
        except (ConnectionResetError, BrokenPipeError):
            pass
        except Exception as e:
            print("Error serving file:", e)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_len = int(self.headers.get("Content-Length", 0))

        # Enforce API key authentication if configured
        if parsed.path.startswith("/api/") and not self.is_authorized():
            self.send_json_response({"error": "Unauthorized: Invalid or missing API key"}, status=401)
            return

        # API: Video File Upload (Handles streaming binary or multipart uploads with size limit)
        if parsed.path == "/api/upload":
            if content_len > MAX_UPLOAD_BYTES:
                self.send_json_response({
                    "error": f"Upload rejected: File size ({round(content_len/(1024*1024), 1)} MB) exceeds maximum allowed limit of {MAX_UPLOAD_SIZE_MB} MB."
                }, status=413)
                return

            raw_filename = self.headers.get("X-Filename") or ""
            if raw_filename:
                raw_filename = urllib.parse.unquote(raw_filename)
            else:
                raw_filename = "uploaded_video.mp4"
                
            # Clean filename and guard against path traversal
            safe_name = os.path.basename(raw_filename)
            safe_name = "".join(c for c in safe_name if c.isalnum() or c in "._- ")
            if not safe_name:
                safe_name = "uploaded_video.mp4"

            if not is_safe_path(UPLOADS_DIR, safe_name):
                self.send_json_response({"error": "Invalid upload filename"}, status=400)
                return
                
            dest_path = os.path.join(UPLOADS_DIR, safe_name)
            
            try:
                print(f"[Studio] Receiving uploaded file: {safe_name} ({round(content_len / (1024*1024), 2)} MB)...")
                bytes_left = content_len
                total_written = 0
                with open(dest_path, "wb") as out_f:
                    while bytes_left > 0:
                        chunk_size = min(65536, bytes_left)
                        chunk = self.rfile.read(chunk_size)
                        if not chunk:
                            break
                        out_f.write(chunk)
                        bytes_left -= len(chunk)
                        total_written += len(chunk)
                        if total_written > MAX_UPLOAD_BYTES:
                            raise ValueError(f"Uploaded file exceeded maximum limit of {MAX_UPLOAD_SIZE_MB} MB")
                        
                file_size = os.path.getsize(dest_path)
                print(f"[Studio] File uploaded successfully: {dest_path} ({round(file_size/(1024*1024), 2)} MB)")
                
                # Extract basic info & thumbnail immediately
                info = clipper_core.get_local_video_info(dest_path)
                self.send_json_response({
                    "status": "success",
                    "filename": safe_name,
                    "file_path": dest_path,
                    "file_url": f"/uploads/{safe_name}",
                    "file_size": file_size,
                    "file_size_mb": info.get("file_size_mb"),
                    "duration": info.get("duration"),
                    "duration_fmt": clipper_core.format_time(info.get("duration", 0)),
                    "thumbnail": info.get("thumbnail_url", ""),
                    "title": info.get("title")
                })
            except Exception as e:
                print(f"[Studio] File upload error: {e}")
                if os.path.exists(dest_path):
                    try:
                        os.remove(dest_path)
                    except Exception:
                        pass
                self.send_json_response({"error": str(e)}, status=413 if "exceeded maximum limit" in str(e) else 500)
            return

        # Enforce maximum JSON payload size to prevent memory exhaustion
        if content_len > MAX_JSON_BODY_SIZE:
            self.send_json_response({
                "error": f"Request body too large ({content_len} bytes). Maximum allowed JSON payload is {MAX_JSON_BODY_SIZE} bytes."
            }, status=413)
            return

        # Read JSON body for standard endpoints
        post_data = self.rfile.read(content_len) if content_len > 0 else b"{}"
        try:
            body = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            body = {}

        # API: Create background video processing job
        if parsed.path in ("/api/jobs", "/api/jobs/"):
            job_type = body.get("type") or body.get("job_type") or "single"
            target = (body.get("url") or body.get("file_path") or "").strip()
            params = body.get("params") or {}
            
            # Merge any top-level parameters into params
            for k, v in body.items():
                if k not in ("type", "job_type", "url", "file_path", "params"):
                    if k not in params:
                        params[k] = v
                        
            if not target and ("url" in params or "file_path" in params):
                target = (params.get("url") or params.get("file_path") or "").strip()
                
            if not target:
                self.send_json_response({"error": "Video URL or file required"}, status=400)
                return
                
            if clipper_core.is_local_path(target) and not is_safe_media_source(target):
                self.send_json_response({"error": "Access to specified local file is restricted in production. Please upload via the upload interface."}, status=403)
                return
                
            if job_type == "batch":
                clips = params.get("clips") or body.get("clips") or []
                if not clips:
                    self.send_json_response({"error": "Batch job requires at least 1 clip in 'clips' list"}, status=400)
                    return
                params["clips"] = clips
                
            try:
                job = job_mgr.create_job(job_type, target, params)
                self.send_json_response({
                    "status": "queued",
                    "job_id": job["id"],
                    "job": job
                }, status=202)
            except Exception as e:
                self.send_json_response({"error": f"Failed to enqueue job: {str(e)}"}, status=500)
            return

        # API: Cancel background job
        if parsed.path.startswith("/api/jobs/") and parsed.path.endswith("/cancel"):
            subpath = parsed.path[len("/api/jobs/"):].strip("/")
            parts = subpath.split("/")
            if len(parts) == 2 and parts[1] == "cancel":
                job_id = parts[0]
                success = job_mgr.cancel_job(job_id)
                job = job_mgr.get_job(job_id)
                if not job:
                    self.send_json_response({"error": f"Job not found: {job_id}"}, status=404)
                    return
                if success:
                    status_str = "cancelled" if job.get("status") == "cancelled" else "cancelling"
                    msg = "Job cancelled" if status_str == "cancelled" else "Job cancellation requested"
                    self.send_json_response({"status": status_str, "message": msg, "job": job})
                    return
                else:
                    self.send_json_response({
                        "status": "ignored",
                        "message": f"Job is in state '{job.get('status')}' and cannot be cancelled",
                        "job": job
                    })
                    return

        # API: Check Local Path (Instant PC path validation without upload)
        if parsed.path == "/api/check-local":
            if IS_PRODUCTION and not ALLOW_LOCAL_PATH_CHECK:
                self.send_json_response({
                    "error": "Local filesystem path probing is disabled in production for security. Please upload the video file via the upload tab instead."
                }, status=403)
                return

            path_input = (body.get("path") or "").strip().strip('"').strip("'")
            if not path_input:
                self.send_json_response({"error": "No file path provided"}, status=400)
                return
            try:
                abs_path = clipper_core.resolve_local_path(path_input)
                if not os.path.exists(abs_path) or not os.path.isfile(abs_path):
                    self.send_json_response({"error": f"File not found: {path_input}"}, status=404)
                    return
                if not is_safe_media_source(abs_path):
                    self.send_json_response({"error": "Access to specified file path is restricted in production."}, status=403)
                    return
                info = clipper_core.get_local_video_info(abs_path)
                self.send_json_response({
                    "status": "success",
                    "file_path": abs_path,
                    "filename": info.get("filename"),
                    "title": info.get("title"),
                    "duration": info.get("duration"),
                    "duration_fmt": clipper_core.format_time(info.get("duration", 0)),
                    "file_size_mb": info.get("file_size_mb"),
                    "thumbnail": info.get("thumbnail_url")
                })
            except Exception as e:
                self.send_json_response({"error": str(e)}, status=500)
            return

        # API: Analyze Video & Detect Viral Moments (Works for both YouTube URLs and Local Videos)
        if parsed.path == "/api/analyze":
            target = (body.get("url") or body.get("file_path") or "").strip()
            target_duration = float(body.get("target_duration", 35))
            min_moments = int(body.get("min_moments", 5))
            if not target:
                self.send_json_response({"error": "No YouTube URL or file provided"}, status=400)
                return
            try:
                if clipper_core.is_local_path(target):
                    if not is_safe_media_source(target):
                        self.send_json_response({"error": "Access to specified local file is restricted in production. Please upload via the upload interface."}, status=403)
                        return
                    print(f"[Studio] Analyzing Local Video File: {target} (Target Dur: {target_duration}s, Min: {min_moments} clips)")
                    result = clipper_core.analyze_local_video(target, target_duration=target_duration, min_moments=min_moments)
                else:
                    print(f"[Studio] Analyzing YouTube video: {target} (Target Dur: {target_duration}s, Min: {min_moments} clips)")
                    result = clipper_core.analyze_video(target, target_duration=target_duration, min_moments=min_moments)
                self.send_json_response(result)
            except Exception as e:
                print(f"[Studio] Analysis error: {e}")
                self.send_json_response({"error": str(e)}, status=500)
            return

        # API: Generate Single 9:16 Short (Works for both YouTube URLs and Local Videos)
        elif parsed.path == "/api/generate":
            url = (body.get("url") or body.get("file_path") or "").strip()
            start_time = body.get("start_time", "0:00")
            end_time = body.get("end_time", "0:35")
            layout = body.get("layout", "blur")
            subtitle_style = body.get("subtitle_style", "3d_hormozi")
            top_hook = body.get("top_hook", "WAIT TILL THE END 😱")
            header_lines = body.get("header_lines")
            sfx_enabled = bool(body.get("sfx_enabled", True))
            sfx_hook = body.get("sfx_hook", "vine_boom")
            dynamic_zoom = bool(body.get("dynamic_zoom", True))
            high_quality = bool(body.get("high_quality", True))
            copyright_shield = bool(body.get("copyright_shield", True))
            custom_title = body.get("title") or body.get("custom_title")
            
            if not url:
                self.send_json_response({"error": "Video URL or file required"}, status=400)
                return

            if clipper_core.is_local_path(url) and not is_safe_media_source(url):
                self.send_json_response({"error": "Access to specified local file is restricted in production. Please upload via the upload interface."}, status=403)
                return

            # Support asynchronous queueing via async flag or header
            if body.get("async") or self.headers.get("X-Async") == "1":
                job = job_mgr.create_job("single", url, body)
                self.send_json_response({"status": "queued", "job_id": job["id"], "job": job}, status=202)
                return
                
            try:
                print(f"[Studio] Generating 9:16 Short for {url} ({start_time} -> {end_time}) [3D Style: {subtitle_style}, SFX: {sfx_hook if sfx_enabled else 'Off'}, Zoom: {dynamic_zoom}]")
                result = clipper_core.generate_short(
                    url=url,
                    start_time=start_time,
                    end_time=end_time,
                    layout=layout,
                    subtitle_style=subtitle_style,
                    top_hook=top_hook,
                    header_lines=header_lines,
                    sfx_enabled=sfx_enabled,
                    sfx_hook=sfx_hook,
                    dynamic_zoom=dynamic_zoom,
                    high_quality=high_quality,
                    copyright_shield=copyright_shield,
                    output_dir=OUTPUT_DIR,
                    custom_title=custom_title
                )
                result["download_url"] = f"/output/{result['video_filename']}"
                self.send_json_response(result)
            except Exception as e:
                print(f"[Studio] Generation error: {e}")
                self.send_json_response({"error": str(e)}, status=500)
            return

        # API: Batch Generate Multiple (4-5+) 9:16 Shorts (Works for both YouTube URLs and Local Videos)
        elif parsed.path == "/api/generate-batch":
            url = (body.get("url") or body.get("file_path") or "").strip()
            clips = body.get("clips", [])
            layout = body.get("layout", "blur")
            subtitle_style = body.get("subtitle_style", "3d_hormozi")
            header_lines = body.get("header_lines")
            sfx_enabled = bool(body.get("sfx_enabled", True))
            sfx_hook = body.get("sfx_hook", "vine_boom")
            dynamic_zoom = bool(body.get("dynamic_zoom", True))
            high_quality = bool(body.get("high_quality", True))
            copyright_shield = bool(body.get("copyright_shield", True))
            
            if not url or not clips:
                self.send_json_response({"error": "Video URL/file and at least 1 clip required"}, status=400)
                return

            if clipper_core.is_local_path(url) and not is_safe_media_source(url):
                self.send_json_response({"error": "Access to specified local file is restricted in production. Please upload via the upload interface."}, status=403)
                return

            # Support asynchronous queueing via async flag or header
            if body.get("async") or self.headers.get("X-Async") == "1":
                job = job_mgr.create_job("batch", url, body)
                self.send_json_response({"status": "queued", "job_id": job["id"], "job": job}, status=202)
                return
                
            try:
                print(f"[Studio] Batch Generating {len(clips)} Shorts for {url} (Layout: {layout}, 3D Style: {subtitle_style}, SFX: {sfx_hook if sfx_enabled else 'Off'})")
                result = clipper_core.generate_shorts_batch(
                    url=url,
                    clips=clips,
                    layout=layout,
                    subtitle_style=subtitle_style,
                    header_lines=header_lines,
                    sfx_enabled=sfx_enabled,
                    sfx_hook=sfx_hook,
                    dynamic_zoom=dynamic_zoom,
                    high_quality=high_quality,
                    copyright_shield=copyright_shield,
                    output_dir=OUTPUT_DIR
                )
                self.send_json_response(result)
            except Exception as e:
                print(f"[Studio] Batch generation error: {e}")
                self.send_json_response({"error": str(e)}, status=500)
            return

        # API: Open Output Folder (Desktop Windows File Explorer only)
        elif parsed.path == "/api/open-folder":
            if sys.platform == "win32" and hasattr(os, "startfile") and not IS_PRODUCTION:
                try:
                    os.startfile(OUTPUT_DIR)
                    self.send_json_response({"status": "opened", "platform": "win32"})
                except Exception as e:
                    self.send_json_response({"status": "error", "message": str(e)}, status=200)
            else:
                self.send_json_response({
                    "status": "unsupported",
                    "message": "Direct folder exploration is only available in local desktop mode. Use download links in the browser."
                }, status=200)
            return

        self.send_error(404, "Endpoint Not Found")


    def send_json_response(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

class ExclusiveThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True

def should_open_browser():
    if IS_PRODUCTION:
        return False
    if AUTO_OPEN_BROWSER in ("0", "false", "no", "off"):
        return False
    if AUTO_OPEN_BROWSER in ("1", "true", "yes", "on"):
        return True
    return sys.platform == "win32"

def open_browser_delayed(url):
    import time
    time.sleep(0.8)
    if should_open_browser():
        try:
            webbrowser.open(url)
        except Exception:
            pass

def run(host=HOST, port=PORT):
    server_address = (host, port)
    httpd = None

    def shutdown_handler(signum=None, frame=None):
        print(f"\n[Studio] Stopping background job queue workers...")
        try:
            job_mgr.stop()
        except Exception:
            pass
        if httpd:
            try:
                httpd.server_close()
            except Exception:
                pass
        if signum is not None:
            sys.exit(0)

    try:
        signal.signal(signal.SIGTERM, shutdown_handler)
        signal.signal(signal.SIGINT, shutdown_handler)
    except Exception:
        pass

    try:
        httpd = ExclusiveThreadingHTTPServer(server_address, ShortsStudioHandler)
        display_host = "localhost" if host in ("0.0.0.0", "") else host
        url = f"http://{display_host}:{port}"
        print(f"==================================================")
        print(f"  [+] VIRAL SHORTS STUDIO RUNNING")
        print(f"  [>] Bound to: {host}:{port}")
        print(f"  [>] Access URL: {url}")
        print(f"  [>] Environment: {ENVIRONMENT.upper()}")
        print(f"  [>] Workers: {MAX_CONCURRENT_RENDERS} rendering worker(s)")
        print(f"==================================================")
        if should_open_browser():
            threading.Thread(target=open_browser_delayed, args=(url,), daemon=True).start()
        httpd.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        shutdown_handler()
    except OSError as e:
        if not IS_PRODUCTION and port < (PORT + 10):
            print(f"Port {port} busy, trying {port + 1}...")
            run(host, port + 1)
        else:
            raise e
    finally:
        shutdown_handler()

if __name__ == "__main__":
    run()

