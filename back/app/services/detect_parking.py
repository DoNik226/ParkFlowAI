#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np

COCO_CAR_CLASS_ID = 0


@dataclass
class Detection:
    xyxy: Tuple[float, float, float, float]
    confidence: float
    class_id: int
    source: str

    @property
    def x1(self) -> float:
        return self.xyxy[0]

    @property
    def y1(self) -> float:
        return self.xyxy[1]

    @property
    def x2(self) -> float:
        return self.xyxy[2]

    @property
    def y2(self) -> float:
        return self.xyxy[3]

    @property
    def width(self) -> float:
        return max(0.0, self.x2 - self.x1)

    @property
    def height(self) -> float:
        return max(0.0, self.y2 - self.y1)

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center(self) -> Tuple[float, float]:
        return ((self.x1 + self.x2) * 0.5, (self.y1 + self.y2) * 0.5)

    @property
    def bottom_center(self) -> Tuple[float, float]:
        return ((self.x1 + self.x2) * 0.5, self.y2)

    def to_vehicle_payload(self) -> Dict[str, object]:
        return {
            "bbox": {
                "x1": round(float(self.x1), 2),
                "y1": round(float(self.y1), 2),
                "x2": round(float(self.x2), 2),
                "y2": round(float(self.y2), 2),
            },
            "confidence": round(float(self.confidence), 4),
            "class_id": int(self.class_id),
            "label": "car",
            "source": self.source,
        }


def polygon_to_np(points: Sequence[Dict[str, float]]) -> np.ndarray:
    return np.array([[float(p["x"]), float(p["y"])] for p in points], dtype=np.float32)


def polygon_bounds(poly: np.ndarray) -> Tuple[int, int, int, int]:
    x, y, w, h = cv2.boundingRect(poly.astype(np.float32))
    return int(x), int(y), int(w), int(h)


def expand_polygon(poly: np.ndarray, pixels: float) -> np.ndarray:
    if pixels <= 0:
        return poly.copy()
    center = poly.mean(axis=0)
    expanded = []
    for point in poly:
        vec = point - center
        norm = float(np.linalg.norm(vec))
        if norm < 1e-6:
            expanded.append(point.copy())
        else:
            expanded.append(point + vec / norm * pixels)
    return np.array(expanded, dtype=np.float32)


def bbox_iou(a: Detection, b: Detection) -> float:
    ix1 = max(a.x1, b.x1)
    iy1 = max(a.y1, b.y1)
    ix2 = min(a.x2, b.x2)
    iy2 = min(a.y2, b.y2)
    iw = max(0.0, ix2 - ix1)
    ih = max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    union = a.area + b.area - inter
    return inter / union if union > 0 else 0.0


def deduplicate_detections(detections: List[Detection], iou_threshold: float) -> List[Detection]:
    detections = sorted(detections, key=lambda d: d.confidence, reverse=True)
    kept: List[Detection] = []
    for det in detections:
        if all(bbox_iou(det, prev) < iou_threshold for prev in kept):
            kept.append(det)
    return kept


def maybe_apply_clahe(image: np.ndarray, enabled: bool) -> np.ndarray:
    if not enabled:
        return image
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l2 = clahe.apply(l)
    merged = cv2.merge((l2, a, b))
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)


def load_model(model_path: str):
    from ultralytics import YOLO
    return YOLO(model_path)


def run_yolo(model, image: np.ndarray, conf: float, imgsz: int, source_label: str) -> List[Detection]:
    results = model.predict(
        source=image,
        conf=conf,
        imgsz=imgsz,
        verbose=False,
        classes=[COCO_CAR_CLASS_ID],
        device="cpu",
        augment=True,
    )
    detections: List[Detection] = []
    for result in results:
        boxes = result.boxes
        if boxes is None:
            continue
        xyxy = boxes.xyxy.cpu().numpy()
        confs = boxes.conf.cpu().numpy()
        classes = boxes.cls.cpu().numpy().astype(int)
        for box, score, cls_id in zip(xyxy, confs, classes):
            detections.append(
                Detection(
                    xyxy=(float(box[0]), float(box[1]), float(box[2]), float(box[3])),
                    confidence=float(score),
                    class_id=int(cls_id),
                    source=source_label,
                )
            )
    return detections


