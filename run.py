"""Single entry point: builds the frontend if needed, starts the server, opens the browser."""
import argparse
import os
import socket
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def ensure_frontend_built() -> None:
    dist_index = ROOT / "frontend" / "dist" / "index.html"
    src = ROOT / "frontend" / "src"
    if dist_index.exists():
        built_at = dist_index.stat().st_mtime
        if all(p.stat().st_mtime <= built_at for p in src.rglob("*") if p.is_file()):
            return
        print("frontend source changed since last build, running npm run build ...")
    else:
        print("frontend/dist not found, running npm run build ...")
    subprocess.run(["npm", "run", "build"], cwd=str(ROOT / "frontend"), check=True, shell=(os.name == "nt"))


def open_browser_later(url: str) -> None:
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()


def lan_addresses() -> list[str]:
    """IPv4 addresses other devices on the same Wi-Fi/hotspot can reach."""
    found = []
    try:
        # No packet is sent; this just asks the OS which interface routes outward.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            found.append(s.getsockname()[0])
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            found.append(info[4][0])
    except OSError:
        pass
    return [ip for ip in dict.fromkeys(found) if not ip.startswith("127.")]


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
    print()
    print(f"Dashboard: {url}")
    ips = lan_addresses()
    if ips:
        # The first address is the one the OS routes outward, i.e. the hotspot/Wi-Fi.
        print(f"Phone remote (open on your phone): http://{ips[0]}:8000/remote")
        for ip in ips[1:]:
            print(f"  other network adapters, only if the one above fails: http://{ip}:8000/remote")
    else:
        print("Phone remote: no network found. Connect the laptop to the phone hotspot and restart.")
    print()
    open_browser_later(url)
    # 0.0.0.0 so the phone on the same hotspot can reach the remote page.
    uvicorn.run("main:app", host="0.0.0.0", port=8000, app_dir=str(ROOT / "backend"))


if __name__ == "__main__":
    main()
