from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright


URL = "http://127.0.0.1:5173/"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
OUT = Path(__file__).resolve().parent


def main() -> int:
    errors: list[str] = []
    page_errors: list[str] = []
    forecast_requests: list[dict[str, object]] = []
    result: dict[str, object] = {"status": "RUNNING", "url": URL}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=CHROME)
        page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
        page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "response",
            lambda response: forecast_requests.append({"url": response.url, "status": response.status})
            if "/demo/forecast/" in response.url
            else None,
        )
        page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_selector(".cesium-scene-mount", timeout=60_000)
        page.wait_for_function(
            "() => document.querySelector('.cesium-scene-mount')?.dataset.forecastStatus === 'ready'",
            timeout=60_000,
        )
        mount = page.locator(".cesium-scene-mount")
        result["mount_count"] = mount.count()
        result["canvas_count"] = mount.locator("canvas").count()
        result["scene_source"] = mount.get_attribute("data-source")
        result["initial_forecast"] = mount.get_attribute("data-forecast-source")
        result["initial_forecast_status"] = mount.get_attribute("data-forecast-status")

        states: list[dict[str, object]] = []
        for index, (label, expected) in enumerate((("PLUS_30", "+30 min"), ("NOW", "NOW"), ("PLUS_10", "+10 min"))):
            button = page.locator(".timeline-forecast-switcher button").filter(has_text=expected)
            if button.count() != 1:
                raise AssertionError(f"forecast button missing: {label} / {expected}")
            button.click()
            page.wait_for_function(
                "expected => document.querySelector('.cesium-scene-mount')?.dataset.forecastSource === expected",
                arg=label,
                timeout=20_000,
            )
            page.wait_for_function(
                "() => document.querySelector('.cesium-scene-mount')?.dataset.forecastStatus === 'ready'",
                timeout=20_000,
            )
            page.screenshot(path=str(OUT / f"forecast-{label.lower()}-1920x1080.png"), full_page=True)
            states.append(
                {
                    "key": label,
                    "scene_source": mount.get_attribute("data-source"),
                    "forecast_source": mount.get_attribute("data-forecast-source"),
                    "forecast_status": mount.get_attribute("data-forecast-status"),
                }
            )

        canvas = mount.locator("canvas").first
        box = canvas.bounding_box()
        if box:
            x = box["x"] + box["width"] * 0.5
            y = box["y"] + box["height"] * 0.5
            page.mouse.move(x, y)
            page.mouse.down()
            page.mouse.move(x + 140, y + 30, steps=8)
            page.mouse.up()
            page.wait_for_timeout(1000)

        result.update(
            {
                "status": "PASS" if not errors and not page_errors else "CONDITIONAL",
                "forecast_states": states,
                "forecast_requests": forecast_requests,
                "console_errors": errors,
                "page_errors": page_errors,
                "camera_gesture": bool(box),
                "screenshots": [str(OUT / f"forecast-{key.lower()}-1920x1080.png") for key in ("PLUS_30", "NOW", "PLUS_10")],
            }
        )
        browser.close()

    (OUT / "rc0-cesium-geographic-smoke.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
