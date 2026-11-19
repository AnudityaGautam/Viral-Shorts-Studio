import os
import sys
import unittest
import json
import io
import time
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import server
import clipper_core
import job_manager

class MockSocket:
    def __init__(self, request_bytes):
        self._rfile = io.BytesIO(request_bytes)
        self._wfile = io.BytesIO()

    def makefile(self, mode="r", buffering=-1):
        if "r" in mode:
            return self._rfile
        return self._wfile

    def sendall(self, data):
        self._wfile.write(data)

    def get_response(self):
        return self._wfile.getvalue()


class MockServer:
    def __init__(self):
        self.server_name = "localhost"
        self.server_port = 5000


def call_handler(method, path, body=None, headers=None):
    """Invoke ShortsStudioHandler directly without network sockets."""
    headers = headers or {}
    body_bytes = b""
    if body is not None:
        if isinstance(body, str):
            body_bytes = body.encode("utf-8")
        elif isinstance(body, dict):
            body_bytes = json.dumps(body).encode("utf-8")
            if "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"
        elif isinstance(body, bytes):
            body_bytes = body
    if body_bytes and "Content-Length" not in headers:
        headers["Content-Length"] = str(len(body_bytes))

    header_lines = [f"{k}: {v}\r\n" for k, v in headers.items()]
    req_bytes = f"{method} {path} HTTP/1.1\r\nHost: localhost\r\n{''.join(header_lines)}\r\n".encode("utf-8") + body_bytes

    sock = MockSocket(req_bytes)
    srv = MockServer()
    try:
        handler = server.ShortsStudioHandler(sock, ("127.0.0.1", 12345), srv)
    except Exception as e:
        pass

    raw_response = sock.get_response()
    # Parse status and headers from raw HTTP response
    header_part, _, body_part = raw_response.partition(b"\r\n\r\n")
    lines = header_part.decode("utf-8", errors="replace").split("\r\n")
    status_line = lines[0] if lines else "HTTP/1.1 500 Internal Error"
    parts = status_line.split(" ", 2)
    status_code = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 500

    resp_headers = {}
    for line in lines[1:]:
        if ": " in line:
            hk, hv = line.split(": ", 1)
            resp_headers[hk.lower()] = hv

    return status_code, resp_headers, body_part


class TestServerEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Patch clipper_core.generate_short to prevent external network calls during tests
        cls.patcher = patch("clipper_core.generate_short", return_value={
            "status": "success",
            "video_filename": "mock_short.mp4",
            "duration": 30,
            "file_size_mb": 10.0
        })
        cls.mock_gen = cls.patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.patcher.stop()

    def test_01_list_jobs_endpoint(self):
        code, headers, body = call_handler("GET", "/api/jobs")
        self.assertEqual(code, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("jobs", data)
        self.assertIsInstance(data["jobs"], list)
        print("[PASS] GET /api/jobs returns job list")

    def test_02_create_single_job_endpoint(self):
        payload = {
            "type": "single",
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "start_time": "0:00",
            "end_time": "0:30",
            "layout": "blur",
            "subtitle_style": "3d_hormozi"
        }
        code, headers, body = call_handler("POST", "/api/jobs", body=payload)
        self.assertEqual(code, 202)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "queued")
        self.assertIn("job_id", data)
        job_id = data["job_id"]

        # Fetch job details via GET /api/jobs/<job_id>
        code2, headers2, body2 = call_handler("GET", f"/api/jobs/{job_id}")
        self.assertEqual(code2, 200)
        data2 = json.loads(body2.decode("utf-8"))
        self.assertEqual(data2["id"], job_id)
        self.assertEqual(data2["job_type"], "single")
        print("[PASS] POST /api/jobs (202) and GET /api/jobs/{id} (200) verified")

    def test_03_cancel_queued_job_endpoint(self):
        payload = {
            "type": "single",
            "url": "https://www.youtube.com/watch?v=test_cancel",
            "layout": "crop"
        }
        code, headers, body = call_handler("POST", "/api/jobs", body=payload)
        self.assertEqual(code, 202)
        job_id = json.loads(body.decode("utf-8"))["job_id"]

        # Cancel the job
        code_cancel, _, body_cancel = call_handler("POST", f"/api/jobs/{job_id}/cancel", body={})
        self.assertEqual(code_cancel, 200)
        cancel_data = json.loads(body_cancel.decode("utf-8"))
        self.assertIn(cancel_data["status"], ("cancelled", "cancelling", "ignored"))

        # Verify job is tracked
        code_status, _, body_status = call_handler("GET", f"/api/jobs/{job_id}")
        self.assertEqual(code_status, 200)
        job_status = json.loads(body_status.decode("utf-8"))
        self.assertIn(job_status["status"], ("cancelled", "completed", "processing"))
        print("[PASS] POST /api/jobs/{id}/cancel verified")

    def test_04_create_batch_job_validation(self):
        # Missing clips in batch should return 400 Bad Request
        payload = {
            "type": "batch",
            "url": "https://www.youtube.com/watch?v=test"
        }
        code, _, body = call_handler("POST", "/api/jobs", body=payload)
        self.assertEqual(code, 400)
        err = json.loads(body.decode("utf-8"))
        self.assertIn("error", err)

        # Valid batch clips
        valid_batch = {
            "type": "batch",
            "url": "https://www.youtube.com/watch?v=test",
            "clips": [{"id": 1, "start_time": "0:00", "end_time": "0:30"}]
        }
        code_ok, _, body_ok = call_handler("POST", "/api/jobs", body=valid_batch)
        self.assertEqual(code_ok, 202)
        batch_job = json.loads(body_ok.decode("utf-8"))
        self.assertEqual(batch_job["job"]["job_type"], "batch")
        print("[PASS] Batch job parameter validation verified")

    def test_05_download_file_endpoint_security(self):
        # Non-existent job
        code, _, _ = call_handler("GET", "/api/jobs/non-existent-id/download?file=clip.mp4")
        self.assertEqual(code, 404)

        # Path traversal attempt in file query param
        code2, _, _ = call_handler("GET", "/api/jobs/non-existent-id/download?file=../../server.py")
        self.assertEqual(code2, 404)
        print("[PASS] GET /api/jobs/{id}/download security checks verified")

    def test_06_database_file_protection(self):
        # Direct attempt to download jobs.db via static route must be blocked (403)
        code, _, _ = call_handler("GET", "/jobs.db")
        self.assertEqual(code, 403)

        code2, _, _ = call_handler("GET", "/jobs.sqlite")
        self.assertEqual(code2, 403)
        print("[PASS] Static server blocks sensitive database extensions (.db, .sqlite)")

    def test_07_legacy_generate_async_flag(self):
        # Test backward-compatible /api/generate with async=True
        payload = {
            "async": True,
            "url": "https://www.youtube.com/watch?v=legacy_async",
            "start_time": "0:00",
            "end_time": "0:30"
        }
        code, _, body = call_handler("POST", "/api/generate", body=payload)
        self.assertEqual(code, 202)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "queued")
        self.assertIn("job_id", data)
        print("[PASS] Legacy /api/generate with async flag returns 202 queued job")

    def test_08_health_check_endpoint(self):
        code, _, body = call_handler("GET", "/api/health")
        self.assertEqual(code, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "healthy")
        self.assertIn("workers_running", data)

        code2, _, body2 = call_handler("GET", "/healthz")
        self.assertEqual(code2, 200)
        data2 = json.loads(body2.decode("utf-8"))
        self.assertEqual(data2["status"], "healthy")
        print("[PASS] Health check endpoints (/healthz and /api/health) return healthy 200")

    def test_09_upload_size_limit_rejection(self):
        # Oversized upload header must be rejected immediately with 413
        oversized = server.MAX_UPLOAD_BYTES + 1024 * 1024
        headers = {
            "Content-Length": str(oversized),
            "X-Filename": "oversized_video.mp4"
        }
        code, _, body = call_handler("POST", "/api/upload", body=b"", headers=headers)
        self.assertEqual(code, 413)
        err = json.loads(body.decode("utf-8"))
        self.assertIn("exceeds maximum allowed limit", err["error"])
        print("[PASS] Upload size enforcement rejects oversized files with HTTP 413")

    def test_10_json_payload_size_limit(self):
        # Oversized JSON payload must be rejected with 413
        oversized = server.MAX_JSON_BODY_SIZE + 1024
        headers = {"Content-Length": str(oversized)}
        code, _, body = call_handler("POST", "/api/jobs", body=b"", headers=headers)
        self.assertEqual(code, 413)
        err = json.loads(body.decode("utf-8"))
        self.assertIn("too large", err["error"].lower())
        print("[PASS] JSON payload size limit rejects oversized bodies with HTTP 413")

    def test_11_optional_api_key_auth(self):
        with patch.object(server, "STUDIO_API_KEY", "secret-test-token-123"):
            # Request without token must fail with 401
            code, _, body = call_handler("GET", "/api/jobs")
            self.assertEqual(code, 401)
            err = json.loads(body.decode("utf-8"))
            self.assertIn("Unauthorized", err["error"])

            # Query parameter tokens are rejected with 401 to prevent URL logging leaks
            code_query, _, _ = call_handler("GET", "/api/jobs?api_key=secret-test-token-123")
            self.assertEqual(code_query, 401)

            # Unauthenticated job submission must be blocked with 401
            code_post, _, _ = call_handler("POST", "/api/jobs", body={"type": "single", "url": "test"})
            self.assertEqual(code_post, 401)

            # Request with valid X-API-Key header token must succeed
            code_ok, _, body_ok = call_handler("GET", "/api/jobs", headers={"X-API-Key": "secret-test-token-123"})
            self.assertEqual(code_ok, 200)

            # Request with valid Authorization: Bearer token must succeed
            code_bearer, _, _ = call_handler("GET", "/api/jobs", headers={"Authorization": "Bearer secret-test-token-123"})
            self.assertEqual(code_bearer, 200)

            # Health check endpoint must remain unauthenticated
            code_health, _, _ = call_handler("GET", "/api/health")
            self.assertEqual(code_health, 200)
        print("[PASS] Optional API key authentication protects API routes (headers only) while preserving public healthcheck")

    def test_12_cancellable_subprocess_immediate_kill(self):
        # Run a long sleep command and verify cancellation kills it immediately
        is_cancelled = False
        def cancel_hook():
            return is_cancelled

        # Trigger cancellation after 100ms
        def cancel_soon():
            nonlocal is_cancelled
            time.sleep(0.15)
            is_cancelled = True

        import threading
        threading.Thread(target=cancel_soon, daemon=True).start()

        cmd = ["python", "-c", "import time; time.sleep(10)"]
        start_t = time.time()
        with self.assertRaises(RuntimeError) as ctx:
            clipper_core.run_cancellable_subprocess(cmd, cancel_check=cancel_hook, timeout=15)

        elapsed = time.time() - start_t
        self.assertLess(elapsed, 2.0, "Subprocess was not terminated promptly on cancellation")
        self.assertIn("cancelled", str(ctx.exception).lower())
        print("[PASS] Cancellable subprocess execution promptly terminates process on user cancellation")

if __name__ == "__main__":
    unittest.main(verbosity=2)
