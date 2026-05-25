from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import traceback

import cv2

from back.app.database import SessionLocal
from back.app.logger import EventLogger
from back.app.models.enums import CameraSourceType, CameraStatus
from back.app.repositories.camera_repository import CameraRepository
from back.app.repositories.event_log_repository import EventLogRepository
from back.app.repositories.parking_repository import ParkingRepository
from back.app.repositories.user_repository import UserRepository
from back.app.services.event_service import EventService
from back.app.services.detect_parking import (
    load_layout,
    load_model,
    process_frame,
    save_image,
)

DATA_ROOT = Path(os.getenv("DETECTOR_DATA_ROOT", "/app/data/companies"))
DEFAULT_SLEEP_SEC = 0.5
MAX_RECONNECT_ATTEMPTS = 3


def read_json(path: Path, default=None):
    if not path.exists():
        return default

    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return default


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp = path.with_suffix(path.suffix + ".tmp")

    with tmp.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    tmp.replace(path)


def iter_control_files():
    if not DATA_ROOT.exists():
        return []

    return list(DATA_ROOT.glob("*/parkings/*/detector_control.json"))


def extract_status_signature(occupancy):
    if not occupancy or "spots" not in occupancy:
        return None

    return {
        str(item.get("spot_id")): str(item.get("status"))
        for item in occupancy.get("spots", [])
        if item.get("spot_id") is not None
    }


def load_json_if_exists(path: str):
    if not path:
        return None

    return read_json(Path(path), default=None)


def build_event_logger(db):
    return EventLogger(
        EventService(
            event_log_repository=EventLogRepository(db),
            user_repository=UserRepository(db),
            camera_repository=CameraRepository(db),
            parking_repository=ParkingRepository(db),
        )
    )


def is_connection_error_message(message: str) -> bool:
    lowered = (message or "").lower()
    return "cannot open source" in lowered or "cannot read frame" in lowered


def record_reconnect_failure(control: dict, max_attempts: int = MAX_RECONNECT_ATTEMPTS) -> tuple[dict, bool]:
    updated = dict(control or {})
    attempts = min(int(updated.get("failed_attempts") or 0) + 1, max_attempts)
    updated["failed_attempts"] = attempts
    updated["max_failed_attempts"] = max_attempts
    return updated, attempts >= max_attempts


def build_unknown_occupancy(occupancy: dict | None) -> dict | None:
    if not isinstance(occupancy, dict) or not isinstance(occupancy.get("spots"), list):
        return None

    updated = dict(occupancy)
    spots = []
    for item in occupancy.get("spots", []):
        if not isinstance(item, dict):
            continue
        spot = dict(item)
        spot["status"] = "unknown"
        spot["confidence"] = None
        spot["vehicle"] = None
        spots.append(spot)

    updated["spots"] = spots
    updated["summary"] = {
        **(updated.get("summary") if isinstance(updated.get("summary"), dict) else {}),
        "total": len(spots),
        "occupied": 0,
        "free": 0,
        "unknown": len(spots),
    }
    return updated

