from pathlib import Path
import sys

from playwright.sync_api import sync_playwright


URL = "http://127.0.0.1:4173/"
SCREENSHOT = Path(__file__).resolve().parents[1] / "review" / "l1-shanghai.png"
SHADER_SCREENSHOT = SCREENSHOT.with_name("l1-shanghai-shader.png")
CORE_SCREENSHOT = SCREENSHOT.with_name("l1-core-not-ready.png")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    page_errors: list[str] = []
    tile_responses: list[tuple[int, str]] = []
    tile_bytes: list[tuple[int, str, int]] = []
    core_tile_responses: list[tuple[int, str]] = []
    bad_responses: list[tuple[int, str]] = []
    local_bad_responses: list[tuple[int, str]] = []
    test_phase = "online"
    online_console_errors: list[tuple[str, dict]] = []
    offline_console_errors: list[tuple[str, dict]] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=CHROME)
        page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
        page.on(
            "console",
            lambda message: (
                online_console_errors.append((message.text, message.location))
                if test_phase == "online"
                else offline_console_errors.append((message.text, message.location)),
            )
            if message.type == "error"
            else None,
        )
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        def record_tile(response) -> None:
            if "/data/runtime/shanghai-core/" in response.url:
                core_tile_responses.append((response.status, response.url))
            if "jzw-shanghai" not in response.url:
                return
            tile_responses.append((response.status, response.url))
            try:
                tile_bytes.append((response.status, response.url, len(response.body())))
            except Exception:
                pass

        page.on("response", record_tile)
        page.on(
            "response",
            lambda response: bad_responses.append((response.status, response.url))
            if response.status >= 400
            else None,
        )
        page.on(
            "response",
            lambda response: local_bad_responses.append((response.status, response.url))
            if "data/tiles/shanghai-aoi" in response.url and response.status >= 400
            else None,
        )

        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_function(
            "document.querySelector('#sceneStatus')?.textContent !== '加载中' && "
            "document.querySelector('#sceneStatus')?.textContent !== '初始化中'",
            timeout=60000,
        )
        page.wait_for_timeout(8000)

        print("status=", page.locator("#sceneStatus").inner_text(), flush=True)
        print("log=", page.locator("#logLine").inner_text(), flush=True)
        print("tiles_responses=", tile_responses[:10], flush=True)
        print("tile_response_count=", len(tile_responses), flush=True)
        overview_tile_bytes_total = sum(item[2] for item in tile_bytes)
        print("tile_bytes_total=", overview_tile_bytes_total, flush=True)
        print("tile_bytes=", tile_bytes[:10], flush=True)
        print("bad_responses=", bad_responses[:10], flush=True)
        print(
            "render_error_panel=",
            page.get_by_text("An error occurred while rendering").count(),
            flush=True,
        )
        SCREENSHOT.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(SCREENSHOT), full_page=True)

        page.select_option("#materialSelect", "shader")
        page.wait_for_timeout(1800)
        shader_log = page.locator("#logLine").inner_text()
        page.screenshot(path=str(SHADER_SCREENSHOT), full_page=True)
        print("shader_log=", shader_log, flush=True)
        print("shader_screenshot=", SHADER_SCREENSHOT, flush=True)
        assert "material=blue-gray shader" in shader_log
        page.select_option("#materialSelect", "style")
        page.wait_for_timeout(800)

        page.locator('input[data-layer="city"]').uncheck()
        page.wait_for_timeout(1000)
        page.locator('input[data-layer="city"]').check()
        print("city_layer_toggle=passed", flush=True)

        page.click('button[data-forecast="PLUS_10"]')
        print("forecast_plus10_depth=", page.locator("#depthValue").inner_text(), flush=True)
        page.click('button[data-forecast="PLUS_30"]')
        print("forecast_plus30_depth=", page.locator("#depthValue").inner_text(), flush=True)
        print("forecast_log=", page.locator("#logLine").inner_text(), flush=True)

        page.click("#flyToEvent")
        page.wait_for_timeout(1800)
        event_tile_bytes = sum(item[2] for item in tile_bytes)
        print("event_tile_bytes_total=", event_tile_bytes, flush=True)
        print("event_tile_bytes_delta=", event_tile_bytes - overview_tile_bytes_total, flush=True)
        page.screenshot(path=str(SCREENSHOT.with_name("l1-event.png")), full_page=True)
        print("flyto_log=", page.locator("#logLine").inner_text(), flush=True)

        test_phase = "offline"
        page.route("https://data.mars3d.cn/**", lambda route: route.abort())
        page.route("https://data.marsgis.cn/**", lambda route: route.abort())
        page.select_option("#sourceSelect", "shanghai-local")
        page.click("#reloadSource")
        page.wait_for_timeout(8000)
        page.screenshot(path=str(SCREENSHOT.with_name("l1-local-tiles.png")), full_page=True)
        print("local_tiles_status=", page.locator("#sceneStatus").inner_text(), flush=True)
        print("local_tiles_log=", page.locator("#logLine").inner_text(), flush=True)
        print("local_tiles_bad_responses=", local_bad_responses[:20], flush=True)

        page.select_option("#sourceSelect", "shanghai-core")
        page.click("#reloadSource")
        page.wait_for_function(
            "document.querySelector('#sceneStatus')?.textContent !== '加载中'",
            timeout=60000,
        )
        page.wait_for_timeout(8000)
        core_status = page.locator("#sceneStatus").inner_text()
        core_log = page.locator("#logLine").inner_text()
        page.screenshot(path=str(CORE_SCREENSHOT), full_page=True)
        print("core_local_status=", core_status, flush=True)
        print("core_local_log=", core_log, flush=True)
        print("core_local_screenshot=", CORE_SCREENSHOT, flush=True)
        print("core_tile_responses=", core_tile_responses, flush=True)
        if "本地核心模型尚未就绪" in core_status:
            assert "source=core local" in core_log
            assert "/data/runtime/shanghai-core/tileset.json" in core_log
        else:
            assert core_status == "已加载"
            assert "source=Shanghai Core Local · core local" in core_log
            assert any(status == 200 and ".b3dm" in url for status, url in core_tile_responses)
        
        page.select_option("#sourceSelect", "local")
        page.click("#reloadSource")
        page.wait_for_timeout(1800)
        page.screenshot(path=str(SCREENSHOT.with_name("l1-local-fallback.png")), full_page=True)
        print("local_fallback_status=", page.locator("#sceneStatus").inner_text(), flush=True)
        print("local_fallback_log=", page.locator("#logLine").inner_text(), flush=True)
        print("online_console_errors=", online_console_errors[:10], flush=True)
        print("offline_expected_console_errors=", offline_console_errors[:10], flush=True)
        print("page_errors=", page_errors[:10], flush=True)

        browser.close()


if __name__ == "__main__":
    main()
