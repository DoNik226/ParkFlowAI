# main.py
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import os
from dotenv import load_dotenv
from back.migrations.migrations import run_migrations

from back.app.api.routes import __routes__

load_dotenv()
app = FastAPI()

for route in __routes__:
    app.include_router(route)

origins = [
    "http://localhost.tiangolo.com",
    "https://localhost.tiangolo.com",
    "http://localhost",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def main():
    # Получаем URL базы данных
    DATABASE_URL = os.getenv('DATABASE_URL')

    if not DATABASE_URL:
        raise ValueError("DATABASE_URL не указан в переменных окружения")

    # Запускаем миграции при старте приложения
    print("Проверка и выполнение миграций базы данных...")
    run_migrations(DATABASE_URL, create_admin=True)

    # Далее запускаем основное приложение
    print("Запуск основного приложения...")
    # Ваш код приложения здесь


if __name__ == "__main__":
    main()
    uvicorn.run("back.app.main:app", host="0.0.0.0", log_level="info")