def normalize_layout_for_detector(layout: dict) -> dict:
    """
    Приводит layout из Vue-редактора к формату, который ожидает detect_parking.py.

    Новый редактор хранит:
      layout["zones"] — список зон
      layout["spots"] — общий список мест

    Старый detector часто ожидает, что у каждой зоны будет:
      zone["spots"] — список мест внутри зоны
    """

    if not isinstance(layout, dict):
        return layout

    zones = layout.get("zones") or []
    spots = layout.get("spots") or []

    if not isinstance(zones, list):
        zones = []

    if not isinstance(spots, list):
        spots = []

    normalized_spots = []

    for index, spot in enumerate(spots, start=1):
        if not isinstance(spot, dict):
            continue

        normalized = dict(spot)

        # Главное: у места обязательно должен быть id.
        if not normalized.get("id"):
            normalized["id"] = (
                normalized.get("spot_id")
                or normalized.get("number")
                or normalized.get("label")
                or f"spot_{index:03d}"
            )

        # Для совместимости оставляем и spot_id.
        if not normalized.get("spot_id"):
            normalized["spot_id"] = normalized["id"]

        if not normalized.get("label"):
            normalized["label"] = str(index).zfill(3)

        if not normalized.get("number"):
            normalized["number"] = normalized["label"]

        # detector обычно работает с polygon.
        if "polygon" not in normalized and "corners" in normalized:
            normalized["polygon"] = normalized["corners"]

        normalized["enabled"] = normalized.get("enabled", True)

        normalized_spots.append(normalized)

    normalized_zones = []

    for zone_index, zone in enumerate(zones, start=1):
        if not isinstance(zone, dict):
            continue

        normalized_zone = dict(zone)

        if not normalized_zone.get("id"):
            normalized_zone["id"] = f"zone_{zone_index}"

        if not normalized_zone.get("name"):
            normalized_zone["name"] = f"Зона {zone_index}"

        zone_id = normalized_zone["id"]
        zone_number = normalized_zone.get("zone", zone_index)

        zone_spots = [
            spot
            for spot in normalized_spots
            if spot.get("zone_id") == zone_id or spot.get("zone") == zone_number
        ]

        # Важное поле для старого detect_parking.py
        normalized_zone["spots"] = zone_spots

        # На всякий случай detector может ждать polygon/corners у зоны.
        if "polygon" not in normalized_zone and "corners" in normalized_zone:
            normalized_zone["polygon"] = normalized_zone["corners"]

        normalized_zones.append(normalized_zone)

    layout["zones"] = normalized_zones
    layout["spots"] = normalized_spots

    camera = layout.get("camera")

    if not isinstance(camera, dict):
        camera = {}

    if "id" not in camera:
        camera["id"] = (
            camera.get("camera_id")
            or layout.get("camera_id")
            or layout.get("parking", {}).get("camera_id")
            or "default_camera"
        )

    layout["camera"] = camera

    return layout


def make_detection_args(config: dict) -> SimpleNamespace:
    return SimpleNamespace(
        model=config.get("model", "/app/models/best.pt"),
        conf=float(config.get("conf", 0.25)),
        imgsz=int(config.get("imgsz", 640)),
        crop_pad=int(config.get("crop_pad", 120)),
        spot_margin_px=float(config.get("spot_margin_px", 0.0)),
        spot_margin_m=float(config.get("spot_margin_m", 0.0)),
        overlap_threshold=float(config.get("overlap_threshold", 0.18)),
        nms_iou=float(config.get("nms_iou", 0.50)),
        interval_sec=float(config.get("interval_sec", 2.0)),
        no_zone_crops=bool(config.get("no_zone_crops", False)),
        no_enhance_crops=bool(config.get("no_enhance_crops", False)),
        no_enhance_full_frame=bool(config.get("no_enhance_full_frame", False)),
        save_frame=config.get("save_frame"),
    )


