from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
EVIDENCE_DIR = ROOT / "review" / "e2e"
EVIDENCE_PATH = EVIDENCE_DIR / "api-realtime-browser-smoke.json"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def start_backend(port: int, *, websocket_enabled: bool) -> subprocess.Popen[bytes]:
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]
    if not websocket_enabled:
        command.extend(["--ws", "none"])
    environment = os.environ.copy()
    environment["REPOSITORY_BACKEND"] = "memory"
    return subprocess.Popen(
        command,
        cwd=BACKEND_DIR,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def start_frontend(port: int, backend_port: int) -> subprocess.Popen[bytes]:
    npm = "npm.cmd" if os.name == "nt" else "npm"
    environment = os.environ.copy()
    environment.update(
        {
            "VITE_DATA_SOURCE": "api",
            "VITE_API_BASE_URL": f"http://127.0.0.1:{backend_port}",
            "VITE_CESIUM_ION_TOKEN": "",
        }
    )
    return subprocess.Popen(
        [npm, "run", "dev", "--", "--host", "127.0.0.1", "--port", str(port), "--strictPort"],
        cwd=FRONTEND_DIR,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def stop_process(process: subprocess.Popen[bytes] | None) -> None:
    if process is None or process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def wait_for_http(url: str, process: subprocess.Popen[bytes], timeout: float = 45) -> None:
    deadline = time.monotonic() + timeout
    last_error = "not attempted"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"service exited with code {process.returncode} while waiting for {url}")
        try:
            with urlopen(url, timeout=2) as response:
                if response.status < 500:
                    return
                last_error = f"HTTP {response.status}"
        except (OSError, URLError) as error:
            last_error = str(error)
        time.sleep(0.25)
    raise TimeoutError(f"timed out waiting for {url}: {last_error}")


def post_observation(base_url: str, depth_mm: int, sequence: int) -> dict[str, object]:
    payload = {
        "sensorId": "SSZJ-NODE-001",
        "observedAt": datetime.now(timezone.utc).isoformat(),
        "depthMm": depth_mm,
        "sequence": sequence,
        "transport": "SIMULATOR",
        "batteryMv": 3920,
        "signalDbm": -61,
    }
    request = Request(
        f"{base_url}/api/v1/telemetry/observations",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=10) as response:
        if response.status != 201:
            raise AssertionError(f"telemetry POST returned HTTP {response.status}")
        result = json.loads(response.read().decode("utf-8"))
    if result.get("depthMm") != depth_mm or result.get("sensorId") != "SSZJ-NODE-001":
        raise AssertionError(f"unexpected telemetry response shape: {result}")
    return result


def wait_for_badge(page: Page, text: str, timeout: float = 20_000) -> None:
    page.wait_for_function(
        "expected => document.querySelector('.dashboard-demo-badge')?.textContent?.includes(expected)",
        arg=text,
        timeout=timeout,
    )


def wait_for_depth(page: Page, depth_cm: str, timeout: float = 15_000) -> None:
    page.wait_for_function(
        "expected => document.querySelector('.event-panel .event-metric strong')?.textContent?.includes(expected)",
        arg=depth_cm,
        timeout=timeout,
    )


def read_depth(page: Page) -> str:
    return page.locator(".event-panel .event-metric strong").first.inner_text()


def wait_for_request_count(page: Page, request_counts: dict[str, int], key: str, minimum: int, timeout: float = 10_000) -> int:
    deadline = time.monotonic() + timeout / 1000
    while time.monotonic() < deadline:
        current = request_counts[key]
        if current >= minimum:
            return current
        page.wait_for_timeout(100)
    raise AssertionError(f"timed out waiting for {key} request count >= {minimum}; observed {request_counts[key]}")


def main() -> int:
    backend_port = free_port()
    frontend_port = free_port()
    while frontend_port == backend_port:
        frontend_port = free_port()
    backend: subprocess.Popen[bytes] | None = None
    frontend: subprocess.Popen[bytes] | None = None
    browser = None
    page: Page | None = None
    evidence: dict[str, object] = {
        "status": "RUNNING",
        "backend_port": backend_port,
        "frontend_port": frontend_port,
        "frontend_command": "npm run dev -- --host 127.0.0.1 --port <free-port> --strictPort",
        "backend_commands": [
            "python -m uvicorn app.main:app --host 127.0.0.1 --port <free-port>",
            "python -m uvicorn app.main:app --host 127.0.0.1 --port <free-port> --ws none",
        ],
    }
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    try:
        backend = start_backend(backend_port, websocket_enabled=True)
        wait_for_http(f"http://127.0.0.1:{backend_port}/api/v1/dashboard/overview", backend)
        frontend = start_frontend(frontend_port, backend_port)
        frontend_url = f"http://127.0.0.1:{frontend_port}/"
        wait_for_http(frontend_url, frontend)

        launch_options: dict[str, object] = {"headless": True}
        if CHROME.exists():
            launch_options["executable_path"] = str(CHROME)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(**launch_options)
            page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
            console_errors: list[str] = []
            page_errors: list[str] = []
            request_counts = {"event": 0, "points": 0}
            page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
            page.on("pageerror", lambda error: page_errors.append(str(error)))

            def record_request(request) -> None:
                if request.method != "GET":
                    return
                if request.url.endswith("/api/v1/flood-events/FP202506010024"):
                    request_counts["event"] += 1
                if request.url.endswith("/api/v1/flood-points"):
                    request_counts["points"] += 1

            page.on("request", record_request)
            page.goto(frontend_url, wait_until="domcontentloaded", timeout=60_000)
            wait_for_badge(page, "WS CONNECTED")
            initial_depth = read_depth(page)
            live_response = post_observation(f"http://127.0.0.1:{backend_port}", 345, 501)
            wait_for_depth(page, "34.5")
            live_ui_depth = read_depth(page)
            page.screenshot(path=str(EVIDENCE_DIR / "api-realtime-live.png"), full_page=True)
            live_event_requests = request_counts["event"]

            page.wait_for_timeout(250)
            degraded_before = request_counts["event"]
            stop_process(backend)
            backend = start_backend(backend_port, websocket_enabled=False)
            wait_for_http(f"http://127.0.0.1:{backend_port}/api/v1/dashboard/overview", backend)
            wait_for_badge(page, "WS FALLBACK")
            immediate_refresh_requests = wait_for_request_count(page, request_counts, "event", degraded_before + 1)
            degraded_response = post_observation(f"http://127.0.0.1:{backend_port}", 412, 502)
            degraded_after = wait_for_request_count(page, request_counts, "event", immediate_refresh_requests + 1, timeout=12_000)
            wait_for_depth(page, "41.2", timeout=20_000)
            page.screenshot(path=str(EVIDENCE_DIR / "api-realtime-rest-fallback.png"), full_page=True)

            stop_process(backend)
            backend = start_backend(backend_port, websocket_enabled=True)
            wait_for_http(f"http://127.0.0.1:{backend_port}/api/v1/dashboard/overview", backend)
            wait_for_badge(page, "WS CONNECTED", timeout=20_000)
            connected_event_requests = request_counts["event"]
            page.wait_for_timeout(6_000)
            quiet_event_requests = request_counts["event"]
            resumed_response = post_observation(f"http://127.0.0.1:{backend_port}", 433, 503)
            wait_for_depth(page, "43.3", timeout=10_000)
            page.screenshot(path=str(EVIDENCE_DIR / "api-realtime-reconnected.png"), full_page=True)

            evidence.update(
                {
                    "status": "PASS",
                    "live": {
                        "badge": "API DATA · WS CONNECTED",
                        "initial_depth_text": initial_depth,
                        "telemetry_response_depth_cm": live_response.get("depthCm"),
                        "ui_depth_text": live_ui_depth,
                        "event_requests_before_fallback": live_event_requests,
                    },
                    "rest_fallback": {
                        "badge": "API DATA · WS FALLBACK",
                        "telemetry_response_depth_cm": degraded_response.get("depthCm"),
                        "ui_depth_text": "41.2cm",
                        "event_requests_before_fallback": degraded_before,
                        "event_requests_after_immediate_reload": immediate_refresh_requests,
                        "event_requests_after_5s_poll": degraded_after,
                        "polling_request_observed": degraded_after > immediate_refresh_requests,
                    },
                    "reconnected": {
                        "badge": "API DATA · WS CONNECTED",
                        "event_requests_at_connect": connected_event_requests,
                        "event_requests_after_6s": quiet_event_requests,
                        "polling_stopped": quiet_event_requests == connected_event_requests,
                        "telemetry_response_depth_cm": resumed_response.get("depthCm"),
                        "ui_depth_text": read_depth(page),
                    },
                    "console_errors": console_errors,
                    "page_errors": page_errors,
                    "screenshots": [
                        str(EVIDENCE_DIR / "api-realtime-live.png"),
                        str(EVIDENCE_DIR / "api-realtime-rest-fallback.png"),
                        str(EVIDENCE_DIR / "api-realtime-reconnected.png"),
                    ],
                }
            )
            if not bool(evidence["reconnected"]["polling_stopped"]):
                raise AssertionError("REST polling continued after WS reconnection")
    except Exception as error:
        evidence.update({"status": "FAIL", "error": str(error)})
        raise
    finally:
        stop_process(frontend)
        stop_process(backend)
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        EVIDENCE_PATH.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"evidence={EVIDENCE_PATH}")
        print(f"status={evidence['status']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
