import os
import sys
import json
import time
import sqlite3
import uuid
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import clipper_core

def utc_now_iso():
    """Return ISO format UTC timestamp string without deprecation warnings."""
    return datetime.now(timezone.utc).isoformat()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
DATA_DIR = os.environ.get("DATA_DIR", OUTPUT_DIR)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "jobs.db")
MAX_CONCURRENT_RENDERS = max(1, int(os.environ.get("MAX_CONCURRENT_RENDERS", "1")))
JOB_RETENTION_HOURS = int(os.environ.get("JOB_RETENTION_HOURS", "72"))

class JobManager:
    def __init__(self, db_path=DB_PATH, max_concurrency=MAX_CONCURRENT_RENDERS, output_dir=OUTPUT_DIR, start_workers=True):
        self.db_path = db_path
        self.max_concurrency = max_concurrency
        self.output_dir = output_dir
        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)
        self.cancel_requested = set()
        self.running_jobs = set()
        self.stop_event = threading.Event()
        self.workers = []
        self._shared_conn = None
        
        self._init_db()
        self._recover_interrupted_jobs()
        self._prune_expired_jobs()
        if start_workers:
            self._start_workers()

    @contextmanager
    def get_conn(self):
        """Thread-safe context manager for SQLite connections."""
        if self.db_path == ":memory:":
            if self._shared_conn is None:
                self._shared_conn = sqlite3.connect(":memory:", timeout=30.0, check_same_thread=False)
                self._shared_conn.row_factory = sqlite3.Row
            with self.lock:
                yield self._shared_conn
                self._shared_conn.commit()
            return

        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA busy_timeout = 30000;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        """Initialize the SQLite jobs schema."""
        with self.get_conn() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                job_type TEXT NOT NULL,
                status TEXT NOT NULL,
                input_ref TEXT NOT NULL,
                params TEXT NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0,
                stage TEXT NOT NULL DEFAULT 'Queued',
                error_message TEXT,
                outputs TEXT,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status_created ON jobs(status, created_at);")

    def _recover_interrupted_jobs(self):
        """Mark any jobs that were actively processing when the server stopped as failed."""
        now_iso = utc_now_iso()
        with self.get_conn() as conn:
            cur = conn.execute("""
                UPDATE jobs
                SET status = 'failed',
                    stage = 'Interrupted',
                    error_message = 'Job was interrupted by server restart',
                    completed_at = ?
                WHERE status = 'processing';
            """, (now_iso,))
            recovered = cur.rowcount
            if recovered > 0:
                print(f"[JobQueue] Recovered {recovered} interrupted job(s) from previous run.")

    def _prune_expired_jobs(self):
        """Prune old jobs older than JOB_RETENTION_HOURS."""
        if JOB_RETENTION_HOURS <= 0:
            return
        cutoff = time.time() - (JOB_RETENTION_HOURS * 3600)
        cutoff_iso = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()
        try:
            with self.get_conn() as conn:
                conn.execute("""
                    DELETE FROM jobs
                    WHERE status IN ('completed', 'failed', 'cancelled')
                      AND created_at < ?;
                """, (cutoff_iso,))
        except Exception as e:
            print(f"[JobQueue] Job pruning notice: {e}")

    def _start_workers(self):
        """Spawn background worker daemon threads."""
        for i in range(self.max_concurrency):
            t = threading.Thread(target=self._worker_loop, name=f"VideoWorker-{i+1}", daemon=True)
            self.workers.append(t)
            t.start()
        print(f"[JobQueue] Started {self.max_concurrency} background rendering worker(s).")

    def create_job(self, job_type, input_ref, params):
        """Create and enqueue a new clipping job."""
        job_id = str(uuid.uuid4())
        now_iso = utc_now_iso()
        params_json = json.dumps(params)
        
        with self.get_conn() as conn:
            conn.execute("""
                INSERT INTO jobs (
                    id, job_type, status, input_ref, params,
                    progress, stage, error_message, outputs,
                    created_at, started_at, completed_at
                ) VALUES (?, ?, 'queued', ?, ?, 0, 'Queued in line', NULL, NULL, ?, NULL, NULL);
            """, (job_id, job_type, input_ref, params_json, now_iso))

        with self.cond:
            self.cond.notify()

        print(f"[JobQueue] Enqueued {job_type} job: {job_id} for {input_ref}")
        return self.get_job(job_id)

    def get_job(self, job_id):
        """Retrieve sanitized job record by ID."""
        with self.get_conn() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?;", (job_id,)).fetchone()
            if not row:
                return None
            return self._format_job_row(row)

    def list_jobs(self, limit=50):
        """List recent jobs."""
        with self.get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM jobs
                ORDER BY created_at DESC
                LIMIT ?;
            """, (max(1, min(200, int(limit))),)).fetchall()
            return [self._format_job_row(r) for r in rows]

    def cancel_job(self, job_id):
        """Request cooperative cancellation of a queued or running job."""
        with self.lock:
            with self.get_conn() as conn:
                row = conn.execute("SELECT status FROM jobs WHERE id = ?;", (job_id,)).fetchone()
                if not row:
                    return False
                status = row["status"]
                
                if status == "queued":
                    now_iso = utc_now_iso()
                    conn.execute("""
                        UPDATE jobs
                        SET status = 'cancelled',
                            stage = 'Cancelled by user',
                            completed_at = ?
                        WHERE id = ?;
                    """, (now_iso, job_id))
                    return True
                    
                if status == "processing":
                    self.cancel_requested.add(job_id)
                    conn.execute("""
                        UPDATE jobs
                        SET stage = 'Cancelling...'
                        WHERE id = ?;
                    """, (job_id,))
                    return True
                    
                return False

    def is_cancel_requested(self, job_id):
        """Check if job has received a cancellation request."""
        with self.lock:
            return job_id in self.cancel_requested

    def update_job_progress(self, job_id, stage, progress):
        """Thread-safe update of current job stage and progress percentage."""
        progress = max(0, min(100, int(progress)))
        try:
            with self.get_conn() as conn:
                conn.execute("""
                    UPDATE jobs
                    SET stage = ?,
                        progress = ?
                    WHERE id = ? AND status = 'processing';
                """, (stage, progress, job_id))
        except Exception as e:
            print(f"[JobQueue] Progress update error ({job_id}): {e}")

    def get_job_file_path(self, job_id, filename=None):
        """
        Verify that a requested filename belongs to the specified completed job
        and return its absolute path. Protects against arbitrary file downloading.
        """
        job = self.get_job(job_id)
        if not job or job.get("status") != "completed":
            return None
            
        outputs = job.get("outputs") or []
        allowed_filenames = set()
        
        # Check individual clips
        for out in outputs:
            fn = out.get("video_filename")
            if fn:
                allowed_filenames.add(os.path.basename(fn))
                
        # Check ZIP bundle if batch
        zip_fn = job.get("zip_filename")
        if zip_fn:
            allowed_filenames.add(os.path.basename(zip_fn))
            
        if not filename:
            # Default to first available file (or ZIP for batch)
            if zip_fn and os.path.exists(os.path.join(self.output_dir, zip_fn)):
                return os.path.join(self.output_dir, zip_fn)
            if outputs and outputs[0].get("video_filename"):
                return os.path.join(self.output_dir, outputs[0]["video_filename"])
            return None
            
        clean_fn = os.path.basename(filename)
        if clean_fn in allowed_filenames:
            candidate = os.path.join(self.output_dir, clean_fn)
            if os.path.exists(candidate) and os.path.isfile(candidate):
                return candidate
                
        return None

    def _worker_loop(self):
        """Worker thread loop consuming queued jobs."""
        while not self.stop_event.is_set():
            job = None
            with self.cond:
                while not self.stop_event.is_set():
                    job = self._claim_next_job()
                    if job:
                        break
                    # Wait for next job notification or poll every 2s
                    self.cond.wait(timeout=2.0)
                    
            if self.stop_event.is_set():
                break
                
            if job:
                job_id = job["id"]
                with self.lock:
                    self.running_jobs.add(job_id)
                try:
                    self._execute_job(job)
                finally:
                    with self.lock:
                        self.running_jobs.discard(job_id)
                        self.cancel_requested.discard(job_id)

    def _claim_next_job(self):
        """Atomically claim the next queued job."""
        now_iso = utc_now_iso()
        with self.get_conn() as conn:
            conn.execute("BEGIN IMMEDIATE;")
            row = conn.execute("""
                SELECT * FROM jobs
                WHERE status = 'queued'
                ORDER BY created_at ASC
                LIMIT 1;
            """).fetchone()
            
            if not row:
                return None
                
            job_id = row["id"]
            conn.execute("""
                UPDATE jobs
                SET status = 'processing',
                    started_at = ?,
                    stage = 'Starting processing...',
                    progress = 5
                WHERE id = ?;
            """, (now_iso, job_id))
            
            # Fetch freshly updated row
            updated_row = conn.execute("SELECT * FROM jobs WHERE id = ?;", (job_id,)).fetchone()
            return self._format_job_row(updated_row)

    def _execute_job(self, job):
        """Execute the claimed video processing job."""
        job_id = job["id"]
        job_type = job["job_type"]
        input_ref = job["input_ref"]
        params = job.get("params") or {}
        
        print(f"[Worker] Starting {job_type} job {job_id} ({input_ref})...")
        
        cancel_check = lambda: self.is_cancel_requested(job_id)
        progress_cb = lambda stage, pct: self.update_job_progress(job_id, stage, pct)
        
        try:
            if cancel_check():
                raise RuntimeError("Job was cancelled before execution started")
                
            if job_type == "batch":
                result = clipper_core.generate_shorts_batch(
                    url=input_ref,
                    clips=params.get("clips", []),
                    layout=params.get("layout", "blur"),
                    subtitle_style=params.get("subtitle_style", "3d_hormozi"),
                    header_lines=params.get("header_lines"),
                    sfx_enabled=bool(params.get("sfx_enabled", True)),
                    sfx_hook=params.get("sfx_hook", "vine_boom"),
                    dynamic_zoom=bool(params.get("dynamic_zoom", True)),
                    high_quality=bool(params.get("high_quality", True)),
                    copyright_shield=bool(params.get("copyright_shield", True)),
                    output_dir=self.output_dir,
                    progress_callback=progress_cb,
                    cancel_check=cancel_check
                )
                
                if cancel_check():
                    raise RuntimeError("Job was cancelled by user")
                    
                successful_clips = []
                for idx, r in enumerate(result.get("results", [])):
                    if r.get("status") == "success":
                        successful_clips.append(self._sanitize_output_record(r, job_id, idx + 1))
                        
                if not successful_clips:
                    err_msgs = [r.get("error", "Unknown clip render failure") for r in result.get("results", []) if r.get("error")]
                    raise RuntimeError("; ".join(err_msgs) if err_msgs else "Failed to generate any clips")
                    
                zip_filename = result.get("zip_filename")
                zip_url = f"/output/{zip_filename}" if zip_filename else None
                
                self._mark_completed(
                    job_id=job_id,
                    outputs=successful_clips,
                    zip_filename=zip_filename,
                    zip_download_url=zip_url,
                    message=f"Successfully generated {len(successful_clips)} viral shorts."
                )
                
            else: # Single short
                result = clipper_core.generate_short(
                    url=input_ref,
                    start_time=params.get("start_time", "0:00"),
                    end_time=params.get("end_time", "0:35"),
                    layout=params.get("layout", "blur"),
                    subtitle_style=params.get("subtitle_style", "3d_hormozi"),
                    top_hook=params.get("top_hook", "WAIT TILL THE END 😱"),
                    header_lines=params.get("header_lines"),
                    sfx_enabled=bool(params.get("sfx_enabled", True)),
                    sfx_hook=params.get("sfx_hook", "vine_boom"),
                    dynamic_zoom=bool(params.get("dynamic_zoom", True)),
                    high_quality=bool(params.get("high_quality", True)),
                    copyright_shield=bool(params.get("copyright_shield", True)),
                    output_dir=self.output_dir,
                    custom_title=params.get("title") or params.get("custom_title"),
                    progress_callback=progress_cb,
                    cancel_check=cancel_check
                )
                
                if cancel_check():
                    raise RuntimeError("Job was cancelled by user")
                    
                output_record = self._sanitize_output_record(result, job_id, 1)
                self._mark_completed(
                    job_id=job_id,
                    outputs=[output_record],
                    zip_filename=None,
                    zip_download_url=None,
                    message="9:16 Short generated successfully!"
                )
                
            print(f"[Worker] Job {job_id} finished successfully.")

        except Exception as e:
            if cancel_check() or "cancelled" in str(e).lower():
                print(f"[Worker] Job {job_id} was cancelled.")
                self._mark_cancelled(job_id)
            else:
                print(f"[Worker] Job {job_id} failed: {e}")
                self._mark_failed(job_id, str(e))

    def _sanitize_output_record(self, raw_record, job_id, clip_num):
        """Sanitize output record to ensure internal filesystem paths are never exposed."""
        filename = raw_record.get("video_filename") or ""
        clean_fn = os.path.basename(filename)
        
        return {
            "id": raw_record.get("id", clip_num),
            "video_filename": clean_fn,
            "download_url": f"/output/{clean_fn}",
            "secure_download_url": f"/api/jobs/{job_id}/download?file={clean_fn}",
            "duration": raw_record.get("duration", 0),
            "file_size_mb": raw_record.get("file_size_mb", 0.0),
            "title": raw_record.get("title") or f"Short #{clip_num}",
            "virality_score": raw_record.get("virality_score", 95),
            "hook_badge": raw_record.get("hook_badge", "🔥 VIRAL HIGHLIGHT"),
            "attention_point": raw_record.get("attention_point", "High Retention Point"),
            "suggested_title": raw_record.get("suggested_title", ""),
            "suggested_description": raw_record.get("suggested_description", ""),
            "suggested_tags": raw_record.get("suggested_tags", [])
        }

    def _mark_completed(self, job_id, outputs, zip_filename=None, zip_download_url=None, message="Completed"):
        now_iso = utc_now_iso()
        outputs_json = json.dumps({
            "items": outputs,
            "zip_filename": zip_filename,
            "zip_download_url": zip_download_url
        })
        with self.get_conn() as conn:
            conn.execute("""
                UPDATE jobs
                SET status = 'completed',
                    progress = 100,
                    stage = ?,
                    outputs = ?,
                    completed_at = ?
                WHERE id = ?;
            """, (message, outputs_json, now_iso, job_id))

    def _mark_failed(self, job_id, error_message):
        now_iso = utc_now_iso()
        with self.get_conn() as conn:
            conn.execute("""
                UPDATE jobs
                SET status = 'failed',
                    stage = 'Failed',
                    error_message = ?,
                    completed_at = ?
                WHERE id = ?;
            """, (error_message, now_iso, job_id))

    def _mark_cancelled(self, job_id):
        now_iso = utc_now_iso()
        with self.get_conn() as conn:
            conn.execute("""
                UPDATE jobs
                SET status = 'cancelled',
                    stage = 'Cancelled by user',
                    error_message = 'Job was cancelled by user',
                    completed_at = ?
                WHERE id = ?;
            """, (now_iso, job_id))

    def _format_job_row(self, row):
        """Format an SQLite row into a clean user-facing dictionary."""
        d = dict(row)
        try:
            d["params"] = json.loads(d.get("params") or "{}")
        except Exception:
            d["params"] = {}
            
        outputs_raw = d.get("outputs")
        outputs_data = {"items": [], "zip_filename": None, "zip_download_url": None}
        if outputs_raw:
            try:
                parsed = json.loads(outputs_raw)
                if isinstance(parsed, dict):
                    outputs_data = parsed
                elif isinstance(parsed, list):
                    outputs_data["items"] = parsed
            except Exception:
                pass
                
        d["outputs"] = outputs_data.get("items", [])
        d["zip_filename"] = outputs_data.get("zip_filename")
        d["zip_download_url"] = outputs_data.get("zip_download_url")
        if d.get("zip_filename"):
            d["secure_zip_download_url"] = f"/api/jobs/{d['id']}/download?file={d['zip_filename']}"
        else:
            d["secure_zip_download_url"] = None
        
        # Redact any absolute filesystem paths inside params if present
        if isinstance(d["params"], dict):
            if "file_path" in d["params"]:
                d["params"]["file_path"] = os.path.basename(d["params"]["file_path"])
        if d.get("input_ref") and os.path.isabs(d["input_ref"]):
            d["input_ref"] = os.path.basename(d["input_ref"])
            
        return d

    def stop(self):
        """Signal worker threads to terminate gracefully."""
        self.stop_event.set()
        with self.cond:
            self.cond.notify_all()
        for w in self.workers:
            w.join(timeout=2.0)
