import unittest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from fastapi.testclient import TestClient

from back.app.api.deps import get_db
from back.app.database import Base
from back.app.main import app
from back.app.models.camera import Camera
from back.app.models.event_log import EventLog
from back.app.models.parking import Parking
from back.app.models.user import User


class StubEndpointsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        Base.metadata.create_all(bind=cls.engine)

        def override_get_db():
            db = cls.TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)
        cls._seed_data()

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=cls.engine)

    @classmethod
    def _seed_data(cls):
        session = cls.TestingSessionLocal()
        try:
            admin = User(
                id=1,
                username="admin",
                email="admin@example.com",
                password_hash="hashed",
                role="admin",
                full_name="System Admin",
                is_active=True,
            )
            parking = Parking(id=10, name="North Parking", is_active=True)
            camera = Camera(
                id=15,
                name="Gate Camera",
                rtsp_url="rtsp://camera",
                parking_id=10,
                status="online",
            )
            session.add_all([admin, parking, camera])
            session.flush()
            session.add_all(
                [
                    EventLog(
                        id=100,
                        timestamp=datetime(2026, 4, 23, 9, 0, tzinfo=timezone.utc),
                        event_type="user_login",
                        severity="info",
                        entity_type="user",
                        entity_id=1,
                        actor_user_id=1,
                        description="Пользователь вошел в систему",
                        details={},
                    ),
                    EventLog(
                        id=101,
                        timestamp=datetime(2026, 4, 23, 10, 0, tzinfo=timezone.utc),
                        event_type="camera_connected",
                        severity="info",
                        entity_type="camera",
                        entity_id=15,
                        parking_id=10,
                        description="Камера подключена",
                        details={"source": "integration-test"},
                    ),
                ]
            )
            session.commit()
        finally:
            session.close()

    def assert_stub(self, response, expected_path: str, expected_method: str):
        self.assertEqual(response.status_code, 501)
        payload = response.json()
        self.assertTrue(payload["stub"])
        self.assertEqual(payload["path"], expected_path)
        self.assertEqual(payload["method"], expected_method)

    def test_auth_forgot_password_stub(self):
        response = self.client.post("/auth/forgot-password", json={"username": "demo-user"})
        self.assert_stub(response, "/auth/forgot-password", "POST")

    def test_parking_collection_stub(self):
        response = self.client.get("/parkings")
        self.assert_stub(response, "/parkings", "GET")

    def test_camera_collection_stub(self):
        response = self.client.get("/cameras")
        self.assert_stub(response, "/cameras", "GET")

    def test_editor_stub(self):
        response = self.client.get("/editor/parking/1/zones")
        self.assert_stub(response, "/editor/parking/1/zones", "GET")

    def test_logs_list(self):
        response = self.client.get("/logs")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 2)
        self.assertEqual(len(payload["logs"]), 2)
        self.assertEqual(payload["logs"][0]["entity_type"], "camera")

    def test_logs_filter_by_object_and_parking(self):
        response = self.client.get("/logs", params={"object_type": "camera", "parking_id": 10})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["logs"][0]["parking_name"], "North Parking")

    def test_camera_logs_endpoint(self):
        response = self.client.get("/logs/cameras")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["entity_name"], "Gate Camera")

    def test_openapi_contains_expected_stub_paths(self):
        paths = app.openapi()["paths"]
        expected_paths = {
            "/auth/forgot-password",
            "/parkings",
            "/parkings/{parking_id}",
            "/parkings/{parking_id}/occupancy",
            "/parkings/{parking_id}/spots",
            "/parkings/{parking_id}/free-spots",
            "/parkings/{parking_id}/entrances",
            "/parkings/{parking_id}/nearest",
            "/parking-spots/{spot_id}/status",
            "/cameras",
            "/cameras/{camera_id}",
            "/cameras/{camera_id}/reconnect",
            "/cameras/{camera_id}/stream",
            "/cameras/{camera_id}/snapshot",
            "/editor/parking/{parking_id}/zones",
            "/editor/spots/{spot_id}",
            "/editor/spots/{spot_id}/toggle",
            "/editor/parking/{parking_id}/calibrate",
            "/editor/parking/{parking_id}/export/json",
            "/editor/parking/{parking_id}/export/png",
            "/editor/parking/{parking_id}/save",
            "/logs",
            "/logs/cameras",
            "/logs/users",
            "/logs/parkings",
        }
        self.assertTrue(expected_paths.issubset(paths.keys()))


if __name__ == "__main__":
    unittest.main()