class ParkingDetectorRuntime:
    def __init__(self, control_path: Path, config: dict, model):
        self.control_path = control_path
        self.config = config
        self.model = model

        self.capture = None
        self.layout = None
        self.previous_signature = extract_status_signature(
            load_json_if_exists(config.get("save_json"))
        )

        self.last_processed_time = 0.0
        self.frame_index = -1
        self.fps = 25.0
        self.last_error_message = None

    def close(self):
        if self.capture is not None:
            self.capture.release()
            self.capture = None

    def open_capture_if_needed(self):
        if self.capture is not None and self.capture.isOpened():
            return

        source = self.config["source"]
        self.capture = cv2.VideoCapture(source)

        if not self.capture.isOpened():
            raise RuntimeError(f"Cannot open source: {source}")

        fps = self.capture.get(cv2.CAP_PROP_FPS)
        if fps and fps > 0:
            self.fps = fps

    def load_layout_if_needed(self):
        if self.layout is None:
            raw_layout = load_layout(self.config["layout_path"])
            self.layout = normalize_layout_for_detector(raw_layout)

    def process_once_if_due(self):
        now = time.monotonic()
        interval = float(self.config.get("interval_sec", 2.0))

        if now - self.last_processed_time < interval:
            return

        self.last_processed_time = now

        self.open_capture_if_needed()
        self.load_layout_if_needed()

        is_video = bool(self.config.get("loop_video"))

        if is_video:
            fps = self.capture.get(cv2.CAP_PROP_FPS)
            frame_count = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

            if fps and fps > 0:
                self.fps = fps

            # Для тестового видео перескакиваем вперёд по времени,
            # а не читаем один следующий кадр раз в interval_sec.
            if self.frame_index >= 0:
                step_frames = max(1, int(self.fps * interval))
                next_frame = self.frame_index + step_frames

                if frame_count > 0 and next_frame >= frame_count:
                    next_frame = 0

                self.capture.set(cv2.CAP_PROP_POS_FRAMES, next_frame)

        ok, frame = self.capture.read()

        if not ok or frame is None:
            if self.config.get("loop_video"):
                self.capture.release()
                self.capture = None
                self.frame_index = -1
                self.open_capture_if_needed()
                ok, frame = self.capture.read()

            if not ok or frame is None:
                raise RuntimeError("Cannot read frame from source")

        current_frame = int(self.capture.get(cv2.CAP_PROP_POS_FRAMES) or 0)
        self.frame_index = max(0, current_frame - 1)

        timestamp_msec = self.capture.get(cv2.CAP_PROP_POS_MSEC)
        if timestamp_msec and timestamp_msec > 0:
            timestamp_sec = timestamp_msec / 1000
        else:
            timestamp_sec = self.frame_index / self.fps

        detection_args = make_detection_args(self.config)

        occupancy, debug = process_frame(
            model=self.model,
            frame=frame,
            layout=self.layout,
            source_path=self.config["source"],
            frame_index=self.frame_index,
            timestamp_sec=timestamp_sec,
            args=detection_args,
        )

        new_signature = extract_status_signature(occupancy)
        changed = new_signature != self.previous_signature

        # Пишем occupancy всегда, даже если статус не изменился.
        # Так проще видеть, что detector живой, и обновлять timestamp/debug.
        write_json(Path(self.config["save_json"]), occupancy)
        self.previous_signature = new_signature

        save_frame = self.config.get("save_frame")
        if save_frame:
            save_image(debug, save_frame)

        self.mark_ok(changed)

    def mark_ok(self, changed: bool):
        control = read_json(self.control_path, default={}) or {}
        control["last_error"] = None
        control["failed_attempts"] = 0
        control["last_processed_at"] = datetime.now(timezone.utc).isoformat()
        control["last_changed"] = changed
        write_json(self.control_path, control)
        self.last_error_message = None
        self._mark_camera_online()

    def mark_error(self, error: Exception):
        message = str(error)
        control = read_json(self.control_path, default={}) or {}
        control, attempts_exhausted = record_reconnect_failure(control)
        control["last_error"] = message
        control["last_processed_at"] = datetime.now(timezone.utc).isoformat()
        if attempts_exhausted:
            control["active"] = False
        write_json(self.control_path, control)
        if message != self.last_error_message:
            self._persist_error_event(message)
            self.last_error_message = message
        if attempts_exhausted:
            self._mark_camera_offline()
            self._mark_spots_unknown()

    def _mark_camera_online(self):
        camera_id = self.config.get("camera_id")
        parking_id = self.config.get("parking_db_id")
        source_type = self.config.get("source_type")

        if camera_id is None:
            return

        db = SessionLocal()
        try:
            camera_repo = CameraRepository(db)
            camera = camera_repo.get_by_id(int(camera_id))
            if not camera:
                return

            previous_status = camera.status
            if previous_status != CameraStatus.ONLINE.value:
                camera_repo.update(camera.id, status=CameraStatus.ONLINE.value)
                if source_type == CameraSourceType.RTSP.value:
                    build_event_logger(db).log_camera_connected(
                        camera.id,
                        parking_id=int(parking_id) if parking_id is not None else None,
                        restored=previous_status == CameraStatus.ERROR.value,
                    )
        finally:
            db.close()

    def _persist_error_event(self, message: str):
        camera_id = self.config.get("camera_id")
        parking_id = self.config.get("parking_db_id")
        source_type = self.config.get("source_type")

        db = SessionLocal()
        try:
            logger = build_event_logger(db)
            camera = None
            previous_status = None
            if camera_id is not None:
                camera = CameraRepository(db).get_by_id(int(camera_id))
                previous_status = camera.status if camera else None

            is_connection_error = is_connection_error_message(message)
            if camera and camera.status != CameraStatus.ERROR.value:
                CameraRepository(db).update(camera.id, status=CameraStatus.ERROR.value)

            details = {
                "message": message,
                "parking_id": parking_id,
                "camera_id": camera_id,
                "source_type": source_type,
                "source": self.config.get("source"),
            }

            if is_connection_error and camera_id is not None and source_type == CameraSourceType.RTSP.value:
                if previous_status == CameraStatus.ONLINE.value:
                    logger.log_camera_connection_lost(
                        int(camera_id),
                        parking_id=int(parking_id) if parking_id is not None else None,
                        details=details,
                    )
                else:
                    logger.log_video_processing_error(
                        camera_id=int(camera_id),
                        parking_id=int(parking_id) if parking_id is not None else None,
                        description="Ошибка доступа к видеопотоку камеры",
                        details=details,
                    )
                return

            logger.log_detection_error(
                camera_id=int(camera_id) if camera_id is not None else None,
                parking_id=int(parking_id) if parking_id is not None else None,
                description="Ошибка детекции парковки",
                details=details,
            )
        finally:
            db.close()

    def _mark_camera_offline(self):
        camera_id = self.config.get("camera_id")
        if camera_id is None:
            return

        db = SessionLocal()
        try:
            CameraRepository(db).update(int(camera_id), status=CameraStatus.OFFLINE.value)
        finally:
            db.close()

    def _mark_spots_unknown(self):
        save_json = self.config.get("save_json")
        if not save_json:
            return

        path = Path(save_json)
        occupancy = read_json(path, default=None)
        unknown_occupancy = build_unknown_occupancy(occupancy)
        if unknown_occupancy is None:
            return

        write_json(path, unknown_occupancy)


