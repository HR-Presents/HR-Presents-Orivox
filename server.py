import argparse
import os
import signal
import sys
import time
from pathlib import Path


def _trace(message: str) -> None:
    path = os.getenv("ORIVOX_STARTUP_LOG")
    if not path:
        return
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} [server] {message}\n")
    except Exception:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description="ORIVOX local server worker")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    _trace("server worker starting")
    import uvicorn
    from orivox.config import HOST, PORT
    from orivox.app import app

    host = args.host or HOST
    port = args.port or PORT
    _trace(f"building server host={host} port={port}")
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="warning",
        access_log=False,
        use_colors=False,
        loop="asyncio",
        http="httptools",
        ws="none",
        lifespan="off",
        reload=False,
        workers=1,
    )
    server = uvicorn.Server(config)
    _trace("running uvicorn server")
    server.run()
    _trace("server worker stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
