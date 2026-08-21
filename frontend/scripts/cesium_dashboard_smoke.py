from pathlib import Path
import sys
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


URL = "http://127.0.0.1:5173/"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
SCREENSHOT = Path(__file__).resolve().parents[1] / "review" / "dashboard-cesium-1920x1080.png"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    responses: list[tuple[int, str]] = []
    ion_statuses: list[int] = []
    ion_paths: list[str] = []
    console_errors: list[str] = []
    page_errors: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=CHROME)
        page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        def on_response(response) -> None:
            if "/data/shanghai-core/" in response.url:
                responses.append((response.status, response.url))
            parsed = urlsplit(response.url)
            if parsed.hostname and parsed.hostname.endswith("cesium.com"):
                ion_statuses.append(response.status)
                ion_paths.append(f"{parsed.hostname}{parsed.path}")

        page.on("response", on_response)
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_selector(".cesium-scene-mount", timeout=60000)
        page.wait_for_timeout(30000)
        SCREENSHOT.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(SCREENSHOT), full_page=True)
        print("cesium_mount_count=", page.locator(".cesium-scene-mount").count(), flush=True)
        print("placeholder_count=", page.locator(".scene-placeholder-stamp").count(), flush=True)
        print("scene_source=", page.locator(".cesium-scene-mount").get_attribute("data-source"), flush=True)
        print("osm_source_badge=", page.locator(".cesium-scene-source").count(), flush=True)
        print("cesium_external_response_count=", len(ion_statuses), flush=True)
        print("cesium_external_statuses=", ion_statuses, flush=True)
        print("cesium_external_paths=", ion_paths[:40], flush=True)
        print("core_responses=", responses, flush=True)
        print("core_b3dm_200=", sum(1 for status, url in responses if status == 200 and ".b3dm" in url), flush=True)
        print("console_errors=", console_errors, flush=True)
        print("page_errors=", page_errors, flush=True)
        print("screenshot=", SCREENSHOT, flush=True)
        browser.close()


if __name__ == "__main__":
    main()