def zone_crop_detections(model, frame: np.ndarray, zones: Sequence[Dict[str, object]], conf: float, imgsz: int,
                         crop_pad: int, enhance: bool) -> List[Detection]:
    h, w = frame.shape[:2]
    out: List[Detection] = []
    for zone in zones:
        corners = polygon_to_np(zone["corners"])
        x, y, bw, bh = polygon_bounds(corners)
        x1 = max(0, x - crop_pad)
        y1 = max(0, y - crop_pad)
        x2 = min(w, x + bw + crop_pad)
        y2 = min(h, y + bh + crop_pad)
        if x2 <= x1 or y2 <= y1:
            continue
        crop = frame[y1:y2, x1:x2]
        crop = maybe_apply_clahe(crop, enabled=enhance)
        dets = run_yolo(model, crop, conf=conf, imgsz=imgsz, source_label=f"zone:{zone.get('id', 'unknown')}")
        for det in dets:
            out.append(
                Detection(
                    xyxy=(det.x1 + x1, det.y1 + y1, det.x2 + x1, det.y2 + y1),
                    confidence=det.confidence,
                    class_id=det.class_id,
                    source=det.source,
                )
            )
    return out


def mask_overlap_ratio(frame_shape: Tuple[int, int], poly: np.ndarray, det: Detection) -> float:
    height, width = frame_shape[:2]
    x1 = max(0, int(math.floor(det.x1)))
    y1 = max(0, int(math.floor(det.y1)))
    x2 = min(width, int(math.ceil(det.x2)))
    y2 = min(height, int(math.ceil(det.y2)))
    if x2 <= x1 or y2 <= y1:
        return 0.0
    sub_w = x2 - x1
    sub_h = y2 - y1
    bbox_area = float(sub_w * sub_h)
    if bbox_area <= 0:
        return 0.0
    local_poly = poly.copy()
    local_poly[:, 0] -= x1
    local_poly[:, 1] -= y1
    mask = np.zeros((sub_h, sub_w), dtype=np.uint8)
    cv2.fillPoly(mask, [local_poly.astype(np.int32)], 255)
    overlap = float(np.count_nonzero(mask))
    return overlap / bbox_area


def spot_bbox(poly: np.ndarray) -> Tuple[float, float]:
    x, y, w, h = cv2.boundingRect(poly.astype(np.float32))
    return float(w), float(h)


def detection_matches_spot(
    frame_shape: Tuple[int, int],
    expanded_poly: np.ndarray,
    det: Detection,
    overlap_threshold: float,
) -> Tuple[bool, float]:
    bc = det.bottom_center
    c = det.center

    bottom_inside = cv2.pointPolygonTest(expanded_poly, bc, False) >= 0
    center_inside = cv2.pointPolygonTest(expanded_poly, c, False) >= 0
    overlap = mask_overlap_ratio(frame_shape, expanded_poly, det)

    ok = bottom_inside or center_inside or overlap >= overlap_threshold
    score = (
        overlap * 1.2
        + (0.35 if bottom_inside else 0.0)
        + (0.20 if center_inside else 0.0)
        + det.confidence * 0.25
    )
    return ok, score


