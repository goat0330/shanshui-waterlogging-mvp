"""Backend boundary for the existing VisionDepth V1 evidence pipeline."""

from __future__ import annotations

import ipaddress
import mimetypes
import socket
import sys
import tempfile
import uuid
from pathlib import Path
from urllib.parse import urljoin, urlparse

from fastapi import UploadFile
import requests

from .models import VisionDepthObservation

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from vision.ingest import ALLOWED_FORMATS, ImageInputError, MAX_BYTES, is_http_url  # noqa: E402
from vision.pipeline import run_pipeline  # noqa: E402


_ALLOWED_UPLOAD_MEDIA_TYPES = set(ALLOWED_FORMATS.values())
_MEDIA_TYPE_ALIASES = {"image/jpg": "image/jpeg"}
_MEDIA_SUFFIXES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
_MAX_REDIRECTS = 3


class VisionDepthError(Exception):
    """An explicit API-facing error from the evidence boundary."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code

    def detail(self) -> dict[str, str]:
        return {"code": self.code, "message": str(self)}


class VisionDepthAdapter:
    """Call the existing VisionDepth pipeline without coupling it to telemetry."""

    def __init__(self, output_dir: Path | None = None) -> None:
        self.output_dir = output_dir or Path(__file__).resolve().parents[1] / ".runtime" / "vision-depth"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _image_id(image_id: str | None) -> str:
        if image_id is None:
            return f"IMG-API-{uuid.uuid4().hex[:12]}"
        value = image_id.strip()
        if not value:
            raise VisionDepthError(400, "VISION_INVALID_INPUT", "imageId must not be empty")
        return value

    @staticmethod
    def _media_type(file: UploadFile) -> str:
        declared = (file.content_type or "").split(";", 1)[0].strip().lower()
        declared = _MEDIA_TYPE_ALIASES.get(declared, declared)
        if not declared:
            declared = mimetypes.guess_type(file.filename or "")[0] or ""
            declared = _MEDIA_TYPE_ALIASES.get(declared.lower(), declared.lower())
        if declared not in _ALLOWED_UPLOAD_MEDIA_TYPES:
            raise VisionDepthError(
                415,
                "VISION_UNSUPPORTED_MEDIA_TYPE",
                "upload must use image/jpeg, image/png, or image/webp",
            )
        return declared

    def _output_path(self, image_id: str) -> Path:
        return self.output_dir / f"{uuid.uuid4().hex}.json"

    @staticmethod
    def _blocked_ip(address: str) -> bool:
        ip = ipaddress.ip_address(address)
        return not ip.is_global

    @classmethod
    def _validate_public_url(cls, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            raise VisionDepthError(400, "VISION_INVALID_URL", "url must be an HTTP or HTTPS image URL")
        hostname = parsed.hostname
        if not hostname:
            raise VisionDepthError(400, "VISION_INVALID_URL", "url must include a host")
        hostname = hostname.rstrip(".").lower()
        if hostname == "localhost" or hostname.endswith(".localhost") or hostname.endswith(".local"):
            raise VisionDepthError(400, "VISION_PRIVATE_URL", "private or local URL targets are not allowed")
        try:
            port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
            addresses = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
        except (socket.gaierror, UnicodeError, ValueError) as exc:
            raise VisionDepthError(502, "VISION_FETCH_FAILED", "could not resolve image URL host") from exc
        if not addresses:
            raise VisionDepthError(502, "VISION_FETCH_FAILED", "image URL host did not resolve")
        for address in {entry[4][0] for entry in addresses}:
            try:
                blocked = cls._blocked_ip(address)
            except ValueError as exc:
                raise VisionDepthError(400, "VISION_INVALID_URL", "image URL host is invalid") from exc
            if blocked:
                raise VisionDepthError(400, "VISION_PRIVATE_URL", "private or reserved URL targets are not allowed")

    @staticmethod
    def _response_media_type(response: requests.Response) -> str:
        media_type = (response.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
        media_type = _MEDIA_TYPE_ALIASES.get(media_type, media_type)
        if media_type not in _ALLOWED_UPLOAD_MEDIA_TYPES:
            raise VisionDepthError(
                400,
                "VISION_INVALID_MEDIA",
                "URL must return image/jpeg, image/png, or image/webp",
            )
        return media_type

    @classmethod
    def _download_public_url(cls, url: str) -> tuple[bytes, str]:
        current_url = url
        session = requests.Session()
        session.trust_env = False
        try:
            for redirect_count in range(_MAX_REDIRECTS + 1):
                cls._validate_public_url(current_url)
                try:
                    with session.get(
                        current_url,
                        stream=True,
                        timeout=(5, 20),
                        allow_redirects=False,
                        headers={"Accept": "image/jpeg,image/png,image/webp", "User-Agent": "VisionDepthV1/0.1"},
                    ) as response:
                        if 300 <= response.status_code < 400:
                            location = response.headers.get("Location")
                            if not location or redirect_count >= _MAX_REDIRECTS:
                                raise VisionDepthError(400, "VISION_INVALID_URL", "image URL redirect chain is invalid")
                            current_url = urljoin(current_url, location)
                            continue
                        response.raise_for_status()
                        media_type = cls._response_media_type(response)
                        declared_length = response.headers.get("Content-Length")
                        if declared_length:
                            try:
                                if int(declared_length) > MAX_BYTES:
                                    raise VisionDepthError(
                                        400,
                                        "VISION_IMAGE_TOO_LARGE",
                                        f"image exceeds {MAX_BYTES // (1024 * 1024)} MB limit",
                                    )
                            except ValueError as exc:
                                raise VisionDepthError(400, "VISION_INVALID_MEDIA", "invalid image Content-Length") from exc
                        chunks: list[bytes] = []
                        total = 0
                        for chunk in response.iter_content(chunk_size=64 * 1024):
                            if not chunk:
                                continue
                            total += len(chunk)
                            if total > MAX_BYTES:
                                raise VisionDepthError(
                                    400,
                                    "VISION_IMAGE_TOO_LARGE",
                                    f"image exceeds {MAX_BYTES // (1024 * 1024)} MB limit",
                                )
                            chunks.append(chunk)
                        return b"".join(chunks), media_type
                except VisionDepthError:
                    raise
                except requests.RequestException as exc:
                    raise VisionDepthError(502, "VISION_FETCH_FAILED", f"image download failed: {exc}") from exc
            raise VisionDepthError(400, "VISION_INVALID_URL", "image URL redirect chain is too long")
        finally:
            session.close()

    def _run(self, source: str, source_type: str, source_value: str, image_id: str) -> VisionDepthObservation:
        try:
            observation = run_pipeline(source, self._output_path(image_id), image_id=image_id)
        except ImageInputError as exc:
            message = str(exc)
            if source_type == "url" and "image download failed" in message:
                raise VisionDepthError(502, "VISION_FETCH_FAILED", message) from exc
            if "exceeds" in message and source_type == "local":
                raise VisionDepthError(413, "VISION_IMAGE_TOO_LARGE", message) from exc
            raise VisionDepthError(400, "VISION_INVALID_MEDIA", message) from exc
        except Exception as exc:  # The algorithm boundary must not leak internal tracebacks.
            raise VisionDepthError(502, "VISION_INFERENCE_FAILED", "VisionDepth inference failed") from exc

        observation["imageId"] = image_id
        observation["source"] = {"type": source_type, "value": source_value}
        license_review = "not_required" if source_type == "local" else "pending"
        observation["provenance"] = {
            "sourceType": "VISION_IMAGE",
            "sourceId": image_id,
            "observedAt": None,
            "licenseReview": license_review,
            "runtimePolicy": "research_mvp",
        }
        try:
            return VisionDepthObservation.model_validate(observation)
        except Exception as exc:
            raise VisionDepthError(502, "VISION_INVALID_RESULT", "VisionDepth result did not match Contract") from exc

    async def analyze_upload(self, file: UploadFile, image_id: str | None = None) -> VisionDepthObservation:
        """Persist one bounded upload temporarily, then call the shared pipeline."""

        media_type = self._media_type(file)
        raw = await file.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise VisionDepthError(
                413,
                "VISION_IMAGE_TOO_LARGE",
                f"image exceeds {MAX_BYTES // (1024 * 1024)} MB limit",
            )

        normalized_id = self._image_id(image_id)
        source_value = Path(file.filename or "upload").name or "upload"
        suffix = _MEDIA_SUFFIXES[media_type]
        with tempfile.TemporaryDirectory(prefix="vision-depth-upload-") as temp_dir:
            source_path = Path(temp_dir) / f"input{suffix}"
            source_path.write_bytes(raw)
            return self._run(str(source_path), "local", source_value, normalized_id)

    def analyze_url(self, url: str, image_id: str | None = None) -> VisionDepthObservation:
        normalized_url = url.strip()
        if not is_http_url(normalized_url):
            raise VisionDepthError(400, "VISION_INVALID_URL", "url must be an HTTP or HTTPS image URL")
        normalized_id = self._image_id(image_id)
        raw, media_type = self._download_public_url(normalized_url)
        suffix = _MEDIA_SUFFIXES[media_type]
        with tempfile.TemporaryDirectory(prefix="vision-depth-url-") as temp_dir:
            source_path = Path(temp_dir) / f"input{suffix}"
            source_path.write_bytes(raw)
            return self._run(str(source_path), "url", normalized_url, normalized_id)
