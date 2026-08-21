from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
OUT = Path(__file__).resolve().parent
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def start_backend(port: int, websocket_enabled: bool = True) -> subprocess.Popen[bytes]:
    command = [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)]
    if not websocket_enabled:
        command.extend(["--ws", "none"])
    env = os.environ.copy()
    env["REPOSITORY_BACKEND"] = "memory"
    return subprocess.Popen(command, cwd=BACKEND_DIR, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def start_frontend(port: int, backend_port: int) -> subprocess.Popen[bytes]:
    npm = "npm.cmd" if os.name == "nt" else "npm"
    env = os.environ.copy()
    env.update({"VITE_DATA_SOURCE": "api", "VITE_API_BASE_URL": f"http://127.0.0.1:{backend_port}"})
    return subprocess.Popen(
        [npm, "run", "dev", "--", "--host", "127.0.0.1", "--port", str(port), "--strictPort"],
        cwd=FRONTEND_DIR,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def stop_process(process: subprocess.Popen[bytes] | None) -> None:
    if process is None or process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    else:
        process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def wait_http(url: str, process: subprocess.Popen[bytes], timeout: float = 45) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"service exited with code {process.returncode}: {url}")
        try:
            with urlopen(url, timeout=2) as response:
                if response.status < 500:
                    return
        except OSError:
            pass
        time.sleep(0.25)
    raise TimeoutError(f"timed out waiting for {url}")


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
    request = Request(f"{base_url}/api/v1/telemetry/observations", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode())


def wait_badge(page: Page, text: str, timeout: float = 20_000) -> None:
    page.wait_for_function("expected => document.querySelector('.dashboard-demo-badge')?.textContent?.includes(expected)", arg=text, timeout=timeout)


def wait_depth(page: Page, text: str, timeout: float = 20_000) -> None:
    page.wait_for_function("expected => document.querySelector('.event-panel .event-metric strong')?.textContent?.includes(expected)", arg=text, timeout=timeout)


def switch_forecast(page: Page, key: str, label: str) -> None:
    button = page.locator(".timeline-forecast-switcher button").filter(has_text=label)
    if button.count() != 1:
        raise AssertionError(f"forecast control missing: {key}")
    button.click()
    page.wait_for_function("expected => document.querySelector('.cesium-scene-mount')?.dataset.forecastSource === expected", arg=key, timeout=20_000)
    page.wait_for_function("() => document.querySelector('.cesium-scene-mount')?.dataset.forecastStatus === 'ready'", timeout=20_000)


def main() -> int:
    backend_port = free_port()
    frontend_port = free_port()
    while frontend_port == backend_port:
        frontend_port = free_port()
    backend: subprocess.Popen[bytes] | None = None
    frontend: subprocess.Popen[bytes] | None = None
    events: list[dict[str, object]] = []
    console_errors: list[str] = []
    page_errors: list[str] = []
    started = time.monotonic()
    result: dict[str, object] = {"status": "RUNNING", "backend_port": backend_port, "frontend_port": frontend_port}

    def mark(page: Page, name: str, **details: object) -> None:
        events.append({"elapsed_s": round(time.monotonic() - started, 1), "name": name, **details})
        page.screenshot(path=str(OUT / f"60s-{len(events):02d}-{name}.png"), full_page=True)

    try:
        backend = start_backend(backend_port)
        wait_http(f"http://127.0.0.1:{backend_port}/api/v1/dashboard/overview", backend)
        frontend = start_frontend(frontend_port, backend_port)
        frontend_url = f"http://127.0.0.1:{frontend_port}/"
        wait_http(frontend_url, frontend)
        launch = {"headless": True}
        if CHROME.exists():
            launch["executable_path"] = str(CHROME)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(**launch)
            page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
            page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.goto(frontend_url, wait_until="domcontentloaded", timeout=60_000)
            wait_badge(page, "WS CONNECTED")
            page.wait_for_function("() => document.querySelector('.cesium-scene-mount')?.dataset.forecastStatus === 'ready'", timeout=90_000)
            page.wait_for_function("() => document.querySelector('.cesium-scene-mount')?.dataset.source !== 'loading'", timeout=90_000)
            mark(page, "initial", badge=page.locator(".dashboard-demo-badge").inner_text(), scene_source=page.locator(".cesium-scene-mount").get_attribute("data-source"))

            if "人民路" not in page.locator(".event-panel").inner_text():
                raise AssertionError("FP-001 event panel not selected")
            mark(page, "fp001-selected", event="FP-001", event_panel="人民路 × 滨江大道")

            live = post_observation(f"http://127.0.0.1:{backend_port}", 120, 601)
            wait_depth(page, "12.0")
            mark(page, "telemetry-12cm", response_depth_cm=live.get("depthCm"), ui_depth="12.0cm")

            live = post_observation(f"http://127.0.0.1:{backend_port}", 286, 602)
            wait_depth(page, "28.6")
            mark(page, "telemetry-28-6cm", response_depth_cm=live.get("depthCm"), ui_depth="28.6cm")

            switch_forecast(page, "PLUS_10", "+10 min")
            mark(page, "forecast-plus10", forecast="PLUS_10", scene_source=page.locator(".cesium-scene-mount").get_attribute("data-forecast-source"))
            switch_forecast(page, "PLUS_30", "+30 min")
            mark(page, "forecast-plus30", forecast="PLUS_30", scene_source=page.locator(".cesium-scene-mount").get_attribute("data-forecast-source"))
            switch_forecast(page, "NOW", "NOW")
            mark(page, "forecast-now", forecast="NOW", scene_source=page.locator(".cesium-scene-mount").get_attribute("data-forecast-source"))

            stop_process(backend)
            backend = start_backend(backend_port, websocket_enabled=False)
            wait_http(f"http://127.0.0.1:{backend_port}/api/v1/dashboard/overview", backend)
            wait_badge(page, "WS FALLBACK")
            mark(page, "degraded", badge=page.locator(".dashboard-demo-badge").inner_text())

            stop_process(backend)
            backend = start_backend(backend_port, websocket_enabled=True)
            wait_http(f"http://127.0.0.1:{backend_port}/api/v1/dashboard/overview", backend)
            wait_badge(page, "WS CONNECTED", timeout=20_000)
            mark(page, "return-realtime", badge=page.locator(".dashboard-demo-badge").inner_text())
            browser.close()

        result.update({"status": "PASS" if not page_errors else "CONDITIONAL", "events": events, "console_errors": console_errors, "page_errors": page_errors, "screenshots": [str(path) for path in sorted(OUT.glob("60s-*.png"))]})
    except Exception as error:
        result.update({"status": "FAIL", "error": str(error), "events": events, "console_errors": console_errors, "page_errors": page_errors})
        raise
    finally:
        stop_process(frontend)
        stop_process(backend)
        (OUT / "60-second-chain.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        lines = ["# RC0 60-second chain", "", f"Status: `{result['status']}`", "", "| Elapsed (s) | Step | Evidence |", "|---:|---|---|"]
        for event in events:
            lines.append(f"| {event['elapsed_s']} | {event['name']} | " + ", ".join(f"{key}={value}" for key, value in event.items() if key not in {"elapsed_s", "name"}) + " |")
        lines.extend(["", "Console errors:", "```text", *console_errors, "```", "", "Page errors:", "```text", *page_errors, "```"])
        (OUT / "60-second-chain.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
