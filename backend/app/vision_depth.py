"""Backend boundary for the existing VisionDepth V1 evidence pipeline."""

from __future__ import annotations

import mimetypes
import sys
import tempfile
import uuid
from pathlib import Path

from fastapi import UploadFile

from .models import VisionDepthObservation

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from vision.ingest import ALLOWED_FORMATS, ImageInputError, MAX_BYTES, is_http_url  # noqa: E402
from vision.pipeline import run_pipeline  # noqa: E402


_ALLOWED_UPLOAD_MEDIA_TYPES = set(ALLOWED_FORMATS.values())
_MEDIA_TYPE_ALIASES = {"image/jpg": "image/jpeg"}
_MEDIA_SUFFIXES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


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
        return self._run(normalized_url, "url", normalized_url, normalized_id)
