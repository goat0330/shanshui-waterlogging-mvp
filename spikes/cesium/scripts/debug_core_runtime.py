from pathlib import Path
import sys

from playwright.sync_api import sync_playwright


URL = "http://127.0.0.1:4173/"
OUT = Path(__file__).resolve().parents[1] / "review" / "debug-core-runtime.png"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    console_messages: list[tuple[str, str]] = []
    page_errors: list[str] = []
    requests: list[tuple[int, str, str]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=CHROME)
        page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
        page.on("console", lambda message: console_messages.append((message.type, message.text)))
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "response",
            lambda response: requests.append((response.status, response.url, response.request.resource_type))
            if "/data/runtime/shanghai-core/" in response.url
            else None,
        )
        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_function(
            "document.querySelector('#sceneStatus')?.textContent !== '加载中'",
            timeout=60000,
        )
        page.wait_for_timeout(1000)
        page.select_option("#sourceSelect", "shanghai-core")
        page.locator("#reloadSource").click()
        page.wait_for_timeout(2500)
        page.locator("#flyToEvent").click()
        page.wait_for_timeout(20000)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(OUT), full_page=True)
        print("status=", page.locator("#sceneStatus").inner_text(), flush=True)
        print("log=", page.locator("#logLine").inner_text(), flush=True)
        print("requests=", requests, flush=True)
        print("console=", console_messages, flush=True)
        print("page_errors=", page_errors, flush=True)
        print("screenshot=", OUT, flush=True)
        browser.close()


if __name__ == "__main__":
    main()
