import argparse
import os
import socket
import threading
import time
import webbrowser
from pathlib import Path


def _trace(message: str) -> None:
    path = os.getenv("ORIVOX_STARTUP_LOG")
    if not path:
        return
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")
    except Exception:
        pass


def _server_ready(host: str, port: int, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.15)
    return False


def _load_runtime():
    _trace("importing uvicorn")
    import uvicorn
    _trace("uvicorn imported")

    _trace("importing ORIVOX config")
    from orivox.config import HOST, PORT, APP_NAME
    _trace("ORIVOX config imported")

    _trace("importing ORIVOX database module")
    import orivox.db  # noqa: F401
    _trace("ORIVOX database module imported")

    _trace("importing ORIVOX services module")
    import orivox.services  # noqa: F401
    _trace("ORIVOX services module imported")

    _trace("importing ORIVOX app")
    from orivox.app import app
    _trace("ORIVOX app imported")
    _trace("runtime imports complete")
    return uvicorn, app, HOST, PORT, APP_NAME


def _build_server(uvicorn, app, host: str, port: int):
    # Frozen Windows executables are more reliable when Uvicorn is told
    # exactly which event loop and HTTP implementation to use.  Avoid the
    # auto selectors, which can import optional uvloop/httptools paths that
    # are unnecessary for ORIVOX's local-only server.
    _trace("creating uvicorn config")
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="warning",
        access_log=False,
        loop="asyncio",
        http="h11",
        ws="none",
        lifespan="off",
    )
    _trace("uvicorn config created")
    server = uvicorn.Server(config)
    _trace("uvicorn server created")
    return server


def _run_server(server) -> None:
    _trace("background uvicorn server starting")
    server.run()
    _trace("background uvicorn server stopped")


def _open_browser_when_ready(host: str, port: int, url: str) -> None:
    if not _server_ready(host, port, timeout=30):
        _trace("browser launcher timed out waiting for server")
        return
    _trace("server ready for browser mode")
    if os.getenv("ORIVOX_NO_BROWSER") != "1":
        webbrowser.open(url)


def _smoke_test(app) -> None:
    _trace("smoke test starting")
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
    _trace("smoke test passed")


def main() -> int:
    _trace("launcher entered main")
    parser = argparse.ArgumentParser(description="HR-Presents ORIVOX desktop launcher")
    parser.add_argument("--browser", action="store_true", help="Use the system browser instead of an embedded desktop window")
    parser.add_argument("--smoke-test", action="store_true", help="Verify the packaged app and bundled web/API runtime, then exit")
    args = parser.parse_args()
    _trace(f"arguments parsed browser={args.browser} smoke_test={args.smoke_test}")

    uvicorn, app, HOST, PORT, APP_NAME = _load_runtime()

    if args.smoke_test:
        _smoke_test(app)
        return 0

    server = _build_server(uvicorn, app, HOST, PORT)
    url = f"http://{HOST}:{PORT}"

    if args.browser:
        opener = threading.Thread(
            target=_open_browser_when_ready,
            args=(HOST, PORT, url),
            daemon=True,
            name="orivox-browser-opener",
        )
        opener.start()
        _trace("starting uvicorn on main thread")
        try:
            server.run()
        except KeyboardInterrupt:
            pass
        except Exception as exc:
            _trace(f"main-thread uvicorn failed: {exc!r}")
            raise
        finally:
            server.should_exit = True
        _trace("main-thread uvicorn stopped")
        return 0

    thread = threading.Thread(target=_run_server, args=(server,), daemon=True, name="orivox-local-server")
    thread.start()

    if not _server_ready(HOST, PORT):
        server.should_exit = True
        thread.join(timeout=5)
        raise RuntimeError("ORIVOX local server failed to start")

    try:
        _trace("opening embedded webview")
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
    except Exception as exc:
        _trace(f"embedded webview failed: {exc!r}; falling back to browser")
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
