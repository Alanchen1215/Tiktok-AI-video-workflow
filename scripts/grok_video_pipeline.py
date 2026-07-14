#!/usr/bin/env python3
"""Generate an image, then animate it with the xAI Grok Imagine API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

API_BASE = "https://api.x.ai/v1"


def request_json(
    method: str,
    url: str,
    api_key: str,
    payload: dict[str, Any] | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Authorization": f"Bearer {api_key}"}
    if payload is not None:
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"xAI API returned HTTP {error.code}: {body}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Could not reach xAI API: {error.reason}") from error


def download(url: str, destination: Path, timeout: int = 300) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "grok-video-workflow/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        destination.write_bytes(response.read())


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-prompt", required=True)
    parser.add_argument("--video-prompt", required=True)
    parser.add_argument("--aspect-ratio", default="9:16")
    parser.add_argument("--image-resolution", choices=("1k", "2k"), default="1k")
    parser.add_argument("--video-resolution", choices=("480p", "720p", "1080p"), default="720p")
    parser.add_argument("--duration", type=int, choices=range(1, 16), default=10)
    parser.add_argument("--image-model", default="grok-imagine-image-quality")
    parser.add_argument("--video-model", default="grok-imagine-video-1.5")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    image_payload = {
        "model": args.image_model,
        "prompt": args.image_prompt,
        "aspect_ratio": args.aspect_ratio,
        "resolution": args.image_resolution,
        "n": 1,
    }
    plan = {
        "image_request": image_payload,
        "video_request": {
            "model": args.video_model,
            "prompt": args.video_prompt,
            "image": {"url": "<generated-image-url>"},
            "duration": args.duration,
            "resolution": args.video_resolution,
        },
        "dry_run": args.dry_run,
    }
    write_json(output_dir / "request-plan.json", plan)

    if args.dry_run:
        print("Dry run complete. Request plan written without calling the xAI API.")
        return 0

    api_key = os.environ.get("XAI_API_KEY", "").strip()
    if not api_key:
        print("XAI_API_KEY is required when dry-run is disabled.", file=sys.stderr)
        return 2

    print("Generating source image...")
    image_response = request_json(
        "POST", f"{API_BASE}/images/generations", api_key, image_payload
    )
    write_json(output_dir / "image-response.json", image_response)
    try:
        image_url = image_response["data"][0]["url"]
    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError(f"Image response did not contain a URL: {image_response}") from error
    download(image_url, output_dir / "source-image.png")

    video_payload = {
        "model": args.video_model,
        "prompt": args.video_prompt,
        "image": {"url": image_url},
        "duration": args.duration,
        "resolution": args.video_resolution,
    }
    print("Starting image-to-video generation...")
    video_start = request_json(
        "POST", f"{API_BASE}/videos/generations", api_key, video_payload
    )
    write_json(output_dir / "video-start-response.json", video_start)
    request_id = video_start.get("request_id")
    if not request_id:
        raise RuntimeError(f"Video response did not contain request_id: {video_start}")

    deadline = time.monotonic() + 30 * 60
    while time.monotonic() < deadline:
        result = request_json(
            "GET", f"{API_BASE}/videos/{request_id}", api_key, timeout=60
        )
        status = result.get("status", "unknown")
        progress = result.get("progress")
        print(f"Video status: {status}; progress: {progress}")
        if status == "done":
            write_json(output_dir / "video-response.json", result)
            try:
                video_url = result["video"]["url"]
            except (KeyError, TypeError) as error:
                raise RuntimeError(f"Completed response had no video URL: {result}") from error
            download(video_url, output_dir / "video.mp4", timeout=600)
            print("Video saved to output/video.mp4")
            return 0
        if status in {"failed", "expired", "cancelled"}:
            write_json(output_dir / "video-response.json", result)
            raise RuntimeError(f"Video generation ended with status {status}: {result}")
        time.sleep(10)

    raise TimeoutError("Video generation did not finish within 30 minutes.")


if __name__ == "__main__":
    raise SystemExit(main())
