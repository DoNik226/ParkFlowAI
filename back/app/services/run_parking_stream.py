#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, Optional, Tuple

import cv2

# This worker reuses the already existing detection logic from detect_parking.py.
# Keep detect_parking.py in the same project root when running this file.
from back.app.services.detect_parking import (
    load_layout,
    load_model,
    process_frame,
    save_image,
)


def infer_source_type(source: str) -> str:
    suffix = Path(source).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
        return "image"
    return "stream_or_video"


def load_json_if_exists(path: str) -> Optional[Dict[str, object]]:
    p = Path(path)
    if not p.exists():
        return None
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def extract_status_signature(occupancy: Optional[Dict[str, object]]) -> Optional[Dict[str, str]]:
    if not occupancy or "spots" not in occupancy:
        return None
    signature: Dict[str, str] = {}
    for item in occupancy.get("spots", []):
        if not isinstance(item, dict):
            continue
        spot_id = item.get("spot_id")
        status = item.get("status")
        if spot_id is None or status is None:
            continue
        signature[str(spot_id)] = str(status)
    return signature


def atomic_write_json(data: Dict[str, object], path: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, target)


def make_detection_args(cli: argparse.Namespace) -> SimpleNamespace:
    """Build the args object expected by detect_parking.process_frame()."""
    return SimpleNamespace(
        model=cli.model,
        conf=cli.conf,
        imgsz=cli.imgsz,
        crop_pad=cli.crop_pad,
        spot_margin_px=cli.spot_margin_px,
        spot_margin_m=cli.spot_margin_m,
        overlap_threshold=cli.overlap_threshold,
        nms_iou=cli.nms_iou,
        interval_sec=cli.interval_sec,
        no_zone_crops=cli.no_zone_crops,
        no_enhance_crops=cli.no_enhance_crops,
        no_enhance_full_frame=cli.no_enhance_full_frame,
        save_frame=cli.save_frame,
    )


def process_and_maybe_update(
    *,
    model,
    layout: Dict[str, object],
    frame,
    source: str,
    frame_index: int,
    timestamp_sec: float,
    detection_args: SimpleNamespace,
    output_json: str,
    debug_frame_path: Optional[str],
    previous_signature: Optional[Dict[str, str]],
    write_debug_every_frame: bool,
) -> Tuple[Optional[Dict[str, str]], bool]:
    occupancy, debug = process_frame(
        model=model,
        frame=frame,
        layout=layout,
        source_path=source,
        frame_index=frame_index,
        timestamp_sec=timestamp_sec,
        args=detection_args,
    )

    new_signature = extract_status_signature(occupancy)
    changed = new_signature != previous_signature

    if changed:
        atomic_write_json(occupancy, output_json)

    if debug_frame_path and (changed or write_debug_every_frame):
        save_image(debug, debug_frame_path)

    return new_signature, changed


def run_image_once(cli: argparse.Namespace) -> None:
    layout = load_layout(cli.layout)
    model = load_model(cli.model)
    detection_args = make_detection_args(cli)

    frame = cv2.imread(cli.source)
    if frame is None:
        raise RuntimeError(f"Не удалось прочитать изображение: {cli.source}")

    old_state = load_json_if_exists(cli.save_json)
    prev_signature = extract_status_signature(old_state)

    signature, changed = process_and_maybe_update(
        model=model,
        layout=layout,
        frame=frame,
        source=cli.source,
        frame_index=0,
        timestamp_sec=0.0,
        detection_args=detection_args,
        output_json=cli.save_json,
        debug_frame_path=cli.save_frame,
        previous_signature=prev_signature,
        write_debug_every_frame=cli.write_debug_every_frame,
    )
    print("updated occupancy.json" if changed else "no changes")


def open_capture(source: str) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(source)
    return cap


