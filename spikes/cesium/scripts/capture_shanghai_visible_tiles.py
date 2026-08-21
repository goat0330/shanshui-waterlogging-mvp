"""Capture the Shanghai 3D Tiles requested by the fixed L1 demo views.

This is a bounded viewport cache, not a complete Shanghai mirror.  It keeps the
remote URL path below public/data/tiles/shanghai-aoi so relative references in
the captured tileset JSON continue to work when served by Vite.
"""

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

from playwright.sync_api import sync_playwright


URL = "http://127.0.0.1:4173/"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
APP_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = APP_ROOT / "public" / "data" / "tiles" / "shanghai-aoi"
REMOTE_PREFIX = "/3dtiles/jzw-shanghai/"


def relative_tile_path(url: str) -> Path | None:
    parsed = urlparse(url)
    path = unquote(parsed.path)
    if not path.startswith(REMOTE_PREFIX):
        return None
    relative = Path(path[len(REMOTE_PREFIX) :])
    if not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
        return None
    return relative


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    records: dict[str, dict[str, object]] = {}
    capture_phase = "overview"
    failed: list[tuple[int, str]] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=CHROME)
        page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)

        def capture(response) -> None:
            nonlocal records
            relative = relative_tile_path(response.url)
            if relative is None:
                return
            if response.status >= 400:
                failed.append((response.status, response.url))
                return
            key = str(relative).replace("\\", "/")
            if key in records:
                records[key]["phases"] = sorted({*records[key]["phases"], capture_phase})
                return
            try:
                body = response.body()
                target = OUTPUT_ROOT / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(body)
                records[key] = {
                    "url": response.url,
                    "relative_path": key,
                    "bytes": len(body),
                    "status": response.status,
                    "content_type": response.headers.get("content-type", ""),
                    "phases": [capture_phase],
                }
            except Exception as error:
                failed.append((response.status, f"{response.url} ({error})"))

        page.on("response", capture)
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_function(
            "document.querySelector('#sceneStatus')?.textContent !== '加载中' && "
            "document.querySelector('#sceneStatus')?.textContent !== '初始化中'",
            timeout=60000,
        )
        page.wait_for_timeout(8000)
        print("overview_status=", page.locator("#sceneStatus").inner_text(), flush=True)

        capture_phase = "event"
        page.click("#flyToEvent")
        page.wait_for_timeout(10000)
        print("event_log=", page.locator("#logLine").inner_text(), flush=True)
        browser.close()

    manifest = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "source": "https://data.mars3d.cn/3dtiles/jzw-shanghai/tileset.json",
        "cache_type": "fixed-view visible tile cache",
        "scope": {
            "viewport": "1920x1080",
            "overview_camera": "Shanghai overview from the L1 PoC",
            "event_camera": "人民路 × 滨江大道 (121.4874, 31.2297)",
            "warning": "Not a complete Shanghai AOI mirror; files outside the captured LOD/view may be absent.",
        },
        "file_count": len(records),
        "total_bytes": sum(int(item["bytes"]) for item in records.values()),
        "failed_responses": failed,
        "files": sorted(records.values(), key=lambda item: str(item["relative_path"])),
    }
    (OUTPUT_ROOT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("cache_root=", OUTPUT_ROOT, flush=True)
    print("file_count=", manifest["file_count"], flush=True)
    print("total_bytes=", manifest["total_bytes"], flush=True)
    print("failed_responses=", failed, flush=True)


if __name__ == "__main__":
    main()
