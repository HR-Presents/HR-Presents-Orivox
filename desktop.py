import argparse
import socket
import threading
import time
import webbrowser

import uvicorn

from orivox.app import app
from orivox.config import HOST, PORT, APP_NAME


def _server_ready(host: str, port: int, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.15)
    return False


def _run_server(server: uvicorn.Server) -> None:
    server.run()


def _smoke_test() -> None:
    """Validate the frozen app and bundled web/API routes without starting a
    long-lived uvicorn thread, avoiding Windows shutdown hangs in CI.
    """
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        home = client.get("/")
        home.raise_for_status()
        if "ORIVOX" not in home.text:
            raise RuntimeError("Packaged web client did not render ORIVOX branding")

        status = client.get("/api/status")
        status.raise_for_status()
        payload = status.json()
        if "version" not in payload or "models" not in payload:
            raise RuntimeError("Packaged API status response is incomplete")


def main() -> int:
    parser = argparse.ArgumentParser(description="HR-Presents ORIVOX desktop launcher")
    parser.add_argument("--browser", action="store_true", help="Use the system browser instead of an embedded desktop window")
    parser.add_argument("--smoke-test", action="store_true", help="Verify the packaged app and bundled web/API runtime, then exit")
    args = parser.parse_args()

    if args.smoke_test:
        _smoke_test()
        return 0

    config = uvicorn.Config(app, host=HOST, port=PORT, log_level="warning", access_log=False)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=_run_server, args=(server,), daemon=True, name="orivox-local-server")
    thread.start()

    if not _server_ready(HOST, PORT):
        server.should_exit = True
        thread.join(timeout=5)
        raise RuntimeError("ORIVOX local server failed to start")

    url = f"http://{HOST}:{PORT}"

    if args.browser:
        webbrowser.open(url)
        try:
            while thread.is_alive():
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            server.should_exit = True
            thread.join(timeout=5)
        return 0

    try:
        import webview
        webview.create_window(
            f"{APP_NAME} — HR-Presents",
            url,
            width=1280,
            height=820,
            min_size=(900, 620),
            confirm_close=False,
        )
        webview.start(debug=False, private_mode=False)
    except Exception:
        webbrowser.open(url)
        try:
            while thread.is_alive():
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
    finally:
        server.should_exit = True
        thread.join(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
