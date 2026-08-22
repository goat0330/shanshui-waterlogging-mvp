"""Command-line entry point for offline VisionDepth video evidence."""

from __future__ import annotations

import argparse
import json
import sys

from .video_pipeline import VideoInputError, run_video_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run VisionDepth V1 on sampled frames from a local MP4.")
    parser.add_argument("--input", required=True, help="local MP4 path; webpages and video URLs are not accepted")
    parser.add_argument("--output", default="media/artifacts/video-result.json", help="video result JSON path")
    parser.add_argument("--video-id", default="VID-00001", help="stable video identifier")
    parser.add_argument("--sample-interval-sec", type=float, default=1.0, help="sampling interval in seconds")
    parser.add_argument("--max-frames", type=int, default=60, help="maximum number of sampled frames")
    parser.add_argument(
        "--license-status",
        default="NOT_VERIFIED",
        help="recorded source license state, for example VERIFIED or NOT_VERIFIED",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run_video_pipeline(
            args.input,
            args.output,
            video_id=args.video_id,
            sample_interval_sec=args.sample_interval_sec,
            max_frames=args.max_frames,
            source_license_status=args.license_status,
        )
    except VideoInputError as exc:
        print(f"VisionDepth video input error: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(f"VisionDepth video processing error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
