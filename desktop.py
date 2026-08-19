import argparse
import os
import socket
import subprocess
import sys
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
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} [launcher] {message}\n")
    except Exception:
        pass


def _server_ready(host: str, port: int, timeout: float = 45.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def _runtime_values():
    from orivox.config import HOST, PORT, APP_NAME
    return HOST, PORT, APP_NAME


def _server_executable() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).with_name("ORIVOX-server.exe")
    return Path(sys.executable)


def _start_server(host: str, port: int) -> subprocess.Popen:
    exe = _server_executable()
    if getattr(sys, "frozen", False):
        cmd = [str(exe), "--host", host, "--port", str(port)]
    else:
        cmd = [str(exe), str(Path(__file__).with_name("server.py")), "--host", host, "--port", str(port)]

    creationflags = 0
    startupinfo = None
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    _trace(f"starting server worker: {exe.name}")
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
        startupinfo=startupinfo,
        env=os.environ.copy(),
    )
    _trace(f"server worker pid={proc.pid}")
    return proc


def _stop_server(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    _trace("stopping server worker")
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="HR-Presents ORIVOX desktop launcher")
    parser.add_argument("--browser", action="store_true", help="Use the system browser instead of an embedded desktop window")
    args = parser.parse_args()

    HOST, PORT, APP_NAME = _runtime_values()
    url = f"http://{HOST}:{PORT}"
    proc = _start_server(HOST, PORT)

    try:
        if not _server_ready(HOST, PORT):
            code = proc.poll()
            raise RuntimeError(f"ORIVOX local server failed to start (exit={code})")
        _trace("server port is ready")

        if args.browser:
            if os.getenv("ORIVOX_NO_BROWSER") != "1":
                webbrowser.open(url)
            while proc.poll() is None:
                time.sleep(0.5)
            return proc.returncode or 0

        try:
            import webview
            _trace("opening embedded webview")
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
            while proc.poll() is None:
                time.sleep(0.5)
    finally:
        _stop_server(proc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
