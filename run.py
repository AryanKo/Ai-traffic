"""Single entry point: builds the frontend if needed, starts the server, opens the browser."""
import argparse
import os
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def ensure_frontend_built() -> None:
    dist = ROOT / "frontend" / "dist"
    if dist.exists():
        return
    print("frontend/dist not found, running npm run build ...")
    subprocess.run(["npm", "run", "build"], cwd=str(ROOT / "frontend"), check=True, shell=(os.name == "nt"))


def open_browser_later(url: str) -> None:
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", dest="port", default=None, help="Arduino COM port override, e.g. COM5")
    args = parser.parse_args()
    if args.port:
        os.environ["TRAFFIC_PORT"] = args.port

    ensure_frontend_built()

    sys.path.insert(0, str(ROOT / "backend"))
    import uvicorn

    url = "http://127.0.0.1:8000"
    open_browser_later(url)
    uvicorn.run("main:app", host="127.0.0.1", port=8000, app_dir=str(ROOT / "backend"))


if __name__ == "__main__":
    main()
