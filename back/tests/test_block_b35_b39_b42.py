import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from back.app.logger import EventLogger
from back.app.models.enums import CameraStatus, EventEntityType, EventType
from back.app.services import detector_supervisor
from back.app.services.detector_supervisor import (
    MAX_RECONNECT_ATTEMPTS,
    ParkingDetectorRuntime,
    build_unknown_occupancy,
    normalize_layout_for_detector,
    record_reconnect_failure,
)
from back.app.services.parking_layout_storage_service import ParkingLayoutStorageService


class _FakeResult:
    _next_id = 1

    def first(self):
        row_id = _FakeResult._next_id
        _FakeResult._next_id += 1
        return (row_id,)


class _FakeDb:
    def __init__(self):
        self.statements = []
        self.params = []
        self.committed = False

    def execute(self, statement, params=None):
        self.statements.append(str(statement))
        self.params.append(params or {})
        return _FakeResult()

    def commit(self):
        self.committed = True


class _FakeSession:
    def close(self):
        pass


class BlockTestsB35B39B42(unittest.TestCase):
    def test_b35_save_layout_deletes_removed_parking_spot(self):
        db = _FakeDb()
        service = ParkingLayoutStorageService(db)
        parking = SimpleNamespace(id=10)

        service.save_layout_to_db(
            parking,
            {
                "parking": {"id": "p10"},
                "camera": {},
                "zones": [],
                "spots": [{"id": "spot_2", "label": "002", "polygon": []}],
                "edges": [],
                "entrances": [],
            },
        )

        self.assertTrue(
            any("DELETE FROM parking_spots WHERE parking_id = :parking_id" in sql for sql in db.statements)
        )
        inserted_spots = [
            params
            for sql, params in zip(db.statements, db.params)
            if "INSERT INTO parking_spots" in sql
        ]
        self.assertEqual(len(inserted_spots), 1)
        self.assertEqual(inserted_spots[0]["client_id"], "spot_2")
        self.assertTrue(db.committed)

    def test_b36_normalized_layout_json_contains_spots(self):
        layout = normalize_layout_for_detector(
            {
                "parking": {"id": "parking_1"},
                "camera": {},
                "zones": [{"id": "zone_1", "zone": 1}],
                "spots": [{"id": "spot_001", "zone_id": "zone_1", "corners": [{"x": 1, "y": 2}]}],
            }
        )

        self.assertEqual(layout["spots"][0]["id"], "spot_001")
        self.assertEqual(layout["spots"][0]["spot_id"], "spot_001")
        self.assertTrue(layout["spots"][0]["enabled"])
        self.assertEqual(layout["spots"][0]["polygon"], [{"x": 1, "y": 2}])
        self.assertEqual(layout["zones"][0]["spots"][0]["id"], "spot_001")

    def test_b37_reconnect_attempts_are_limited_to_three(self):
        control = {}
        exhausted = False

        for _ in range(5):
            control, exhausted = record_reconnect_failure(control)

        self.assertEqual(control["failed_attempts"], MAX_RECONNECT_ATTEMPTS)
        self.assertEqual(control["max_failed_attempts"], 3)
        self.assertTrue(exhausted)

    def test_b38_camera_goes_offline_after_three_failed_attempts(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            control_path = Path(tmp_dir) / "detector_control.json"
            save_json = Path(tmp_dir) / "occupancy.json"
            control_path.write_text(json.dumps({"failed_attempts": 2, "active": True}), encoding="utf-8")
            save_json.write_text(json.dumps({"spots": []}), encoding="utf-8")

            updated = {}

            class FakeCameraRepository:
                def __init__(self, db):
                    pass

                def get_by_id(self, camera_id):
                    return SimpleNamespace(id=camera_id, status=CameraStatus.ONLINE.value)

                def update(self, camera_id, **kwargs):
                    updated[camera_id] = kwargs

            runtime = ParkingDetectorRuntime(
                control_path=control_path,
                config={"camera_id": 15, "save_json": str(save_json), "source_type": "rtsp"},
                model=None,
            )

            with patch.object(detector_supervisor, "SessionLocal", return_value=_FakeSession()), \
                patch.object(detector_supervisor, "CameraRepository", FakeCameraRepository), \
                patch.object(detector_supervisor, "build_event_logger", return_value=Mock()):
                runtime.mark_error(RuntimeError("Cannot open source: rtsp://camera"))

            control = json.loads(control_path.read_text(encoding="utf-8"))
            self.assertFalse(control["active"])
            self.assertEqual(control["failed_attempts"], 3)
            self.assertEqual(updated[15]["status"], CameraStatus.OFFLINE.value)

    def test_b39_camera_loss_marks_spots_unknown(self):
        occupancy = build_unknown_occupancy(
            {
                "summary": {"total": 2, "free": 1, "occupied": 1, "unknown": 0},
                "spots": [
                    {"spot_id": "1", "status": "free", "confidence": 0.9, "vehicle": None},
                    {"spot_id": "2", "status": "occupied", "confidence": 0.8, "vehicle": {"id": "car"}},
                ],
            }
        )

        self.assertEqual(occupancy["summary"], {"total": 2, "free": 0, "occupied": 0, "unknown": 2})
        self.assertEqual([spot["status"] for spot in occupancy["spots"]], ["unknown", "unknown"])
        self.assertIsNone(occupancy["spots"][0]["confidence"])
        self.assertIsNone(occupancy["spots"][1]["vehicle"])

    def test_b42_camera_connected_event_log_entry_is_created(self):
        event_service = Mock()
        logger = EventLogger(event_service)

        logger.log_camera_connected(15, parking_id=10)

        event_service.create_event.assert_called_once_with(
            event_type=EventType.CAMERA_CONNECTED.value,
            description="Камера подключена",
            severity="info",
            entity_type=EventEntityType.CAMERA.value,
            entity_id=15,
            actor_user_id=None,
            parking_id=10,
            details=None,
        )


if __name__ == "__main__":
    unittest.main()
