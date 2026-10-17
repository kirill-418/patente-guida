#!/usr/bin/env python3
"""Lightweight HTTP server for Parole Patente B.

Serves the standalone static flip-card app and provides persistent
storage on disk for single-user progress sync across devices (phone & desktop).
Zero external dependencies (Python standard library only).
"""

import gzip
import json
import os
import signal
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

VERSION = "1.2.0"
PORT = int(os.environ.get("PORT", "80"))
BIND_HOST = os.environ.get("BIND_HOST", "0.0.0.0")
DATA_DIR = os.environ.get("DATA_DIR", "/data")
PROGRESS_FILE = os.path.join(DATA_DIR, "progress.json")

# Fallback index path for local development vs docker
INDEX_PATH = os.environ.get("INDEX_PATH", "/app/index.html")
if not os.path.exists(INDEX_PATH):
    local_index = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "app", "index.html")
    )
    if os.path.exists(local_index):
        INDEX_PATH = local_index

# If /data cannot be written (e.g. running locally outside docker without root),
# fall back to a local storage directory.
try:
    os.makedirs(DATA_DIR, exist_ok=True)
    test_file = os.path.join(DATA_DIR, ".write_test")
    with open(test_file, "w") as f:
        f.write("ok")
    os.remove(test_file)
except OSError:
    DATA_DIR = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "storage")
    )
    os.makedirs(DATA_DIR, exist_ok=True)
    PROGRESS_FILE = os.path.join(DATA_DIR, "progress.json")

SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'none'; "
        "form-action 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}

# In-memory progress state & lock
progress_lock = threading.Lock()
progress_data = {}


def load_progress_from_disk():
    global progress_data
    with progress_lock:
        if os.path.exists(PROGRESS_FILE):
            try:
                with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                    progress_data = json.load(f)
                k_count = len(progress_data.get("known", []))
                l_count = len(progress_data.get("learning", []))
                up = progress_data.get("updated", 0)
                print(
                    f"[storage] Loaded progress from {PROGRESS_FILE}: "
                    f"{k_count} known, {l_count} learning, updated={up}"
                )
            except Exception as e:
                print(f"[storage] Error reading {PROGRESS_FILE}: {e}")
                progress_data = {}
        else:
            print(f"[storage] No existing progress file at {PROGRESS_FILE}. Starting empty.")
            progress_data = {}


def save_progress_to_disk(data):
    """Atomically save progress data to disk using a temp file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp_path = PROGRESS_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, PROGRESS_FILE)


# Preload index.html
try:
    with open(INDEX_PATH, "rb") as f:
        INDEX_BYTES = f.read()
    INDEX_GZIP = gzip.compress(INDEX_BYTES, compresslevel=9)
    print(f"[server] Loaded {INDEX_PATH} ({len(INDEX_BYTES)} bytes, {len(INDEX_GZIP)} gzipped)")
except Exception as e:
    print(f"[server] Warning: could not load {INDEX_PATH}: {e}")
    INDEX_BYTES = b"<h1>Patente Guida app not found.</h1>"
    INDEX_GZIP = gzip.compress(INDEX_BYTES)


class AppRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress noisy healthcheck logs
        if args and any("/health" in str(a) for a in args):
            return
        super().log_message(format, *args)

    def send_cors_and_sec_headers(self):
        for k, v in SECURITY_HEADERS.items():
            self.send_header(k, v)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_cors_and_sec_headers()
        self.end_headers()

    def do_HEAD(self):
        self.handle_get(head_only=True)

    def do_GET(self):
        self.handle_get(head_only=False)

    def handle_get(self, head_only=False):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/health", "/healthz"):
            body = json.dumps({"status": "ok", "version": VERSION}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_cors_and_sec_headers()
            self.end_headers()
            if not head_only:
                self.wfile.write(body)
            return

        if path == "/api/progress":
            with progress_lock:
                body = json.dumps(progress_data, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_cors_and_sec_headers()
            self.end_headers()
            if not head_only:
                self.wfile.write(body)
            return

        if path.startswith("/images/"):
            fname = os.path.basename(path)
            possible_dirs = [
                os.path.join(os.path.dirname(__file__), "..", "quiz", "images"),
                os.path.join("/app", "images"),
                os.path.join(os.path.dirname(__file__), "images"),
            ]
            img_file = None
            for d in possible_dirs:
                p = os.path.join(d, fname)
                if os.path.isfile(p):
                    img_file = p
                    break
            if img_file:
                content_type = "image/webp" if fname.endswith(".webp") else "image/jpeg"
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Cache-Control", "public, max-age=31536000, immutable")
                self.send_cors_and_sec_headers()
                with open(img_file, "rb") as f:
                    data = f.read()
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                if not head_only:
                    self.wfile.write(data)
                return
            else:
                self.send_error(404, "Image not found")
                return

        # Serve index.html for root and all other routes
        accept_encoding = self.headers.get("Accept-Encoding", "")
        if "gzip" in accept_encoding:
            content = INDEX_GZIP
            use_gzip = True
        else:
            content = INDEX_BYTES
            use_gzip = False

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        if use_gzip:
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache")
        self.send_cors_and_sec_headers()
        self.end_headers()
        if not head_only:
            self.wfile.write(content)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/progress":
            self.send_error(404, "Endpoint not found")
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            if length > 2 * 1024 * 1024:
                self.send_error(413, "Payload too large")
                return
            body = self.rfile.read(length)
            incoming = json.loads(body.decode("utf-8"))
            if not isinstance(incoming, dict):
                raise ValueError("Payload must be a JSON object")
        except Exception as e:
            self.send_error(400, f"Invalid JSON payload: {e}")
            return

        global progress_data
        with progress_lock:
            incoming_updated = incoming.get("updated", 0)
            current_updated = progress_data.get("updated", 0)

            # Conflict resolution: newer updated timestamp wins
            if incoming_updated >= current_updated:
                progress_data = incoming
                save_progress_to_disk(progress_data)
                k_count = len(progress_data.get("known", []))
                l_count = len(progress_data.get("learning", []))
                print(
                    f"[storage] Updated progress: {k_count} known, {l_count} learning, "
                    f"updated={incoming_updated}"
                )
            else:
                print(
                    f"[storage] Ignored older update (incoming={incoming_updated} < current={current_updated})"
                )

            res_body = json.dumps(
                {"ok": True, "updated": progress_data.get("updated", 0)},
                ensure_ascii=False,
            ).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(res_body)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_cors_and_sec_headers()
        self.end_headers()
        self.wfile.write(res_body)


def run_server():
    load_progress_from_disk()
    server = ThreadingHTTPServer((BIND_HOST, PORT), AppRequestHandler)
    print(f"[server] Listening on http://{BIND_HOST}:{PORT} (storage at {DATA_DIR})")

    def handle_signal(sig, frame):
        print("\n[server] Shutting down...")
        threading.Thread(target=server.shutdown).start()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        server.serve_forever()
    finally:
        server.server_close()
        print("[server] Stopped.")


if __name__ == "__main__":
    run_server()
