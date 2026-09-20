import os
import sys
import json
import urllib.parse
import mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
import clipper_core

PORT = 5000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

class ShortsStudioHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        # Enable CORS and disable aggressive caching for local dev
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        
        # Route: Serve root
        if path == "/" or path == "":
            path = "/index.html"
            
        # Route: Serve output videos
        if path.startswith("/output/"):
            rel_file = path[len("/output/"):]
            file_path = os.path.join(OUTPUT_DIR, rel_file)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                self.serve_file(file_path, "video/mp4")
                return
            else:
                self.send_error(404, "Video Not Found")
                return
                
        # Route: Serve static local files
        file_path = os.path.join(BASE_DIR, path.lstrip("/"))
        if os.path.exists(file_path) and os.path.isfile(file_path):
            ctype, _ = mimetypes.guess_type(file_path)
            self.serve_file(file_path, ctype or "application/octet-stream")
            return
            
        self.send_error(404, "File Not Found")

    def serve_file(self, file_path, content_type):
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
                
                with open(file_path, "rb") as f:
                    f.seek(start)
                    self.wfile.write(f.read(length))
                return

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(file_size))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            
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
        post_data = self.rfile.read(content_len) if content_len > 0 else b"{}"
        
        try:
            body = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            body = {}

        # API: Analyze Video & Detect Viral Moments
        if parsed.path == "/api/analyze":
            url = body.get("url", "").strip()
            if not url:
                self.send_json_response({"error": "No YouTube URL provided"}, status=400)
                return
            try:
                print(f"[Studio] Analyzing YouTube video: {url}")
                result = clipper_core.analyze_video(url)
                self.send_json_response(result)
            except Exception as e:
                print(f"[Studio] Analysis error: {e}")
                self.send_json_response({"error": str(e)}, status=500)
            return

        # API: Generate 9:16 Short
        elif parsed.path == "/api/generate":
            url = body.get("url", "").strip()
            start_time = body.get("start_time", "0:00")
            end_time = body.get("end_time", "0:35")
            layout = body.get("layout", "blur")
            subtitle_style = body.get("subtitle_style", "hormozi")
            top_hook = body.get("top_hook", "WAIT TILL THE END 😱")
            copyright_shield = bool(body.get("copyright_shield", True))
            
            if not url:
                self.send_json_response({"error": "URL required"}, status=400)
                return
                
            try:
                print(f"[Studio] Generating 9:16 Short for {url} ({start_time} -> {end_time}) Layout: {layout}")
                result = clipper_core.generate_short(
                    url=url,
                    start_time=start_time,
                    end_time=end_time,
                    layout=layout,
                    subtitle_style=subtitle_style,
                    top_hook=top_hook,
                    copyright_shield=copyright_shield,
                    output_dir=OUTPUT_DIR
                )
                result["download_url"] = f"/output/{result['video_filename']}"
                self.send_json_response(result)
            except Exception as e:
                print(f"[Studio] Generation error: {e}")
                self.send_json_response({"error": str(e)}, status=500)
            return

        # API: Open Output Folder in Windows File Explorer
        elif parsed.path == "/api/open-folder":
            try:
                os.startfile(OUTPUT_DIR)
                self.send_json_response({"status": "opened"})
            except Exception as e:
                self.send_json_response({"error": str(e)}, status=500)
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

def run(port=PORT):
    server_address = ("127.0.0.1", port)
    try:
        httpd = HTTPServer(server_address, ShortsStudioHandler)
        print(f"==================================================")
        print(f"  [+] VIRAL SHORTS STUDIO RUNNING")
        print(f"  [>] Open in your browser: http://localhost:{port}")
        print(f"==================================================")
        httpd.serve_forever()
    except OSError as e:
        if port < 5010:
            print(f"Port {port} busy, trying {port + 1}...")
            run(port + 1)
        else:
            raise e

if __name__ == "__main__":
    run()

