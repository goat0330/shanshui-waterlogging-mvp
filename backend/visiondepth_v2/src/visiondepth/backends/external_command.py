from __future__ import annotations

import json
import subprocess
from pathlib import Path


class ExternalCommandBackend:
    """License-gated subprocess seam; it does not vendor a third-party model."""

    def __init__(
        self,
        command_template: list[str],
        license_approved: bool = False,
        timeout_seconds: int = 120,
    ) -> None:
        if not license_approved:
            raise PermissionError("THIRD_PARTY_LICENSE_NOT_APPROVED")
        if not command_template:
            raise ValueError("external command template must not be empty")
        self.command_template = command_template
        self.timeout_seconds = timeout_seconds

    def run(
        self,
        input_path: str | Path,
        mask_path: str | Path,
        metadata_path: str | Path,
    ) -> dict[str, object]:
        substitutions = {
            "{input}": str(input_path),
            "{mask}": str(mask_path),
            "{json}": str(metadata_path),
        }
        command = [
            part.replace("{input}", substitutions["{input}"])
            .replace("{mask}", substitutions["{mask}"])
            .replace("{json}", substitutions["{json}"])
            for part in self.command_template
        ]
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        if process.returncode != 0:
            raise RuntimeError("EXTERNAL_BACKEND_FAILED: " + process.stderr[-2000:])
        metadata = Path(metadata_path)
        if not metadata.is_file():
            return {}
        value = json.loads(metadata.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("external backend metadata must be a JSON object")
        return value
