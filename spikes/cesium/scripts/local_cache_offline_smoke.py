from pathlib import Path
import sys

from playwright.sync_api import sync_playwright


URL = "http://127.0.0.1:4173/"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
SCREENSHOT = Path(__file__).resolve().parents[1] / "review" / "l1-local-offline.png"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    local_responses: list[tuple[int, str]] = []
    local_bad: list[tuple[int, str]] = []
    local_failed: list[str] = []
    console_errors: list[str] = []
    page_errors: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=CHROME)
        page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
        page.route("https://data.mars3d.cn/**", lambda route: route.abort())
        page.route("https://data.marsgis.cn/**", lambda route: route.abort())
        page.on(
            "response",
            lambda response: (
                local_responses.append((response.status, response.url)),
                local_bad.append((response.status, response.url)) if response.status >= 400 else None,
            )
            if "/data/tiles/shanghai-aoi/" in response.url
            else None,
        )
        page.on(
            "requestfailed",
            lambda request: local_failed.append(f"{request.url} :: {request.failure}" )
            if "/data/tiles/shanghai-aoi/" in request.url
            else None,
        )
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.on("pageerror", lambda error: page_errors.append(str(error)))

        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)
        page.select_option("#sourceSelect", "shanghai-local")
        page.click("#reloadSource")
        page.wait_for_timeout(10000)
        SCREENSHOT.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(SCREENSHOT), full_page=True)
        print("status=", page.locator("#sceneStatus").inner_text(), flush=True)
        print("log=", page.locator("#logLine").inner_text(), flush=True)
        print("local_response_count=", len(local_responses), flush=True)
        print("local_bad_responses=", local_bad, flush=True)
        print("local_failed_requests=", local_failed, flush=True)
        print("console_errors=", console_errors, flush=True)
        print("page_errors=", page_errors, flush=True)
        browser.close()


if __name__ == "__main__":
    main()