def main():
    print("Detector supervisor started", flush=True)

    model_cache = {}
    runtimes: dict[str, ParkingDetectorRuntime] = {}

    while True:
        active_keys = set()

        for control_path in iter_control_files():
            config = read_json(control_path, default={}) or {}
            key = str(control_path)

            if not config.get("active"):
                runtime = runtimes.pop(key, None)
                if runtime:
                    runtime.close()
                continue

            active_keys.add(key)

            model_path = config.get("model", "/app/models/best.pt")

            if model_path not in model_cache:
                print(f"Loading model: {model_path}", flush=True)
                model_cache[model_path] = load_model(model_path)

            runtime = runtimes.get(key)

            if runtime is None:
                print(f"Starting detector for {config.get('parking_id')}", flush=True)
                runtime = ParkingDetectorRuntime(
                    control_path=control_path,
                    config=config,
                    model=model_cache[model_path],
                )
                runtimes[key] = runtime

            try:
                runtime.process_once_if_due()
            except Exception as exc:
                print(f"Detector error for {config.get('parking_id')}: {exc}", flush=True)
                traceback.print_exc()
                runtime.mark_error(exc)
                runtime.close()
                time.sleep(1.0)

        for key in list(runtimes.keys()):
            if key not in active_keys:
                runtimes[key].close()
                del runtimes[key]

        time.sleep(DEFAULT_SLEEP_SEC)


if __name__ == "__main__":
    main()