def build_occupancy(layout: Dict[str, object], detections: Sequence[Detection], source_path: str, frame_index: int,
                    timestamp_sec: float, args: argparse.Namespace, frame_shape: Tuple[int, int]) -> Dict[str, object]:
    spots = layout["spots"]
    ppm = None
    calibration = layout.get("calibration")
    if isinstance(calibration, dict):
        ppm = calibration.get("pixels_per_meter")

    prepared = []
    for idx, spot in enumerate(spots):
        enabled = bool(spot.get("enabled", True))
        poly = polygon_to_np(spot["polygon"])
        margin_px = float(args.spot_margin_px)
        if margin_px <= 0 and ppm:
            margin_px = float(ppm) * float(args.spot_margin_m)
        expanded = expand_polygon(poly, margin_px)
        bw, bh = spot_bbox(poly)
        prepared.append((idx, spot, enabled, poly, expanded, bw, bh))

    candidates = []
    for det_idx, det in enumerate(detections):
        for spot_idx, spot, enabled, poly, expanded, bw, bh in prepared:
            if not enabled:
                continue
            # Отсев явного мусора/столбов: bbox не должен быть слишком мелким относительно места.
            w_ratio = det.width / max(1.0, bw)
            h_ratio = det.height / max(1.0, bh)
            area_ratio = det.area / max(1.0, bw * bh)

            # Отсекаем только откровенный мусор
            if max(w_ratio, h_ratio) < 0.12:
                continue
            if area_ratio < 0.015:
                continue

            ok, score = detection_matches_spot(
                frame_shape=frame_shape,
                expanded_poly=expanded,
                det=det,
                overlap_threshold=args.overlap_threshold,
            )
            if ok:
                candidates.append((score, det.confidence, det_idx, spot_idx))

    # Жадное one-to-one сопоставление: один bbox -> одно место.
    candidates.sort(reverse=True)
    used_dets = set()
    used_spots = set()
    assigned: Dict[int, Detection] = {}
    for _score, _conf, det_idx, spot_idx in candidates:
        if det_idx in used_dets or spot_idx in used_spots:
            continue
        used_dets.add(det_idx)
        used_spots.add(spot_idx)
        assigned[spot_idx] = detections[det_idx]

    spots_payload: List[Dict[str, object]] = []
    occupied = 0
    free = 0
    unknown = 0
    for spot_idx, spot, enabled, _poly, _expanded, _bw, _bh in prepared:
        det = assigned.get(spot_idx)
        if not enabled:
            status = "unknown"
            confidence = None
            vehicle = None
            unknown += 1
        elif det is None:
            status = "free"
            confidence = None
            vehicle = None
            free += 1
        else:
            status = "occupied"
            confidence = det.confidence
            vehicle = det.to_vehicle_payload()
            occupied += 1
        spots_payload.append({
            "spot_id": spot["id"],
            "status": status,
            "enabled": enabled,
            "confidence": None if confidence is None else round(float(confidence), 4),
            "row": spot.get("row"),
            "col": spot.get("col"),
            "zone": spot.get("zone"),
            "zone_id": spot.get("zone_id"),
            "vehicle": vehicle,
        })

    return {
        "parking_id": layout["parking"]["id"],
        "parking_name": layout["parking"].get("name"),
        "camera_id": layout["camera"]["id"],
        "frame_index": int(frame_index),
        "timestamp_sec": round(float(timestamp_sec), 3),
        "summary": {
            "total": len(spots_payload),
            "occupied": occupied,
            "free": free,
            "unknown": unknown,
        },
        "params": {
            "model": args.model,
            "conf": args.conf,
            "imgsz": args.imgsz,
            "crop_pad": args.crop_pad,
            "spot_margin_px": args.spot_margin_px,
            "spot_margin_m": args.spot_margin_m,
            "overlap": args.overlap_threshold,
            "zone_crops": not args.no_zone_crops,
            "spot_crops": False,
            "enhance_crops": not args.no_enhance_crops,
            "interval_sec": args.interval_sec,
            "source_path": source_path,
        },
        "spots": spots_payload,
        "source_type": infer_source_type(source_path),
        "source_path": source_path,
    }


