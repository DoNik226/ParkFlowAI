# main.py
import os
from dotenv import load_dotenv
from back.migrations.migrations import run_migrations

load_dotenv()


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