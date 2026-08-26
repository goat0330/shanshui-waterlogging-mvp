#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--media-root", required=True)
    args = ap.parse_args()

    repo_root = Path(args.repo_root)
    media_root = Path(args.media_root)

    fixture = repo_root / "contracts" / "fixtures" / "cameras.json"
    if not fixture.exists():
        print("camera fixture missing; no runtime media rewrite")
        return 0

    cameras = json.loads(fixture.read_text(encoding="utf-8"))
    current_video = media_root / "video" / "current" / "flood_cam_017.mp4"
    current_overlay = media_root / "video" / "current" / "flood_cam_017.overlay.json"

    changed = False
    for camera in cameras:
        if camera.get("id") != "CAM-017":
            continue
        if current_video.is_file():
            camera["mediaUrl"] = "/media/video/current/flood_cam_017.mp4"
            changed = True
        if current_overlay.is_file():
            camera["overlayUrl"] = "/media/video/current/flood_cam_017.overlay.json"
            changed = True

    if changed:
        fixture.write_text(json.dumps(cameras, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("RC2.4 camera fixture points to bundled /media current-event asset")
    else:
        print("RC2.4 no bundled current-event video found; tracked /demo/video fallback preserved")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
