import os
import sys
import unittest
import json
import time
from unittest.mock import patch, MagicMock

# Ensure workspace is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import job_manager

class TestJobSystem(unittest.TestCase):
    def setUp(self):
        # Use an isolated SQLite file for each test
        self.test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "test_jobs")
        os.makedirs(self.test_dir, exist_ok=True)
        self.db_path = os.path.join(self.test_dir, f"test_jobs_{time.time_ns()}.db")
        self.output_dir = os.path.join(self.test_dir, "output")
        os.makedirs(self.output_dir, exist_ok=True)

    def tearDown(self):
        if hasattr(self, 'jm') and self.jm:
            self.jm.stop()
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass

    def test_job_creation_and_retrieval(self):
        self.jm = job_manager.JobManager(db_path=self.db_path, output_dir=self.output_dir, start_workers=False)
        params = {"layout": "blur", "subtitle_style": "3d_hormozi", "start_time": "0:00", "end_time": "0:30"}
        job = self.jm.create_job("single", "https://youtube.com/watch?v=dQw4w9WgXcQ", params)
        
        self.assertIsNotNone(job)
        self.assertEqual(job["status"], "queued")
        self.assertEqual(job["job_type"], "single")
        self.assertEqual(job["progress"], 0)
        
        # Test retrieve
        fetched = self.jm.get_job(job["id"])
        self.assertEqual(fetched["id"], job["id"])
        self.assertEqual(fetched["params"]["layout"], "blur")
        print("[PASS] Job creation and retrieval verified")

    def test_queued_job_cancellation(self):
        self.jm = job_manager.JobManager(db_path=self.db_path, output_dir=self.output_dir, start_workers=False)
        job = self.jm.create_job("single", "https://youtube.com/watch?v=test", {})
        
        # Cancel while queued
        success = self.jm.cancel_job(job["id"])
        self.assertTrue(success)
        
        updated = self.jm.get_job(job["id"])
        self.assertEqual(updated["status"], "cancelled")
        self.assertIn("Cancelled", updated["stage"])
        print("[PASS] Queued job cancellation verified")

    def test_server_restart_recovery(self):
        # 1. Create a job and manually simulate it being in 'processing' state when server abruptly terminated
        self.jm = job_manager.JobManager(db_path=self.db_path, output_dir=self.output_dir, start_workers=False)
        job = self.jm.create_job("single", "https://youtube.com/watch?v=crash", {})
        
        with self.jm.get_conn() as conn:
            conn.execute("UPDATE jobs SET status = 'processing', stage = 'FFmpeg rendering' WHERE id = ?;", (job["id"],))
        self.jm.stop()

        # 2. Start a fresh JobManager instance pointing to the same DB (simulating server restart)
        new_jm = job_manager.JobManager(db_path=self.db_path, output_dir=self.output_dir, start_workers=False)
        recovered_job = new_jm.get_job(job["id"])
        new_jm.stop()

        self.assertEqual(recovered_job["status"], "failed")
        self.assertIn("interrupted by server restart", recovered_job["error_message"].lower())
        print("[PASS] Server restart job recovery verified")

    def test_worker_processing_success(self):
        # Mock clipper_core.generate_short to return dummy output quickly
        mock_result = {
            "status": "success",
            "video_filename": "test_short.mp4",
            "video_path": os.path.join(self.output_dir, "test_short.mp4"),
            "file_size_mb": 12.5,
            "duration": 30,
            "suggested_title": "Viral Hook #Shorts",
            "suggested_description": "Description",
            "suggested_tags": ["#Shorts"]
        }

        # Create dummy file
        with open(os.path.join(self.output_dir, "test_short.mp4"), "w") as f:
            f.write("mock video content")

        with patch("clipper_core.generate_short", return_value=mock_result):
            self.jm = job_manager.JobManager(db_path=self.db_path, max_concurrency=1, output_dir=self.output_dir, start_workers=True)
            job = self.jm.create_job("single", "https://youtube.com/watch?v=mock", {"start_time": "0:00", "end_time": "0:30"})
            
            # Poll for completion up to 5 seconds
            completed = False
            for _ in range(50):
                time.sleep(0.1)
                st = self.jm.get_job(job["id"])
                if st["status"] == "completed":
                    completed = True
                    break

            self.assertTrue(completed, f"Job did not complete in time, status: {st['status']}")
            self.assertEqual(st["progress"], 100)
            self.assertEqual(len(st["outputs"]), 1)
            self.assertEqual(st["outputs"][0]["video_filename"], "test_short.mp4")
            self.assertNotIn(self.output_dir, st["outputs"][0]["download_url"])
            print("[PASS] Worker successful processing verified")

    def test_worker_processing_failure(self):
        with patch("clipper_core.generate_short", side_effect=RuntimeError("FFmpeg test failure")):
            self.jm = job_manager.JobManager(db_path=self.db_path, max_concurrency=1, output_dir=self.output_dir, start_workers=True)
            job = self.jm.create_job("single", "https://youtube.com/watch?v=fail", {})
            
            failed = False
            for _ in range(50):
                time.sleep(0.1)
                st = self.jm.get_job(job["id"])
                if st["status"] == "failed":
                    failed = True
                    break

            self.assertTrue(failed, f"Job did not fail as expected, status: {st['status']}")
            self.assertIn("FFmpeg test failure", st["error_message"])
            print("[PASS] Worker error handling verified")

    def test_secure_download_file_resolution(self):
        self.jm = job_manager.JobManager(db_path=self.db_path, output_dir=self.output_dir, start_workers=False)
        job = self.jm.create_job("single", "test", {})
        
        # Write valid output file and unauthorized file
        valid_file = os.path.join(self.output_dir, "valid_clip.mp4")
        with open(valid_file, "w") as f:
            f.write("valid")
            
        secret_file = os.path.join(self.output_dir, "secret.txt")
        with open(secret_file, "w") as f:
            f.write("secret")

        # Mark job completed with valid_clip.mp4 only
        self.jm._mark_completed(
            job["id"],
            outputs=[{"video_filename": "valid_clip.mp4"}]
        )

        # Resolving valid file
        resolved = self.jm.get_job_file_path(job["id"], "valid_clip.mp4")
        self.assertEqual(os.path.abspath(resolved), os.path.abspath(valid_file))

        # Resolving unauthorized file must return None
        unauthorized = self.jm.get_job_file_path(job["id"], "secret.txt")
        self.assertIsNone(unauthorized)

        # Path traversal attempts must return None
        traversal = self.jm.get_job_file_path(job["id"], "../../server.py")
        self.assertIsNone(traversal)
        print("[PASS] Secure download file resolution verified")

if __name__ == "__main__":
    unittest.main(verbosity=2)
