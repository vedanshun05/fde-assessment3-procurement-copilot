from __future__ import annotations

import signal
import argparse
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env", override=False)


def start(cmd: list[str]) -> subprocess.Popen:
    return subprocess.Popen(cmd, cwd=ROOT)


def wait_for_api(url: str, proc: subprocess.Popen, timeout_seconds: float = 10.0) -> None:
    """Wait until the mock API is reachable or fail with a useful message."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(
                f"Vendor-risk API exited during startup with code {proc.returncode}. "
                "Check the terminal output above (a port conflict is a common cause)."
            )
        try:
            response = requests.get(url, timeout=0.5)
            if response.ok:
                return
        except requests.RequestException:
            pass
        time.sleep(0.25)
    raise RuntimeError(f"Vendor-risk API did not become ready within {timeout_seconds:.0f}s: {url}")


def _handle_termination(signum: int, frame: object) -> None:
    """Route SIGTERM through normal cleanup (useful for IDE/terminal stop actions)."""
    raise KeyboardInterrupt


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the procurement app and mock vendor API")
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument("--vendor-port", type=int, default=8001)
    args = parser.parse_args()
    for port in (args.port, args.vendor_port):
        try:
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", port))
        except OSError as exc:
            raise SystemExit(f"Port {port} is unavailable. Stop the existing service or choose --port / --vendor-port.") from exc
    if args.port == args.vendor_port:
        raise SystemExit("App and vendor API must use different ports.")
    os.environ["VENDOR_RISK_BASE_URL"] = f"http://127.0.0.1:{args.vendor_port}"
    signal.signal(signal.SIGTERM, _handle_termination)
    procs: list[subprocess.Popen] = []
    try:
        print(f"Starting vendor-risk API on http://127.0.0.1:{args.vendor_port} ...", flush=True)
        api_proc = start(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "mock_api.app:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(args.vendor_port),
                "--log-level", "warning",
            ]
        )
        procs.append(api_proc)
        wait_for_api(f"http://127.0.0.1:{args.vendor_port}/health", api_proc)
        print("Vendor-risk API is ready.")

        print(f"Starting copilot on http://127.0.0.1:{args.port} ...", flush=True)
        ui_proc = start([sys.executable, "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", str(args.port), "--log-level", "warning"])
        procs.append(ui_proc)
        wait_for_api(f"http://127.0.0.1:{args.port}/health", ui_proc)
        print(f"\nReady: http://127.0.0.1:{args.port}  |  mode={os.getenv('COPILOT_MODE', 'offline')}\nPress Ctrl+C to stop both services.", flush=True)

        while True:
            time.sleep(1)
            for proc in procs:
                if proc.poll() is not None:
                    raise RuntimeError(f"A local process exited with code {proc.returncode}")
    except KeyboardInterrupt:
        print("\nStopping local services ...")
    finally:
        for proc in procs:
            if proc.poll() is None:
                proc.terminate()
        for proc in procs:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)


if __name__ == "__main__":
    main()
