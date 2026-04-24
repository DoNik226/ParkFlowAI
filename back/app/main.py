from contextlib import asynccontextmanager
import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv
from back.app.api.routes import __routes__
from back.app.database import SessionLocal
from back.app.logger import EventLogger, configure_logging
from back.app.repositories.camera_repository import CameraRepository
from back.app.repositories.event_log_repository import EventLogRepository
from back.app.repositories.parking_repository import ParkingRepository
from back.app.repositories.user_repository import UserRepository
from back.app.services.event_service import EventService
from back.migrations.migrations import run_migrations

load_dotenv()


def _build_event_logger() -> EventLogger:
    db = SessionLocal()
    try:
        event_service = EventService(
            event_log_repository=EventLogRepository(db),
            user_repository=UserRepository(db),
            camera_repository=CameraRepository(db),
            parking_repository=ParkingRepository(db),
        )
        logger = EventLogger(event_service)
        logger.log_system_started()
        return logger
    finally:
        db.close()


def _log_system_stopped() -> None:
    db = SessionLocal()
    try:
        event_service = EventService(
            event_log_repository=EventLogRepository(db),
            user_repository=UserRepository(db),
            camera_repository=CameraRepository(db),
            parking_repository=ParkingRepository(db),
        )
        EventLogger(event_service).log_system_stopped()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    app_logger = configure_logging()
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        run_migrations(database_url, create_admin=True)
        _build_event_logger()
    else:
        app_logger.warning("DATABASE_URL is not set; skipping migrations and startup event logging")

    try:
        yield
    finally:
        if database_url:
            _log_system_stopped()


app = FastAPI(lifespan=lifespan)

for route in __routes__:
    app.include_router(route)

origins = [
    "http://localhost.tiangolo.com",
    "https://localhost.tiangolo.com",
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def main():
    print("Запуск приложения...")


if __name__ == "__main__":
    main()
    uvicorn.run("back.app.main:app", host="0.0.0.0", log_level="info")
