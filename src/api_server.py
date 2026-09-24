"""Runs the FastAPI backend inside the Streamlit process.

Hosting that only runs one command (Streamlit Community Cloud, a Hugging Face
Streamlit Space) cannot start uvicorn separately, so the app starts it here in
a background thread. Imports are cached in sys.modules, so the flag below
survives Streamlit reruns and the server is started only once.
"""

import os
import sys
import threading
import time
import urllib.request

API_HOST = "127.0.0.1"
API_PORT = int(os.environ.get("EXAMORA_API_PORT", "8000"))
API_URL = f"http://{API_HOST}:{API_PORT}"

_started = False


def api_is_up(timeout=2):
    try:
        with urllib.request.urlopen(f"{API_URL}/api/health", timeout=timeout) as response:
            return response.status == 200
    except Exception:
        return False


def ensure_api_running(wait_seconds=90):
    global _started

    if _started or api_is_up():
        _started = True
        return API_URL

    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)

    import uvicorn

    import api

    config = uvicorn.Config(
        api.app,
        host=API_HOST,
        port=API_PORT,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True, name="examora-api")
    thread.start()

    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        if api_is_up():
            _started = True
            return API_URL
        time.sleep(1)

    raise RuntimeError("The backend did not start in time.")
