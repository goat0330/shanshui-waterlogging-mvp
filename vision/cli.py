"""Command-line entry point for VisionDepth V1."""

from __future__ import annotations

import argparse
import json
import sys

from .ingest import ImageInputError
from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Estimate coarse flood depth from one JPEG/PNG/WebP image.")
    parser.add_argument("--input", required=True, help="local image path or HTTP/HTTPS image URL")
    parser.add_argument("--output", default="vision/artifacts/result.json", help="JSON output path")
    parser.add_argument("--image-id", default="IMG-00001", help="stable image identifier")
    parser.add_argument(
        "--save-mask",
        action="store_true",
        help="accepted for explicitness; V1 always saves the mask beside the JSON evidence",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        observation = run_pipeline(args.input, args.output, args.image_id)
    except ImageInputError as exc:
        print(f"VisionDepth input error: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(f"VisionDepth processing error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(observation, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

