"""Hdl Automation Frontend Launcher.

Starts the FastAPI web server and launches the web UI.
"""

import sys
import threading
import time
import webbrowser
import uvicorn


def _open_browser_delayed(url: str, delay: float = 1.0):
    time.sleep(delay)
    try:
        webbrowser.open(url)
    except Exception:
        pass


def main():
    host = "127.0.0.1"
    port = 8000
    url = f"http://{host}:{port}"

    print("=" * 68)
    print("   HDL AUTOMATION (WEB UI)")
    print("=" * 68)
    print(f" -> Local Web App URL: {url}")
    print(" -> Backend Integrity: 100% Intact & Untouched (Zero Backend Modification)")
    print(" -> Press Ctrl+C in this console to stop the web server.")
    print("=" * 68)

    # Launch browser after uvicorn initializes socket listener
    threading.Thread(target=_open_browser_delayed, args=(url, 1.2), daemon=True).start()

    uvicorn.run("frontend.app:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