def draw_debug(frame: np.ndarray, layout: Dict[str, object], occupancy: Dict[str, object], detections: Sequence[Detection]) -> np.ndarray:
    vis = frame.copy()
    for det in detections:
        x1, y1, x2, y2 = map(lambda v: int(round(v)), det.xyxy)
        cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 220, 255), 2)
        cv2.putText(vis, f"car {det.confidence:.2f}", (x1, max(18, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 220, 255), 2, cv2.LINE_AA)

    spot_map = {item["spot_id"]: item for item in occupancy["spots"]}
    for spot in layout["spots"]:
        poly = polygon_to_np(spot["polygon"]).astype(np.int32)
        state = spot_map.get(spot["id"], {})
        status = state.get("status", "unknown")
        color = (0, 0, 255) if status == "occupied" else (0, 180, 0) if status == "free" else (150, 150, 150)
        cv2.polylines(vis, [poly], isClosed=True, color=color, thickness=2)
        p = tuple(poly[0])
        cv2.putText(vis, f"{spot['id']}:{status[0].upper()}", (int(p[0]), int(p[1]) + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1, cv2.LINE_AA)

    s = occupancy["summary"]
    cv2.rectangle(vis, (10, 10), (500, 42), (20, 20, 20), -1)
    cv2.putText(vis, f"occupied={s['occupied']} free={s['free']} total={s['total']}", (18, 33), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
    return vis


def ensure_parent(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def load_layout(layout_path: str) -> Dict[str, object]:
    with open(layout_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    for key in ["parking", "camera", "zones", "spots"]:
        if key not in data:
            raise ValueError(f"В layout отсутствует ключ '{key}'")
    return data


def save_json(data: Dict[str, object], path: str) -> None:
    ensure_parent(path)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def save_image(image: np.ndarray, path: str) -> None:
    ensure_parent(path)
    if not cv2.imwrite(path, image):
        raise RuntimeError(f"Не удалось записать изображение: {path}")


def infer_source_type(source_path: str) -> str:
    suffix = Path(source_path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
        return "image"
    return "video"


def process_frame(model, frame: np.ndarray, layout: Dict[str, object], source_path: str, frame_index: int,
                  timestamp_sec: float, args: argparse.Namespace):
    full_frame = maybe_apply_clahe(frame, enabled=not args.no_enhance_full_frame)
    detections = run_yolo(model, full_frame, conf=args.conf, imgsz=args.imgsz, source_label="full_frame")
    if not args.no_zone_crops:
        detections.extend(zone_crop_detections(model, frame, layout["zones"], conf=args.conf * 0.8, imgsz=args.imgsz,
                                               crop_pad=args.crop_pad, enhance=not args.no_enhance_crops))
    detections = [d for d in detections if d.confidence >= args.conf]
    detections = deduplicate_detections(detections, iou_threshold=args.nms_iou)
    occupancy = build_occupancy(layout, detections, source_path, frame_index, timestamp_sec, args, frame.shape)
    debug = draw_debug(frame, layout, occupancy, detections)
    return occupancy, debug


def run_image(model, layout: Dict[str, object], args: argparse.Namespace) -> None:
    frame = cv2.imread(args.source)
    if frame is None:
        raise RuntimeError(f"Не удалось прочитать изображение: {args.source}")
    occupancy, debug = process_frame(model, frame, layout, args.source, 0, 0.0, args)
    save_json(occupancy, args.save_json)
    if args.save_frame:
        save_image(debug, args.save_frame)
    print(json.dumps(occupancy["summary"], ensure_ascii=False))


def run_video(model, layout: Dict[str, object], args: argparse.Namespace) -> None:
    cap = cv2.VideoCapture(args.source)
    if not cap.isOpened():
        raise RuntimeError(f"Не удалось открыть видео/поток: {args.source}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0 or math.isnan(fps):
        fps = 25.0
    frame_step = max(1, int(round(fps * args.interval_sec)))
    frame_index = -1
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame_index += 1
            if frame_index % frame_step != 0:
                continue
            timestamp_sec = frame_index / fps
            occupancy, debug = process_frame(model, frame, layout, args.source, frame_index, timestamp_sec, args)
            save_json(occupancy, args.save_json)
            if args.save_frame:
                save_image(debug, args.save_frame)
            print(f"frame={frame_index} occupied={occupancy['summary']['occupied']} free={occupancy['summary']['free']}", flush=True)
            if args.display:
                cv2.imshow("parking-detection", debug)
                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord('q')):
                    break
            if args.run_once:
                break
    finally:
        cap.release()
        if args.display:
            cv2.destroyAllWindows()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Детекция занятости парковочных мест")
    parser.add_argument("--layout", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--model", default="yolov8x.pt")
    parser.add_argument("--conf", type=float, default=0.06)
    parser.add_argument("--imgsz", type=int, default=1920)
    parser.add_argument("--crop-pad", type=int, default=120)
    parser.add_argument("--spot-margin-px", type=float, default=0.0)
    parser.add_argument("--spot-margin-m", type=float, default=0.30)
    parser.add_argument("--overlap-threshold", type=float, default=0.10)
    parser.add_argument("--nms-iou", type=float, default=0.50)
    parser.add_argument("--save-json", default="occupancy.json")
    parser.add_argument("--save-frame", default="debug_detection.jpg")
    parser.add_argument("--interval-sec", type=float, default=2.0)
    parser.add_argument("--run-once", action="store_true")
    parser.add_argument("--display", action="store_true")
    parser.add_argument("--no-zone-crops", action="store_true")
    parser.add_argument("--no-enhance-crops", action="store_true")
    parser.add_argument("--no-enhance-full-frame", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    layout = load_layout(args.layout)
    model = load_model(args.model)
    source_type = infer_source_type(args.source)
    if source_type == "image":
        run_image(model, layout, args)
    else:
        run_video(model, layout, args)


if __name__ == "__main__":
    main()
