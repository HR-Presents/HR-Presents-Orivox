import argparse
import socket
import threading
import time
import webbrowser

import uvicorn

from orivox.app import app
from orivox.config import HOST, PORT, APP_NAME, VERSION


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


def main() -> int:
    parser = argparse.ArgumentParser(description="HR-Presents ORIVOX desktop launcher")
    parser.add_argument("--browser", action="store_true", help="Use the system browser instead of an embedded desktop window")
    args = parser.parse_args()

    config = uvicorn.Config(app, host=HOST, port=PORT, log_level="warning", access_log=False)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=_run_server, args=(server,), daemon=True, name="orivox-local-server")
    thread.start()

    if not _server_ready(HOST, PORT):
        server.should_exit = True
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
        return 0

    try:
        import webview
        window = webview.create_window(
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
