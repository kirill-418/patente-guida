"""Integration test for docker/server.py persistent storage and HTTP API."""

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error


def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def wait_for_server(url, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=1) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.1)
    return False


def test_server():
    temp_dir = tempfile.mkdtemp(prefix="patente_test_")
    port = get_free_port()
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    server_py = os.path.join(repo_root, "docker", "server.py")
    index_html = os.path.join(repo_root, "app", "index.html")

    env = os.environ.copy()
    env["PORT"] = str(port)
    env["BIND_HOST"] = "127.0.0.1"
    env["DATA_DIR"] = temp_dir
    env["INDEX_PATH"] = index_html

    proc = subprocess.Popen([sys.executable, server_py], env=env)
    base_url = f"http://127.0.0.1:{port}"

    try:
        assert wait_for_server(f"{base_url}/health"), "Server failed to start"
        print("[test] Server started and healthy.")

        # Test HEAD /health
        req = urllib.request.Request(f"{base_url}/health", method="HEAD")
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
        print("[test] HEAD /health OK.")

        # Test GET /
        with urllib.request.urlopen(f"{base_url}/") as resp:
            assert resp.status == 200
            assert "Content-Security-Policy" in resp.headers
            assert "text/html" in resp.headers.get("Content-Type", "")
            body = resp.read().decode("utf-8")
            assert "Parole Patente B" in body
        print("[test] GET / OK.")

        # Test GET /api/progress (initially empty)
        with urllib.request.urlopen(f"{base_url}/api/progress") as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data == {}
        print("[test] Initial GET /api/progress returned empty object.")

        # Test POST /api/progress
        sample_progress = {
            "known": ["abbaglianti", "freno"],
            "learning": ["sorpasso"],
            "levels": ["A", "B"],
            "updated": 1729000000,
            "by": "device_phone"
        }
        post_data = json.dumps(sample_progress).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url}/api/progress",
            data=post_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            res = json.loads(resp.read().decode("utf-8"))
            assert res.get("ok") is True
            assert res.get("updated") == 1729000000
        print("[test] POST /api/progress succeeded.")

        # Verify file on disk
        progress_file = os.path.join(temp_dir, "progress.json")
        assert os.path.exists(progress_file), "progress.json does not exist on disk"
        with open(progress_file, "r", encoding="utf-8") as f:
            disk_data = json.load(f)
        assert disk_data == sample_progress
        print("[test] Verified file written to disk correctly.")

        # Test conflict resolution: older update ignored
        older_progress = {
            "known": ["abbaglianti"],
            "learning": [],
            "levels": ["A"],
            "updated": 1000,
            "by": "device_old"
        }
        req = urllib.request.Request(
            f"{base_url}/api/progress",
            data=json.dumps(older_progress).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            res = json.loads(resp.read().decode("utf-8"))
            assert res.get("updated") == 1729000000
        with open(progress_file, "r", encoding="utf-8") as f:
            disk_data = json.load(f)
        assert disk_data == sample_progress
        print("[test] Verified older update was ignored.")

        # Stop server
        proc.terminate()
        proc.wait(timeout=5)

        # Test persistence on startup: start a NEW server instance on the same temp_dir
        port2 = get_free_port()
        env["PORT"] = str(port2)
        base_url2 = f"http://127.0.0.1:{port2}"
        proc2 = subprocess.Popen([sys.executable, server_py], env=env)
        try:
            assert wait_for_server(f"{base_url2}/health"), "Second server failed to start"
            with urllib.request.urlopen(f"{base_url2}/api/progress") as resp:
                assert resp.status == 200
                data = json.loads(resp.read().decode("utf-8"))
                assert data == sample_progress
            print("[test] Second server loaded existing progress from disk on startup successfully!")
        finally:
            proc2.terminate()
            proc2.wait(timeout=5)

    finally:
        if proc.poll() is None:
            proc.kill()
        shutil.rmtree(temp_dir, ignore_errors=True)

    print("\nALL SERVER TESTS PASSED!")


if __name__ == "__main__":
    test_server()