def run_stream(cli: argparse.Namespace) -> None:
    layout = load_layout(cli.layout)
    model = load_model(cli.model)
    detection_args = make_detection_args(cli)

    old_state = load_json_if_exists(cli.save_json)
    prev_signature = extract_status_signature(old_state)

    frame_index = -1
    processed_count = 0
    last_processed_wall_time = 0.0

    while True:
        cap = open_capture(cli.source)
        if not cap.isOpened():
            print(f"Не удалось открыть источник: {cli.source}. Повтор через {cli.reconnect_sec:.1f} сек.", flush=True)
            time.sleep(cli.reconnect_sec)
            continue

        fps = cap.get(cv2.CAP_PROP_FPS)
        if not fps or fps <= 0 or math.isnan(fps):
            fps = 25.0

        print(f"source opened: {cli.source}; fps≈{fps:.2f}; interval={cli.interval_sec:.2f}s", flush=True)

        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    print("Поток/видео закончилось или кадр не прочитан.", flush=True)
                    break

                frame_index += 1
                now = time.monotonic()
                if now - last_processed_wall_time < cli.interval_sec:
                    continue
                last_processed_wall_time = now

                timestamp_sec = frame_index / fps
                prev_signature, changed = process_and_maybe_update(
                    model=model,
                    layout=layout,
                    frame=frame,
                    source=cli.source,
                    frame_index=frame_index,
                    timestamp_sec=timestamp_sec,
                    detection_args=detection_args,
                    output_json=cli.save_json,
                    debug_frame_path=cli.save_frame,
                    previous_signature=prev_signature,
                    write_debug_every_frame=cli.write_debug_every_frame,
                )

                processed_count += 1
                status = "UPDATED" if changed else "no changes"
                print(f"frame={frame_index} t={timestamp_sec:.2f}s {status}", flush=True)

                if cli.run_once:
                    return

                if cli.display and cli.save_frame:
                    debug_img = cv2.imread(cli.save_frame)
                    if debug_img is not None:
                        cv2.imshow("parking-stream", debug_img)
                        key = cv2.waitKey(1) & 0xFF
                        if key in (27, ord("q")):
                            return
        finally:
            cap.release()

        if infer_source_type(cli.source) != "image" and not cli.loop_video and not cli.is_live:
            break

        print(f"reconnect/restart in {cli.reconnect_sec:.1f}s", flush=True)
        time.sleep(cli.reconnect_sec)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Parking occupancy worker for video files and live camera streams")
    p.add_argument("--layout", default="data/layouts/parking_a_layout.json")
    p.add_argument("--source", required=True, help="image, video path, webcam index, RTSP/HTTP URL")
    p.add_argument("--model", default="models/best.pt")
    p.add_argument("--save-json", default="data/results/occupancy.json")
    p.add_argument("--save-frame", default="data/results/debug_detection.jpg")

    p.add_argument("--interval-sec", type=float, default=2.0, help="process one frame each N seconds")
    p.add_argument("--reconnect-sec", type=float, default=3.0, help="reconnect delay for live streams")
    p.add_argument("--is-live", action="store_true", help="treat source as live stream and reconnect forever")
    p.add_argument("--loop-video", action="store_true", help="restart video file when it ends")
    p.add_argument("--run-once", action="store_true", help="process one frame and exit")
    p.add_argument("--display", action="store_true")
    p.add_argument("--write-debug-every-frame", action="store_true", help="rewrite debug image even when occupancy did not change")

    # Arguments forwarded to detect_parking.process_frame()
    p.add_argument("--conf", type=float, default=0.20)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--crop-pad", type=int, default=120)
    p.add_argument("--spot-margin-px", type=float, default=0.0)
    p.add_argument("--spot-margin-m", type=float, default=0.35)
    p.add_argument("--overlap-threshold", type=float, default=0.06)
    p.add_argument("--nms-iou", type=float, default=0.50)
    p.add_argument("--no-zone-crops", action="store_true")
    p.add_argument("--no-enhance-crops", action="store_true")
    p.add_argument("--no-enhance-full-frame", action="store_true")
    return p


def main() -> None:
    cli = build_parser().parse_args()

    # Allow webcam index like --source 0
    if cli.source.isdigit():
        cli.source = int(cli.source)  # type: ignore[assignment]

    source_type = infer_source_type(str(cli.source))
    if source_type == "image":
        run_image_once(cli)
    else:
        run_stream(cli)


if __name__ == "__main__":
    main()
