#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_extract(archive: Path, output: Path) -> None:
    output = output.resolve()
    with zipfile.ZipFile(archive) as zf:
        for member in zf.infolist():
            candidate = (output / member.filename).resolve()
            if output not in candidate.parents and candidate != output:
                raise RuntimeError(f"unsafe zip member: {member.filename}")
        zf.extractall(output)


def truthy(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    bundle = manifest.get("bundle") or {}

    configured_url = os.getenv("MEDIA_BUNDLE_URL", "").strip()
    url = configured_url or str(bundle.get("url") or "").strip()
    configured_hash = os.getenv("MEDIA_BUNDLE_SHA256", "").strip().lower()
    expected_hash = configured_hash or str(bundle.get("sha256") or "").strip().lower()

    env_required = os.getenv("MEDIA_BUNDLE_REQUIRED", "").strip()
    required = truthy(env_required) if env_required else truthy(bundle.get("required"))
    enabled = bool(configured_url) or truthy(bundle.get("enabled"))

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    if not enabled:
        print("RC2.4 media bundle disabled; tracked repository demo assets remain available.")
        return 0

    if not url:
        if required:
            raise RuntimeError("media bundle is required but no URL is configured")
        print("RC2.4 media bundle enabled without URL; continuing without external bundle.")
        return 0

    with tempfile.TemporaryDirectory(prefix="rc24-media-") as tmp:
        archive = Path(tmp) / "media.zip"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "qixiao-rc24-render-build/1.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as response, archive.open("wb") as dst:
                shutil.copyfileobj(response, dst)
        except Exception as exc:
            if required:
                raise RuntimeError(f"required media bundle download failed: {exc}") from exc
            print(f"WARNING: media bundle download failed; continuing without it: {exc}", file=sys.stderr)
            return 0

        actual_hash = sha256(archive)
        print(f"media bundle sha256={actual_hash}")

        if expected_hash and actual_hash != expected_hash:
            raise RuntimeError(
                f"media bundle sha256 mismatch: expected {expected_hash}, got {actual_hash}"
            )

        safe_extract(archive, output)

    print(f"media bundle extracted to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
