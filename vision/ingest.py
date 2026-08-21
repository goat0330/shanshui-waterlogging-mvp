"""Strict local/HTTP image ingestion for VisionDepth."""

from __future__ import annotations

import io
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import requests
from PIL import Image, UnidentifiedImageError


MAX_BYTES = 15 * 1024 * 1024
MAX_PIXELS = 20_000_000
ALLOWED_FORMATS = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


class ImageInputError(ValueError):
    """Raised when an input is not a supported image or cannot be fetched."""


@dataclass(frozen=True)
class IngestedImage:
    rgb: np.ndarray
    source_type: str
    source_value: str
    media_type: str
    width: int
    height: int


def is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme.lower() in {"http", "https"} and bool(parsed.netloc)


def is_windows_drive_path(value: str) -> bool:
    return len(value) >= 3 and value[0].isalpha() and value[1] == ":" and value[2] in {"\\", "/"}


def _media_type(header: str | None) -> str | None:
    if not header:
        return None
    value = header.split(";", 1)[0].strip().lower()
    if value == "image/jpg":
        return "image/jpeg"
    return value


def _decode(raw: bytes, declared_type: str | None, source: str) -> tuple[np.ndarray, str, int, int]:
    if len(raw) > MAX_BYTES:
        raise ImageInputError(f"image exceeds {MAX_BYTES // (1024 * 1024)} MB limit: {source}")
    if declared_type and declared_type not in set(ALLOWED_FORMATS.values()):
        raise ImageInputError(f"URL did not return an allowed image MIME type: {declared_type}")

    try:
        with Image.open(io.BytesIO(raw)) as checked:
            checked.verify()
            image_format = (checked.format or "").upper()
            width, height = checked.size
        if image_format not in ALLOWED_FORMATS:
            raise ImageInputError(f"unsupported image format {image_format or 'unknown'}: {source}")
        if width * height > MAX_PIXELS:
            raise ImageInputError(f"image exceeds {MAX_PIXELS:,} pixel limit: {source}")
        with Image.open(io.BytesIO(raw)) as image:
            rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageInputError(f"response is not a readable JPEG/PNG/WebP image: {source}") from exc

    return rgb, ALLOWED_FORMATS[image_format], width, height


def _read_url(source: str) -> tuple[bytes, str | None]:
    parsed = urlparse(source)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise ImageInputError("URL input must use HTTP or HTTPS")

    try:
        with requests.get(
            source,
            stream=True,
            timeout=(5, 20),
            allow_redirects=True,
            headers={"Accept": "image/jpeg,image/png,image/webp", "User-Agent": "VisionDepthV1/0.1"},
        ) as response:
            response.raise_for_status()
            final = urlparse(response.url)
            if final.scheme.lower() not in {"http", "https"} or not final.netloc:
                raise ImageInputError("redirected URL is not HTTP/HTTPS")
            declared_type = _media_type(response.headers.get("Content-Type"))
            declared_length = response.headers.get("Content-Length")
            if declared_length and int(declared_length) > MAX_BYTES:
                raise ImageInputError(f"image exceeds {MAX_BYTES // (1024 * 1024)} MB limit: {source}")
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_BYTES:
                    raise ImageInputError(f"image exceeds {MAX_BYTES // (1024 * 1024)} MB limit: {source}")
                chunks.append(chunk)
            return b"".join(chunks), declared_type
    except requests.RequestException as exc:
        raise ImageInputError(f"image download failed for {source}: {exc}") from exc


def load_image(source: str) -> IngestedImage:
    """Load exactly one JPEG/PNG/WebP from a local path or an image URL."""

    if is_http_url(source):
        raw, declared_type = _read_url(source)
        rgb, media_type, width, height = _decode(raw, declared_type, source)
        return IngestedImage(rgb, "url", source, media_type, width, height)

    parsed = urlparse(source)
    if parsed.scheme and not is_windows_drive_path(source):
        raise ImageInputError("local input must be a file path; URL schemes must be HTTP/HTTPS")
    path = Path(source).expanduser()
    if not path.is_file():
        raise ImageInputError(f"local image does not exist: {source}")
    if path.stat().st_size > MAX_BYTES:
        raise ImageInputError(f"image exceeds {MAX_BYTES // (1024 * 1024)} MB limit: {source}")
    declared_type = _media_type(mimetypes.guess_type(path.name)[0])
    raw = path.read_bytes()
    rgb, media_type, width, height = _decode(raw, declared_type, str(path))
    return IngestedImage(rgb, "local", source, media_type, width, height)
