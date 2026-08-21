from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("rc0_chain_helpers", HERE / "rc0-60-second-chain.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load chain helpers")
CHAIN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHAIN)


def main() -> int:
    backend_port = CHAIN.free_port()
    frontend_port = CHAIN.free_port()
    while frontend_port == backend_port:
        frontend_port = CHAIN.free_port()
    backend = None
    frontend = None
    events: list[dict[str, object]] = []
    errors: list[str] = []
    page_errors: list[str] = []
    result: dict[str, object] = {"status": "RUNNING", "backend_port": backend_port, "frontend_port": frontend_port}
    start = time.monotonic()

    def mark(page, name: str, **details: object) -> None:
        events.append({"elapsed_s": round(time.monotonic() - rehearsal_start, 1), "name": name, **details})
        page.screenshot(path=str(HERE / f"5m-{len(events):02d}-{name}.png"), full_page=True)

    try:
        backend = CHAIN.start_backend(backend_port)
        CHAIN.wait_http(f"http://127.0.0.1:{backend_port}/api/v1/dashboard/overview", backend)
        frontend = CHAIN.start_frontend(frontend_port, backend_port)
        frontend_url = f"http://127.0.0.1:{frontend_port}/"
        CHAIN.wait_http(frontend_url, frontend)
        launch = {"headless": True}
        if CHAIN.CHROME.exists():
            launch["executable_path"] = str(CHAIN.CHROME)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(**launch)
            page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
            page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.goto(frontend_url, wait_until="domcontentloaded", timeout=60_000)
            CHAIN.wait_badge(page, "WS CONNECTED")
            page.wait_for_function("() => document.querySelector('.cesium-scene-mount')?.dataset.forecastStatus === 'ready'", timeout=90_000)
            page.wait_for_function("() => document.querySelector('.cesium-scene-mount')?.dataset.source !== 'loading'", timeout=90_000)
            rehearsal_start = time.monotonic()
            mark(page, "00-dashboard", badge=page.locator(".dashboard-demo-badge").inner_text(), scene=page.locator(".cesium-scene-mount").get_attribute("data-source"))

            for step in range(1, 11):
                page.wait_for_timeout(30_000)
                if step == 1:
                    mark(page, "01-city-rainfall", status=page.locator(".status-panel").count(), rainfall=page.locator(".rainfall-panel").count())
                elif step == 2:
                    if "人民路" not in page.locator(".event-panel").inner_text():
                        raise AssertionError("selected FP-001 event not present")
                    mark(page, "02-fp001-flyto", event="FP-001", event_panel="present")
                elif step == 3:
                    response = CHAIN.post_observation(f"http://127.0.0.1:{backend_port}", 120, 701)
                    CHAIN.wait_depth(page, "12.0")
                    mark(page, "03-telemetry-12cm", response_depth_cm=response.get("depthCm"), ui_depth="12.0cm")
                elif step == 4:
                    response = CHAIN.post_observation(f"http://127.0.0.1:{backend_port}", 286, 702)
                    CHAIN.wait_depth(page, "28.6")
                    mark(page, "04-telemetry-28-6cm", response_depth_cm=response.get("depthCm"), ui_depth="28.6cm")
                elif step == 5:
                    CHAIN.switch_forecast(page, "PLUS_10", "+10 min")
                    mark(page, "05-forecast-plus10", forecast="PLUS_10")
                elif step == 6:
                    CHAIN.switch_forecast(page, "PLUS_30", "+30 min")
                    mark(page, "06-forecast-plus30", forecast="PLUS_30")
                elif step == 7:
                    CHAIN.switch_forecast(page, "NOW", "NOW")
                    mark(page, "07-return-now", forecast="NOW")
                elif step == 8:
                    mark(page, "08-cctv-ai", cctv_panel=page.locator(".cctv-panel").count(), ai_panel=page.locator(".analysis-panel").count(), cctv_semantics="placeholder-conditional")
                elif step == 9:
                    mark(page, "09-stable-realtime", badge=page.locator(".dashboard-demo-badge").inner_text())
                else:
                    mark(page, "10-final-return", badge=page.locator(".dashboard-demo-badge").inner_text(), forecast=page.locator(".cesium-scene-mount").get_attribute("data-forecast-source"))
            browser.close()

        elapsed = round(time.monotonic() - rehearsal_start, 1)
        result.update({"status": "PASS" if not page_errors else "CONDITIONAL", "elapsed_s": elapsed, "events": events, "console_errors": errors, "page_errors": page_errors, "screenshots": [str(path) for path in sorted(HERE.glob("5m-*.png"))]})
    except Exception as error:
        result.update({"status": "FAIL", "error": str(error), "events": events, "console_errors": errors, "page_errors": page_errors})
        raise
    finally:
        CHAIN.stop_process(frontend)
        CHAIN.stop_process(backend)
        (HERE / "5-minute-rehearsal.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        lines = ["# RC0 5-minute rehearsal", "", f"Status: `{result['status']}`", f"Elapsed: `{result.get('elapsed_s', 'NOT VERIFIED')}s`", "", "| Elapsed (s) | Step | Evidence |", "|---:|---|---|"]
        for event in events:
            lines.append(f"| {event['elapsed_s']} | {event['name']} | " + ", ".join(f"{key}={value}" for key, value in event.items() if key not in {"elapsed_s", "name"}) + " |")
        lines.extend(["", "Expected degraded/network console entries (if any):", "```text", *errors, "```", "", "Page errors:", "```text", *page_errors, "```"])
        (HERE / "5-minute-rehearsal.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
