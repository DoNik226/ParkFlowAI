import unittest
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from back.app.api.deps import get_db, require_admin
from back.app.database import Base
from back.app.main import app
from back.app.models.camera import Camera
from back.app.models.event_log import EventLog
from back.app.models.parking import Parking
from back.app.models.user import User


class EventLoggingTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        Base.metadata.create_all(bind=cls.engine)

        def override_get_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        def override_require_admin():
            session = cls.SessionLocal()
            try:
                return session.query(User).filter(User.id == 1).first()
            finally:
                session.close()

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[require_admin] = override_require_admin
        cls.client = TestClient(app)
        cls._seed_base_data()

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=cls.engine)

    @classmethod
    def _seed_base_data(cls):
        session = cls.SessionLocal()
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
            user = User(
                id=2,
                username="ivan",
                email="ivan@example.com",
                password_hash="hashed",
                role="user",
                full_name="Ivan Petrov",
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
            session.add_all([admin, user, parking, camera])
            session.flush()
            session.add_all(
                [
                    EventLog(
                        id=100,
                        timestamp=datetime(2026, 5, 3, 9, 0, tzinfo=timezone.utc),
                        event_type="user_login",
                        severity="info",
                        entity_type="user",
                        entity_id=2,
                        actor_user_id=2,
                        description="Пользователь вошел в систему",
                        details={},
                    ),
                    EventLog(
                        id=101,
                        timestamp=datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc),
                        event_type="camera_connected",
                        severity="info",
                        entity_type="camera",
                        entity_id=15,
                        parking_id=10,
                        description="Камера подключена",
                        details={"source": "integration-test"},
                    ),
                    EventLog(
                        id=102,
                        timestamp=datetime(2026, 5, 3, 11, 0, tzinfo=timezone.utc),
                        event_type="admin_action",
                        severity="info",
                        entity_type="admin",
                        entity_id=1,
                        actor_user_id=1,
                        description="Администратор обновил пользователя",
                        details={"target_user_id": 2},
                    ),
                ]
            )
            session.commit()
        finally:
            session.close()

    def test_logs_list(self):
        response = self.client.get("/logs")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 3)
        self.assertEqual(payload["logs"][0]["event_type"], "admin_action")

    def test_logs_filter_by_object_type(self):
        response = self.client.get("/logs", params={"object_type": "camera"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["logs"][0]["entity_name"], "Gate Camera")

    def test_logs_filter_by_description_and_parking(self):
        response = self.client.get(
            "/logs",
            params={"description": "Камера", "parking_id": 10},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["logs"][0]["parking_name"], "North Parking")

    def test_camera_logs_endpoint(self):
        response = self.client.get("/logs/cameras")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["entity_type"], "camera")

    def test_user_logs_endpoint(self):
        response = self.client.get("/logs/users")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 2)
        self.assertEqual(payload[0]["actor_username"], "admin")
