import os

import bcrypt
import psycopg2


class DatabaseMigration:
    """Класс для управления миграциями базы данных"""

    def __init__(self, db_url: str):
        """
        Инициализация миграции

        Args:
            db_url: URL подключения к PostgreSQL
        """
        self.db_url = db_url
        self.conn = None
        self.cursor = None
        self.migration_history = []

    def connect(self):
        """Установка соединения с базой данных"""
        try:
            self.conn = psycopg2.connect(self.db_url)
            self.cursor = self.conn.cursor()
            print("✓ Соединение с базой данных установлено")
        except Exception as e:
            print(f"✗ Ошибка подключения к БД: {e}")
            raise

    def disconnect(self):
        """Закрытие соединения"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("✓ Соединение с БД закрыто")

    def table_exists(self, table_name: str) -> bool:
        """
        Проверяет существование таблицы в базе данных

        Args:
            table_name: Имя таблицы

        Returns:
            True если таблица существует, False в противном случае
        """
        try:
            self.cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                )
            """, (table_name,))
            return self.cursor.fetchone()[0]
        except Exception as e:
            print(f"  Ошибка при проверке таблицы {table_name}: {e}")
            return False

    def enum_exists(self, enum_name: str) -> bool:
        """
        Проверяет существование ENUM типа

        Args:
            enum_name: Имя ENUM типа

        Returns:
            True если ENUM существует, False в противном случае
        """
        try:
            self.cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM pg_type 
                    WHERE typname = %s
                )
            """, (enum_name.lower(),))
            return self.cursor.fetchone()[0]
        except Exception as e:
            print(f"  Ошибка при проверке ENUM {enum_name}: {e}")
            return False

    def index_exists(self, index_name: str) -> bool:
        """
        Проверяет существование индекса

        Args:
            index_name: Имя индекса

        Returns:
            True если индекс существует, False в противном случае
        """
        try:
            self.cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM pg_indexes 
                    WHERE indexname = %s
                )
            """, (index_name,))
            return self.cursor.fetchone()[0]
        except Exception as e:
            print(f"  Ошибка при проверке индекса {index_name}: {e}")
            return False

    def column_exists(self, table_name: str, column_name: str) -> bool:
        try:
            self.cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns
                    WHERE table_schema = 'public'
                    AND table_name = %s
                    AND column_name = %s
                )
            """, (table_name, column_name))
            return self.cursor.fetchone()[0]
        except Exception as e:
            print(f"  Ошибка при проверке колонки {table_name}.{column_name}: {e}")
            return False

    def create_enums(self):
        """Создание ENUM типов с проверкой существования"""
        enums = [
            ('userrole', "CREATE TYPE UserRole AS ENUM ('user', 'admin')"),
            ('camerastatus', "CREATE TYPE CameraStatus AS ENUM ('online', 'offline')"),
            ('spotstatus', "CREATE TYPE SpotStatus AS ENUM ('free', 'occupied')")
        ]

        for enum_name, enum_sql in enums:
            if not self.enum_exists(enum_name):
                try:
                    self.cursor.execute(enum_sql)
                    print(f"✓ ENUM тип '{enum_name}' создан")
                    self.migration_history.append(f"created_enum_{enum_name}")
                except Exception as e:
                    print(f"✗ Ошибка создания ENUM {enum_name}: {e}")
                    raise
            else:
                print(f"  ENUM тип '{enum_name}' уже существует, пропускаем создание")

    def create_users_table(self):
        """Создание таблицы users с проверкой существования"""
        table_name = "users"

        if self.table_exists(table_name):
            print(f"  Таблица '{table_name}' уже существует, пропускаем создание")
            self.ensure_users_table_columns()
            return

        create_table_sql = """
        CREATE TABLE users (
            id BIGSERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role UserRole NOT NULL DEFAULT 'user',
            full_name VARCHAR(255),
            is_active BOOLEAN DEFAULT TRUE,
            failed_attempts INTEGER DEFAULT 0,
            locked_until TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE,

            CONSTRAINT username_min_length CHECK (LENGTH(username) >= 3)
        )
        """

        # Индексы для оптимизации
        indexes = [
            ("idx_users_username", "CREATE INDEX idx_users_username ON users(username)"),
            ("idx_users_email", "CREATE INDEX idx_users_email ON users(email)"),
            ("idx_users_is_active", "CREATE INDEX idx_users_is_active ON users(is_active)"),
            ("idx_users_locked_until", "CREATE INDEX idx_users_locked_until ON users(locked_until)")
        ]

        try:
            self.cursor.execute(create_table_sql)
            print(f"✓ Таблица '{table_name}' создана")
            self.migration_history.append(f"created_table_{table_name}")

            # Создаем индексы с проверкой существования
            for index_name, index_sql in indexes:
                if not self.index_exists(index_name):
                    self.cursor.execute(index_sql)
                    print(f"  ✓ Индекс '{index_name}' создан")
                else:
                    print(f"  Индекс '{index_name}' уже существует, пропускаем")

        except Exception as e:
            print(f"✗ Ошибка создания таблицы {table_name}: {e}")
            raise

    def ensure_users_table_columns(self):
        table_name = "users"
        alter_statements = [
            (
                "created_at",
                "ALTER TABLE users ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()"
            ),
            (
                "updated_at",
                "ALTER TABLE users ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE"
            ),
        ]

        for column_name, sql in alter_statements:
            if self.column_exists(table_name, column_name):
                print(f"  Колонка '{table_name}.{column_name}' уже существует, пропускаем")
                continue
            self.cursor.execute(sql)
            print(f"  ✓ Колонка '{table_name}.{column_name}' создана")

    def create_login_attempts_table(self):
        """Создание таблицы login_attempts для будущего rate limiting по IP."""
        table_name = "login_attempts"

        if self.table_exists(table_name):
            print(f"  Таблица '{table_name}' уже существует, пропускаем создание")
            return

        create_table_sql = """
        CREATE TABLE login_attempts (
            id BIGSERIAL PRIMARY KEY,
            ip_address VARCHAR(45) NOT NULL,
            login VARCHAR(255) NOT NULL,
            was_successful BOOLEAN NOT NULL DEFAULT FALSE,
            attempted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
        """

        indexes = [
            ("idx_login_attempts_ip_address", "CREATE INDEX idx_login_attempts_ip_address ON login_attempts(ip_address)"),
            ("idx_login_attempts_login", "CREATE INDEX idx_login_attempts_login ON login_attempts(login)"),
            ("idx_login_attempts_attempted_at", "CREATE INDEX idx_login_attempts_attempted_at ON login_attempts(attempted_at)")
        ]

        try:
            self.cursor.execute(create_table_sql)
            print(f"✓ Таблица '{table_name}' создана")
            self.migration_history.append(f"created_table_{table_name}")

            for index_name, index_sql in indexes:
                if not self.index_exists(index_name):
                    self.cursor.execute(index_sql)
                    print(f"  ✓ Индекс '{index_name}' создан")
                else:
                    print(f"  Индекс '{index_name}' уже существует, пропускаем")
        except Exception as e:
            print(f"✗ Ошибка создания таблицы {table_name}: {e}")
            raise

    def create_default_admin(self):
        username = os.getenv("INITIAL_ADMIN_USERNAME")
        email = os.getenv("INITIAL_ADMIN_EMAIL")
        password = os.getenv("INITIAL_ADMIN_PASSWORD")
        full_name = os.getenv("INITIAL_ADMIN_FULL_NAME")

        if not username or not email or not password:
            print("  Начальный администратор не настроен через env, пропускаем создание")
            return

        self.cursor.execute(
            "SELECT id FROM users WHERE role = 'admin' OR username = %s OR email = %s LIMIT 1",
            (username, email),
        )
        if self.cursor.fetchone():
            print("  Начальный администратор уже существует, пропускаем создание")
            return

        password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(),
        ).decode("utf-8")
        self.cursor.execute(
            """
            INSERT INTO users (username, email, password_hash, role, full_name, is_active, failed_attempts, locked_until)
            VALUES (%s, %s, %s, 'admin', %s, TRUE, 0, NULL)
            """,
            (username, email, password_hash, full_name),
        )
        print("✓ Начальный администратор создан")

    def create_parkings_table(self):
        """Создание таблицы parkings с проверкой существования"""
        table_name = "parkings"

        if self.table_exists(table_name):
            print(f"  Таблица '{table_name}' уже существует, пропускаем создание")
            return

        create_table_sql = """
        CREATE TABLE parkings (
            id BIGSERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            config_file_path VARCHAR(255),
            is_active BOOLEAN DEFAULT TRUE
        )
        """

        indexes = [
            ("idx_parkings_name", "CREATE INDEX idx_parkings_name ON parkings(name)"),
            ("idx_parkings_is_active", "CREATE INDEX idx_parkings_is_active ON parkings(is_active)")
        ]

        try:
            self.cursor.execute(create_table_sql)
            print(f"✓ Таблица '{table_name}' создана")
            self.migration_history.append(f"created_table_{table_name}")

            for index_name, index_sql in indexes:
                if not self.index_exists(index_name):
                    self.cursor.execute(index_sql)
                    print(f"  ✓ Индекс '{index_name}' создан")
                else:
                    print(f"  Индекс '{index_name}' уже существует, пропускаем")

        except Exception as e:
            print(f"✗ Ошибка создания таблицы {table_name}: {e}")
            raise

    def create_road_vertices_table(self):
        """Создание таблицы road_vertices с проверкой существования"""
        table_name = "road_vertices"

        if self.table_exists(table_name):
            print(f"  Таблица '{table_name}' уже существует, пропускаем создание")
            return

        create_table_sql = """
        CREATE TABLE road_vertices (
            id BIGSERIAL PRIMARY KEY,
            is_spot BOOLEAN DEFAULT FALSE,
            is_entrance BOOLEAN DEFAULT FALSE,
            parking_id BIGINT REFERENCES parkings(id) ON DELETE CASCADE
        )
        """

        indexes = [
            ("idx_road_vertices_parking_id", "CREATE INDEX idx_road_vertices_parking_id ON road_vertices(parking_id)"),
            ("idx_road_vertices_is_spot", "CREATE INDEX idx_road_vertices_is_spot ON road_vertices(is_spot)"),
            ("idx_road_vertices_is_entrance",
             "CREATE INDEX idx_road_vertices_is_entrance ON road_vertices(is_entrance)")
        ]

        try:
            self.cursor.execute(create_table_sql)
            print(f"✓ Таблица '{table_name}' создана")
            self.migration_history.append(f"created_table_{table_name}")

            for index_name, index_sql in indexes:
                if not self.index_exists(index_name):
                    self.cursor.execute(index_sql)
                    print(f"  ✓ Индекс '{index_name}' создан")
                else:
                    print(f"  Индекс '{index_name}' уже существует, пропускаем")

        except Exception as e:
            print(f"✗ Ошибка создания таблицы {table_name}: {e}")
            raise

    def create_road_edges_table(self):
        """Создание таблицы road_edges с проверкой существования"""
        table_name = "road_edges"

        if self.table_exists(table_name):
            print(f"  Таблица '{table_name}' уже существует, пропускаем создание")
            return

        create_table_sql = """
        CREATE TABLE road_edges (
            id BIGSERIAL PRIMARY KEY,
            source BIGINT NOT NULL REFERENCES road_vertices(id) ON DELETE CASCADE,
            destination BIGINT NOT NULL REFERENCES road_vertices(id) ON DELETE CASCADE,
            length_meters FLOAT NOT NULL CHECK (length_meters > 0),
            one_way BOOLEAN DEFAULT FALSE,
            is_bidirectional BOOLEAN DEFAULT TRUE,

            CONSTRAINT source_destination_diff CHECK (source != destination)
        )
        """

        indexes = [
            ("idx_road_edges_source", "CREATE INDEX idx_road_edges_source ON road_edges(source)"),
            ("idx_road_edges_destination", "CREATE INDEX idx_road_edges_destination ON road_edges(destination)"),
            ("idx_road_edges_source_dest", "CREATE INDEX idx_road_edges_source_dest ON road_edges(source, destination)")
        ]

        try:
            self.cursor.execute(create_table_sql)
            print(f"✓ Таблица '{table_name}' создана")
            self.migration_history.append(f"created_table_{table_name}")

            for index_name, index_sql in indexes:
                if not self.index_exists(index_name):
                    self.cursor.execute(index_sql)
                    print(f"  ✓ Индекс '{index_name}' создан")
                else:
                    print(f"  Индекс '{index_name}' уже существует, пропускаем")

        except Exception as e:
            print(f"✗ Ошибка создания таблицы {table_name}: {e}")
            raise

    def create_cameras_table(self):
        """Создание таблицы cameras с проверкой существования"""
        table_name = "cameras"

        if self.table_exists(table_name):
            print(f"  Таблица '{table_name}' уже существует, пропускаем создание")
            return

        create_table_sql = """
        CREATE TABLE cameras (
            id BIGSERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            rtsp_url VARCHAR(500),
            parking_id BIGINT REFERENCES parkings(id) ON DELETE CASCADE,
            status CameraStatus DEFAULT 'offline'
        )
        """

        indexes = [
            ("idx_cameras_parking_id", "CREATE INDEX idx_cameras_parking_id ON cameras(parking_id)"),
            ("idx_cameras_status", "CREATE INDEX idx_cameras_status ON cameras(status)")
        ]

        try:
            self.cursor.execute(create_table_sql)
            print(f"✓ Таблица '{table_name}' создана")
            self.migration_history.append(f"created_table_{table_name}")

            for index_name, index_sql in indexes:
                if not self.index_exists(index_name):
                    self.cursor.execute(index_sql)
                    print(f"  ✓ Индекс '{index_name}' создан")
                else:
                    print(f"  Индекс '{index_name}' уже существует, пропускаем")

        except Exception as e:
            print(f"✗ Ошибка создания таблицы {table_name}: {e}")
            raise

    def create_parking_spots_table(self):
        """Создание таблицы parking_spots с проверкой существования"""
        table_name = "parking_spots"

        if self.table_exists(table_name):
            print(f"  Таблица '{table_name}' уже существует, пропускаем создание")
            return

        create_table_sql = """
        CREATE TABLE parking_spots (
            id BIGSERIAL PRIMARY KEY,
            parking_id BIGINT NOT NULL REFERENCES parkings(id) ON DELETE CASCADE,
            status SpotStatus NOT NULL DEFAULT 'free',
            spot_number VARCHAR(20) NOT NULL,
            road_vertex_id BIGINT REFERENCES road_vertices(id) ON DELETE SET NULL,

            CONSTRAINT unique_parking_spot_number UNIQUE(parking_id, spot_number)
        )
        """

        indexes = [
            ("idx_parking_spots_parking_id", "CREATE INDEX idx_parking_spots_parking_id ON parking_spots(parking_id)"),
            ("idx_parking_spots_status", "CREATE INDEX idx_parking_spots_status ON parking_spots(status)"),
            ("idx_parking_spots_road_vertex_id",
             "CREATE INDEX idx_parking_spots_road_vertex_id ON parking_spots(road_vertex_id)"),
            ("idx_parking_spots_parking_status",
             "CREATE INDEX idx_parking_spots_parking_status ON parking_spots(parking_id, status)")
        ]

        try:
            self.cursor.execute(create_table_sql)
            print(f"✓ Таблица '{table_name}' создана")
            self.migration_history.append(f"created_table_{table_name}")

            for index_name, index_sql in indexes:
                if not self.index_exists(index_name):
                    self.cursor.execute(index_sql)
                    print(f"  ✓ Индекс '{index_name}' создан")
                else:
                    print(f"  Индекс '{index_name}' уже существует, пропускаем")

        except Exception as e:
            print(f"✗ Ошибка создания таблицы {table_name}: {e}")
            raise

    def create_entrances_table(self):
        """Создание таблицы entrances с проверкой существования"""
        table_name = "entrances"

        if self.table_exists(table_name):
            print(f"  Таблица '{table_name}' уже существует, пропускаем создание")
            return

        create_table_sql = """
        CREATE TABLE entrances (
            id BIGSERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            parking_id BIGINT REFERENCES parkings(id) ON DELETE CASCADE,
            road_vertex_id BIGINT NOT NULL REFERENCES road_vertices(id) ON DELETE CASCADE
        )
        """

        indexes = [
            ("idx_entrances_parking_id", "CREATE INDEX idx_entrances_parking_id ON entrances(parking_id)"),
            ("idx_entrances_road_vertex_id", "CREATE INDEX idx_entrances_road_vertex_id ON entrances(road_vertex_id)")
        ]

        try:
            self.cursor.execute(create_table_sql)
            print(f"✓ Таблица '{table_name}' создана")
            self.migration_history.append(f"created_table_{table_name}")

            for index_name, index_sql in indexes:
                if not self.index_exists(index_name):
                    self.cursor.execute(index_sql)
                    print(f"  ✓ Индекс '{index_name}' создан")
                else:
                    print(f"  Индекс '{index_name}' уже существует, пропускаем")

        except Exception as e:
            print(f"✗ Ошибка создания таблицы {table_name}: {e}")
            raise

    def create_parking_occupancy_cache_table(self):
        """Создание таблицы parking_occupancy_cache с проверкой существования"""
        table_name = "parking_occupancy_cache"

        if self.table_exists(table_name):
            print(f"  Таблица '{table_name}' уже существует, пропускаем создание")
            return

        create_table_sql = """
        CREATE TABLE parking_occupancy_cache (
            id BIGSERIAL PRIMARY KEY,
            parking_id BIGINT NOT NULL UNIQUE REFERENCES parkings(id) ON DELETE CASCADE,
            total_spots INTEGER NOT NULL DEFAULT 0 CHECK (total_spots >= 0),
            free_spots INTEGER NOT NULL DEFAULT 0 CHECK (free_spots >= 0),
            occupancy_percentage DECIMAL(5,2) DEFAULT 0.00 CHECK (occupancy_percentage >= 0 AND occupancy_percentage <= 100),
            last_calculated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

            CONSTRAINT free_spots_not_exceed_total CHECK (free_spots <= total_spots)
        )
        """

        indexes = [
            ("idx_parking_occupancy_parking_id",
             "CREATE INDEX idx_parking_occupancy_parking_id ON parking_occupancy_cache(parking_id)"),
            ("idx_parking_occupancy_last_calculated",
             "CREATE INDEX idx_parking_occupancy_last_calculated ON parking_occupancy_cache(last_calculated)")
        ]

        try:
            self.cursor.execute(create_table_sql)
            print(f"✓ Таблица '{table_name}' создана")
            self.migration_history.append(f"created_table_{table_name}")

            for index_name, index_sql in indexes:
                if not self.index_exists(index_name):
                    self.cursor.execute(index_sql)
                    print(f"  ✓ Индекс '{index_name}' создан")
                else:
                    print(f"  Индекс '{index_name}' уже существует, пропускаем")

            # Проверяем существование функции и триггера
            self.cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM pg_proc 
                    WHERE proname = 'update_last_calculated'
                )
            """)
            function_exists = self.cursor.fetchone()[0]

            if not function_exists:
                trigger_sql = """
                CREATE OR REPLACE FUNCTION update_last_calculated()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.last_calculated = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;

                DROP TRIGGER IF EXISTS trigger_update_last_calculated ON parking_occupancy_cache;

                CREATE TRIGGER trigger_update_last_calculated
                    BEFORE UPDATE ON parking_occupancy_cache
                    FOR EACH ROW
                    EXECUTE FUNCTION update_last_calculated();
                """
                self.cursor.execute(trigger_sql)
                print("  ✓ Триггер для 'parking_occupancy_cache' создан")
            else:
                print("  Триггер для 'parking_occupancy_cache' уже существует, пропускаем")

        except Exception as e:
            print(f"✗ Ошибка создания таблицы {table_name}: {e}")
            raise

    def create_event_logs_table(self):
        """Создание таблицы event_logs с проверкой существования"""
        table_name = "event_logs"

        if self.table_exists(table_name):
            print(f"  Таблица '{table_name}' уже существует, пропускаем создание")
            return

        create_table_sql = """
        CREATE TABLE event_logs (
            id BIGSERIAL PRIMARY KEY,
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            event_type VARCHAR(64) NOT NULL,
            severity VARCHAR(20) NOT NULL DEFAULT 'info',
            entity_type VARCHAR(20) NOT NULL DEFAULT 'system',
            entity_id BIGINT,
            actor_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
            parking_id BIGINT REFERENCES parkings(id) ON DELETE SET NULL,
            description TEXT NOT NULL,
            details JSONB NOT NULL DEFAULT '{}'::jsonb
        )
        """

        indexes = [
            ("idx_event_logs_timestamp", "CREATE INDEX idx_event_logs_timestamp ON event_logs(timestamp DESC)"),
            ("idx_event_logs_event_type", "CREATE INDEX idx_event_logs_event_type ON event_logs(event_type)"),
            ("idx_event_logs_entity_type", "CREATE INDEX idx_event_logs_entity_type ON event_logs(entity_type)"),
            ("idx_event_logs_entity_id", "CREATE INDEX idx_event_logs_entity_id ON event_logs(entity_id)"),
            ("idx_event_logs_actor_user_id", "CREATE INDEX idx_event_logs_actor_user_id ON event_logs(actor_user_id)"),
            ("idx_event_logs_parking_id", "CREATE INDEX idx_event_logs_parking_id ON event_logs(parking_id)")
        ]

        try:
            self.cursor.execute(create_table_sql)
            print(f"✓ Таблица '{table_name}' создана")
            self.migration_history.append(f"created_table_{table_name}")

            for index_name, index_sql in indexes:
                if not self.index_exists(index_name):
                    self.cursor.execute(index_sql)
                    print(f"  ✓ Индекс '{index_name}' создан")
                else:
                    print(f"  Индекс '{index_name}' уже существует, пропускаем")
        except Exception as e:
            print(f"✗ Ошибка создания таблицы {table_name}: {e}")
            raise


    def get_migration_status(self) -> dict:
        """
        Получает статус миграции всех таблиц

        Returns:
            Словарь со статусом каждой таблицы
        """
        tables = [
            'users', 'login_attempts', 'parkings', 'road_vertices', 'road_edges',
            'cameras', 'parking_spots', 'entrances', 'parking_occupancy_cache',
            'event_logs'
        ]

        status = {}
        for table in tables:
            status[table] = self.table_exists(table)

        return status

    def run_all_migrations(self, create_admin: bool = False, force: bool = False):
        """
        Запуск всех миграций

        Args:
            create_admin: Создать ли администратора по умолчанию
            force: Принудительное создание таблиц даже если они существуют
        """
        try:
            self.connect()

            print("\n=== Начало миграции базы данных ===\n")

            # Показываем статус существующих таблиц
            if not force:
                status = self.get_migration_status()
                existing_tables = [name for name, exists in status.items() if exists]
                if existing_tables:
                    print(f"Найдены существующие таблицы: {', '.join(existing_tables)}")
                    print("Будут созданы только отсутствующие таблицы\n")

            # Создаем ENUM типы
            self.create_enums()

            # Создаем таблицы в правильном порядке (с учетом зависимостей)
            self.create_users_table()
            self.create_login_attempts_table()
            self.create_parkings_table()
            self.create_road_vertices_table()
            self.create_road_edges_table()
            self.create_cameras_table()
            self.create_parking_spots_table()
            self.create_entrances_table()
            self.create_parking_occupancy_cache_table()
            self.create_event_logs_table()

            if create_admin:
                self.create_default_admin()

            self.conn.commit()

            print("\n=== Миграция успешно завершена ===\n")

            # Показываем итоговый статус
            final_status = self.get_migration_status()
            print("Итоговый статус таблиц:")
            for table, exists in final_status.items():
                status_icon = "✓" if exists else "✗"
                print(f"  {status_icon} {table}")

        except Exception as e:
            print(f"\n✗ Ошибка при выполнении миграции: {e}")
            if self.conn:
                self.conn.rollback()
            raise
        finally:
            self.disconnect()


def run_migrations(db_url: str, create_admin: bool = False, force: bool = False):
    """
    Функция для запуска миграций

    Args:
        db_url: URL подключения к PostgreSQL
        create_admin: Создать ли администратора по умолчанию
        force: Принудительное создание таблиц даже если они существуют
    """
    migration = DatabaseMigration(db_url)
    migration.run_all_migrations(create_admin=create_admin, force=force)


if __name__ == "__main__":
    # Пример использования
    import os

    # Получаем URL базы данных из переменных окружения
    DATABASE_URL = os.getenv(
        'DATABASE_URL',
        'postgresql://user:password@localhost:5432/parking_db'
    )

    # Запускаем миграции
    # force=False - создаем только отсутствующие таблицы
    # force=True - принудительно создаем все таблицы (удаляем существующие)
    run_migrations(DATABASE_URL, create_admin=True, force=False)
import psycopg2


class DatabaseMigration:
    """Класс для управления миграциями базы данных"""

    def __init__(self, db_url: str):
        """
        Инициализация миграции

        Args:
            db_url: URL подключения к PostgreSQL
        """
        self.db_url = db_url
        self.conn = None
        self.cursor = None
        self.migration_history = []

    def connect(self):
        """Установка соединения с базой данных"""
        try:
            self.conn = psycopg2.connect(self.db_url)
            self.cursor = self.conn.cursor()
            print("✓ Соединение с базой данных установлено")
        except Exception as e:
            print(f"✗ Ошибка подключения к БД: {e}")
            raise

    def disconnect(self):
        """Закрытие соединения"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("✓ Соединение с БД закрыто")

    def table_exists(self, table_name: str) -> bool:
        """
        Проверяет существование таблицы в базе данных

        Args:
            table_name: Имя таблицы

        Returns:
            True если таблица существует, False в противном случае
        """
        try:
            self.cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                )
            """, (table_name,))
            return self.cursor.fetchone()[0]
        except Exception as e:
            print(f"  Ошибка при проверке таблицы {table_name}: {e}")
            return False

    def enum_exists(self, enum_name: str) -> bool:
        """
        Проверяет существование ENUM типа

        Args:
            enum_name: Имя ENUM типа

        Returns:
            True если ENUM существует, False в противном случае
        """
        try:
            self.cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM pg_type 
                    WHERE typname = %s
                )
            """, (enum_name.lower(),))
            return self.cursor.fetchone()[0]
        except Exception as e:
            print(f"  Ошибка при проверке ENUM {enum_name}: {e}")
            return False

    def index_exists(self, index_name: str) -> bool:
        """
        Проверяет существование индекса

        Args:
            index_name: Имя индекса

        Returns:
            True если индекс существует, False в противном случае
        """
        try:
            self.cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM pg_indexes 
                    WHERE indexname = %s
                )
            """, (index_name,))
            return self.cursor.fetchone()[0]
        except Exception as e:
            print(f"  Ошибка при проверке индекса {index_name}: {e}")
            return False

    def column_exists(self, table_name: str, column_name: str) -> bool:
        try:
            self.cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns
                    WHERE table_schema = 'public'
                    AND table_name = %s
                    AND column_name = %s
                )
            """, (table_name, column_name))
            return self.cursor.fetchone()[0]
        except Exception as e:
            print(f"  Ошибка при проверке колонки {table_name}.{column_name}: {e}")
            return False

    def create_enums(self):
        """Создание ENUM типов с проверкой существования"""
        enums = [
            ('userrole', "CREATE TYPE UserRole AS ENUM ('user', 'admin', 'super_admin')"),
            ('camerastatus', "CREATE TYPE CameraStatus AS ENUM ('online', 'offline', 'error')"),
            ('spotstatus', "CREATE TYPE SpotStatus AS ENUM ('free', 'occupied', 'unknown')")
        ]

        for enum_name, enum_sql in enums:
            if not self.enum_exists(enum_name):
                try:
                    self.cursor.execute(enum_sql)
                    print(f"✓ ENUM тип '{enum_name}' создан")
                    self.migration_history.append(f"created_enum_{enum_name}")
                except Exception as e:
                    print(f"✗ Ошибка создания ENUM {enum_name}: {e}")
                    raise
            else:
                print(f"  ENUM тип '{enum_name}' уже существует, пропускаем создание")
        self.ensure_enum_value("userrole", "super_admin")
        self.ensure_enum_value("camerastatus", "error")
        self.ensure_enum_value("spotstatus", "unknown")

    def ensure_enum_value(self, enum_name: str, value: str):
        try:
            self.cursor.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM pg_enum
                    JOIN pg_type ON pg_enum.enumtypid = pg_type.oid
                    WHERE pg_type.typname = %s
                    AND pg_enum.enumlabel = %s
                )
                """,
                (enum_name.lower(), value),
            )

            exists = self.cursor.fetchone()[0]

            if exists:
                print(f"  Значение '{value}' уже есть в ENUM '{enum_name}', пропускаем")
                return

            self.cursor.execute(f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS %s", (value,))
            print(f"  ✓ Значение '{value}' добавлено в ENUM '{enum_name}'")
        except Exception as e:
            print(f"  Ошибка при обновлении ENUM {enum_name}: {e}")
            raise

    def create_companies_table(self):
        table_name = "companies"

        if self.table_exists(table_name):
            print(f"  Таблица '{table_name}' уже существует, пропускаем создание")
            return

        create_table_sql = """
        CREATE TABLE companies (
            id BIGSERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            slug VARCHAR(100) UNIQUE NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        )
        """

        indexes = [
            ("idx_companies_slug", "CREATE INDEX idx_companies_slug ON companies(slug)"),
            ("idx_companies_is_active", "CREATE INDEX idx_companies_is_active ON companies(is_active)")
        ]

        try:
            self.cursor.execute(create_table_sql)
            print(f"✓ Таблица '{table_name}' создана")
            self.migration_history.append(f"created_table_{table_name}")

            for index_name, index_sql in indexes:
                if not self.index_exists(index_name):
                    self.cursor.execute(index_sql)
                    print(f"  ✓ Индекс '{index_name}' создан")
                else:
                    print(f"  Индекс '{index_name}' уже существует, пропускаем")
        except Exception as e:
            print(f"✗ Ошибка создания таблицы {table_name}: {e}")
            raise

    def ensure_default_company(self):
        self.cursor.execute("SELECT id FROM companies WHERE slug = 'default' LIMIT 1")
        row = self.cursor.fetchone()

        if row:
            print("  Компания default уже существует")
            return row[0]

        self.cursor.execute(
            """
            INSERT INTO companies (name, slug, is_active)
            VALUES ('Default Company', 'default', TRUE)
            RETURNING id
            """
        )

        company_id = self.cursor.fetchone()[0]
        print("✓ Компания default создана")
        return company_id

    def create_users_table(self):
        """Создание таблицы users с проверкой существования"""
        table_name = "users"

        if self.table_exists(table_name):
            print(f"  Таблица '{table_name}' уже существует, пропускаем создание")
            self.ensure_users_table_columns()
            return

        create_table_sql = """
        CREATE TABLE users (
            id BIGSERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role UserRole NOT NULL DEFAULT 'user',
            full_name VARCHAR(255),
            is_active BOOLEAN DEFAULT TRUE,
            failed_attempts INTEGER DEFAULT 0,
            locked_until TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE,

            CONSTRAINT username_min_length CHECK (LENGTH(username) >= 3)
        )
        """

        # Индексы для оптимизации
        indexes = [
            ("idx_users_username", "CREATE INDEX idx_users_username ON users(username)"),
            ("idx_users_email", "CREATE INDEX idx_users_email ON users(email)"),
            ("idx_users_is_active", "CREATE INDEX idx_users_is_active ON users(is_active)"),
            ("idx_users_locked_until", "CREATE INDEX idx_users_locked_until ON users(locked_until)")
        ]

        try:
            self.cursor.execute(create_table_sql)
            print(f"✓ Таблица '{table_name}' создана")
            self.migration_history.append(f"created_table_{table_name}")

            # Создаем индексы с проверкой существования
            for index_name, index_sql in indexes:
                if not self.index_exists(index_name):
                    self.cursor.execute(index_sql)
                    print(f"  ✓ Индекс '{index_name}' создан")
                else:
                    print(f"  Индекс '{index_name}' уже существует, пропускаем")

        except Exception as e:
            print(f"✗ Ошибка создания таблицы {table_name}: {e}")
            raise

    def ensure_users_table_columns(self):
        table_name = "users"

        default_company_id = None

        if self.table_exists("companies"):
            default_company_id = self.ensure_default_company()

        alter_statements = [
            (
                "company_id",
                "ALTER TABLE users ADD COLUMN company_id BIGINT REFERENCES companies(id) ON DELETE SET NULL"
            ),
            (
                "created_at",
                "ALTER TABLE users ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()"
            ),
            (
                "updated_at",
                "ALTER TABLE users ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE"
            ),
        ]

        for column_name, sql in alter_statements:
            if self.column_exists(table_name, column_name):
                print(f"  Колонка '{table_name}.{column_name}' уже существует, пропускаем")
                continue

            self.cursor.execute(sql)
            print(f"  ✓ Колонка '{table_name}.{column_name}' создана")

        if default_company_id is not None:
            self.cursor.execute(
                """
                UPDATE users
                SET company_id = %s
                WHERE company_id IS NULL
                """,
                (default_company_id,),
            )
            print("  ✓ Существующие пользователи привязаны к default company")

    def create_login_attempts_table(self):
        """Создание таблицы login_attempts для будущего rate limiting по IP."""
        table_name = "login_attempts"

        if self.table_exists(table_name):
            print(f"  Таблица '{table_name}' уже существует, пропускаем создание")
            return

        create_table_sql = """
        CREATE TABLE login_attempts (
            id BIGSERIAL PRIMARY KEY,
            ip_address VARCHAR(45) NOT NULL,
            login VARCHAR(255) NOT NULL,
            was_successful BOOLEAN NOT NULL DEFAULT FALSE,
            attempted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
        """

        indexes = [
            ("idx_login_attempts_ip_address",
             "CREATE INDEX idx_login_attempts_ip_address ON login_attempts(ip_address)"),
            ("idx_login_attempts_login", "CREATE INDEX idx_login_attempts_login ON login_attempts(login)"),
            ("idx_login_attempts_attempted_at",
             "CREATE INDEX idx_login_attempts_attempted_at ON login_attempts(attempted_at)")
        ]

        try:
            self.cursor.execute(create_table_sql)
            print(f"✓ Таблица '{table_name}' создана")
            self.migration_history.append(f"created_table_{table_name}")

            for index_name, index_sql in indexes:
                if not self.index_exists(index_name):
                    self.cursor.execute(index_sql)
                    print(f"  ✓ Индекс '{index_name}' создан")
                else:
                    print(f"  Индекс '{index_name}' уже существует, пропускаем")
        except Exception as e:
            print(f"✗ Ошибка создания таблицы {table_name}: {e}")
            raise

    def create_default_admin(self):
        username = os.getenv("INITIAL_ADMIN_USERNAME")
        email = os.getenv("INITIAL_ADMIN_EMAIL")
        password = os.getenv("INITIAL_ADMIN_PASSWORD")
        full_name = os.getenv("INITIAL_ADMIN_FULL_NAME")

        if not username or not email or not password:
            print("  Начальный администратор не настроен через env, пропускаем создание")
            return

        self.cursor.execute(
            "SELECT id FROM users WHERE role = 'admin' OR username = %s OR email = %s LIMIT 1",
            (username, email),
        )
        if self.cursor.fetchone():
            print("  Начальный администратор уже существует, пропускаем создание")
            return

        password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(),
        ).decode("utf-8")
        self.cursor.execute(
            """
            INSERT INTO users (username, email, password_hash, role, full_name, is_active, failed_attempts, locked_until)
            VALUES (%s, %s, %s, 'admin', %s, TRUE, 0, NULL)
            """,
            (username, email, password_hash, full_name),
        )
        print("✓ Начальный администратор создан")

    def create_parkings_table(self):
        table_name = "parkings"

        if self.table_exists(table_name):
            print(f"  Таблица '{table_name}' уже существует, проверяем колонки")
            self.ensure_parkings_table_columns()
            return

        default_company_id = self.ensure_default_company()

        create_table_sql = """
        CREATE TABLE parkings (
            id BIGSERIAL PRIMARY KEY,
            company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            slug VARCHAR(100) NOT NULL,
            description TEXT,
            layout_file_path VARCHAR(500),
            map_file_path VARCHAR(500),
            occupancy_file_path VARCHAR(500),
            screenshot_file_path VARCHAR(500),
            debug_frame_path VARCHAR(500),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE,
            CONSTRAINT unique_company_parking_slug UNIQUE(company_id, slug)
        )
        """

        indexes = [
            ("idx_parkings_company_id", "CREATE INDEX idx_parkings_company_id ON parkings(company_id)"),
            ("idx_parkings_slug", "CREATE INDEX idx_parkings_slug ON parkings(slug)"),
            ("idx_parkings_name", "CREATE INDEX idx_parkings_name ON parkings(name)"),
            ("idx_parkings_is_active", "CREATE INDEX idx_parkings_is_active ON parkings(is_active)")
        ]

        try:
            self.cursor.execute(create_table_sql)
            print(f"✓ Таблица '{table_name}' создана")
            self.migration_history.append(f"created_table_{table_name}")

            for index_name, index_sql in indexes:
                if not self.index_exists(index_name):
                    self.cursor.execute(index_sql)
                    print(f"  ✓ Индекс '{index_name}' создан")
                else:
                    print(f"  Индекс '{index_name}' уже существует, пропускаем")
        except Exception as e:
            print(f"✗ Ошибка создания таблицы {table_name}: {e}")
            raise

    def ensure_parkings_table_columns(self):
        table_name = "parkings"
        default_company_id = self.ensure_default_company()

        columns = [
            ("company_id",
             "ALTER TABLE parkings ADD COLUMN company_id BIGINT REFERENCES companies(id) ON DELETE CASCADE"),
            ("slug", "ALTER TABLE parkings ADD COLUMN slug VARCHAR(100)"),
            ("layout_file_path", "ALTER TABLE parkings ADD COLUMN layout_file_path VARCHAR(500)"),
            ("map_file_path", "ALTER TABLE parkings ADD COLUMN map_file_path VARCHAR(500)"),
            ("occupancy_file_path", "ALTER TABLE parkings ADD COLUMN occupancy_file_path VARCHAR(500)"),
            ("screenshot_file_path", "ALTER TABLE parkings ADD COLUMN screenshot_file_path VARCHAR(500)"),
            ("debug_frame_path", "ALTER TABLE parkings ADD COLUMN debug_frame_path VARCHAR(500)"),
            ("created_at", "ALTER TABLE parkings ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
            ("updated_at", "ALTER TABLE parkings ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE"),
        ]

        for column_name, sql in columns:
            if self.column_exists(table_name, column_name):
                print(f"  Колонка '{table_name}.{column_name}' уже существует, пропускаем")
                continue

            self.cursor.execute(sql)
            print(f"  ✓ Колонка '{table_name}.{column_name}' создана")

        self.cursor.execute(
            """
            UPDATE parkings
            SET company_id = %s
            WHERE company_id IS NULL
            """,
            (default_company_id,),
        )

        self.cursor.execute(
            """
            UPDATE parkings
            SET slug = LOWER(REGEXP_REPLACE(name, '[^a-zA-Z0-9]+', '_', 'g'))
            WHERE slug IS NULL OR slug = ''
            """
        )

        # self.cursor.execute(
        # """
        # UPDATE parkings
        # SET layout_file_path = config_file_path
        # WHERE layout_file_path IS NULL AND config_file_path IS NOT NULL
        # """
        # )

        if not self.index_exists("idx_parkings_company_id"):
            self.cursor.execute("CREATE INDEX idx_parkings_company_id ON parkings(company_id)")

        if not self.index_exists("idx_parkings_slug"):
            self.cursor.execute("CREATE INDEX idx_parkings_slug ON parkings(slug)")

    def create_road_vertices_table(self):
        """Создание таблицы road_vertices с проверкой существования"""
        table_name = "road_vertices"

        if self.table_exists(table_name):
            print(f"  Таблица '{table_name}' уже существует, пропускаем создание")
            return

        create_table_sql = """
        CREATE TABLE road_vertices (
            id BIGSERIAL PRIMARY KEY,
            is_spot BOOLEAN DEFAULT FALSE,
            is_entrance BOOLEAN DEFAULT FALSE,
            parking_id BIGINT REFERENCES parkings(id) ON DELETE CASCADE
        )
        """

        indexes = [
            ("idx_road_vertices_parking_id", "CREATE INDEX idx_road_vertices_parking_id ON road_vertices(parking_id)"),
            ("idx_road_vertices_is_spot", "CREATE INDEX idx_road_vertices_is_spot ON road_vertices(is_spot)"),
            ("idx_road_vertices_is_entrance",
             "CREATE INDEX idx_road_vertices_is_entrance ON road_vertices(is_entrance)")
        ]

        try:
            self.cursor.execute(create_table_sql)
            print(f"✓ Таблица '{table_name}' создана")
            self.migration_history.append(f"created_table_{table_name}")

            for index_name, index_sql in indexes:
                if not self.index_exists(index_name):
                    self.cursor.execute(index_sql)
                    print(f"  ✓ Индекс '{index_name}' создан")
                else:
                    print(f"  Индекс '{index_name}' уже существует, пропускаем")

        except Exception as e:
            print(f"✗ Ошибка создания таблицы {table_name}: {e}")
            raise

    def create_road_edges_table(self):
        """Создание таблицы road_edges с проверкой существования"""
        table_name = "road_edges"

        if self.table_exists(table_name):
            print(f"  Таблица '{table_name}' уже существует, пропускаем создание")
            return

        create_table_sql = """
        CREATE TABLE road_edges (
            id BIGSERIAL PRIMARY KEY,
            source BIGINT NOT NULL REFERENCES road_vertices(id) ON DELETE CASCADE,
            destination BIGINT NOT NULL REFERENCES road_vertices(id) ON DELETE CASCADE,
            length_meters FLOAT NOT NULL CHECK (length_meters > 0),
            one_way BOOLEAN DEFAULT FALSE,
            is_bidirectional BOOLEAN DEFAULT TRUE,

            CONSTRAINT source_destination_diff CHECK (source != destination)
        )
        """

        indexes = [
            ("idx_road_edges_source", "CREATE INDEX idx_road_edges_source ON road_edges(source)"),
            ("idx_road_edges_destination", "CREATE INDEX idx_road_edges_destination ON road_edges(destination)"),
            ("idx_road_edges_source_dest", "CREATE INDEX idx_road_edges_source_dest ON road_edges(source, destination)")
        ]

        try:
            self.cursor.execute(create_table_sql)
            print(f"✓ Таблица '{table_name}' создана")
            self.migration_history.append(f"created_table_{table_name}")

            for index_name, index_sql in indexes:
                if not self.index_exists(index_name):
                    self.cursor.execute(index_sql)
                    print(f"  ✓ Индекс '{index_name}' создан")
                else:
                    print(f"  Индекс '{index_name}' уже существует, пропускаем")

        except Exception as e:
            print(f"✗ Ошибка создания таблицы {table_name}: {e}")
            raise

    def create_cameras_table(self):
        table_name = "cameras"

        if self.table_exists(table_name):
            print(f"  Таблица '{table_name}' уже существует, проверяем колонки")
            self.ensure_cameras_table_columns()
            return

        create_table_sql = """
        CREATE TABLE cameras (
            id BIGSERIAL PRIMARY KEY,
            parking_id BIGINT NOT NULL REFERENCES parkings(id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            source_type VARCHAR(20) NOT NULL DEFAULT 'rtsp',
            source_url VARCHAR(1000),
            test_video_path VARCHAR(500),
            status CameraStatus DEFAULT 'offline',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            last_snapshot_path VARCHAR(500),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        )
        """

        indexes = [
            ("idx_cameras_parking_id", "CREATE INDEX idx_cameras_parking_id ON cameras(parking_id)"),
            ("idx_cameras_status", "CREATE INDEX idx_cameras_status ON cameras(status)"),
            ("idx_cameras_source_type", "CREATE INDEX idx_cameras_source_type ON cameras(source_type)")
        ]

        try:
            self.cursor.execute(create_table_sql)
            print(f"✓ Таблица '{table_name}' создана")
            self.migration_history.append(f"created_table_{table_name}")

            for index_name, index_sql in indexes:
                if not self.index_exists(index_name):
                    self.cursor.execute(index_sql)
                    print(f"  ✓ Индекс '{index_name}' создан")
                else:
                    print(f"  Индекс '{index_name}' уже существует, пропускаем")

        except Exception as e:
            print(f"✗ Ошибка создания таблицы {table_name}: {e}")
            raise

    def ensure_cameras_table_columns(self):
        table_name = "cameras"

        columns = [
            ("source_type", "ALTER TABLE cameras ADD COLUMN source_type VARCHAR(20) NOT NULL DEFAULT 'rtsp'"),
            ("source_url", "ALTER TABLE cameras ADD COLUMN source_url VARCHAR(1000)"),
            ("test_video_path", "ALTER TABLE cameras ADD COLUMN test_video_path VARCHAR(500)"),
            ("is_active", "ALTER TABLE cameras ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE"),
            ("last_snapshot_path", "ALTER TABLE cameras ADD COLUMN last_snapshot_path VARCHAR(500)"),
            ("created_at", "ALTER TABLE cameras ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
            ("updated_at", "ALTER TABLE cameras ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE"),
        ]

        for column_name, sql in columns:
            if self.column_exists(table_name, column_name):
                print(f"  Колонка '{table_name}.{column_name}' уже существует, пропускаем")
                continue

            self.cursor.execute(sql)
            print(f"  ✓ Колонка '{table_name}.{column_name}' создана")

        if self.column_exists(table_name, "rtsp_url"):
            self.cursor.execute(
                """
                UPDATE cameras
                SET source_url = rtsp_url
                WHERE source_url IS NULL AND rtsp_url IS NOT NULL
                """
            )
            print("  ✓ rtsp_url перенесён в source_url")

        if not self.index_exists("idx_cameras_source_type"):
            self.cursor.execute("CREATE INDEX idx_cameras_source_type ON cameras(source_type)")

    def create_parking_spots_table(self):
        """Создание таблицы parking_spots с проверкой существования"""
        table_name = "parking_spots"

        if self.table_exists(table_name):
            print(f"  Таблица '{table_name}' уже существует, пропускаем создание")
            return

        create_table_sql = """
        CREATE TABLE parking_spots (
            id BIGSERIAL PRIMARY KEY,
            parking_id BIGINT NOT NULL REFERENCES parkings(id) ON DELETE CASCADE,
            status SpotStatus NOT NULL DEFAULT 'free',
            spot_number VARCHAR(20) NOT NULL,
            road_vertex_id BIGINT REFERENCES road_vertices(id) ON DELETE SET NULL,

            CONSTRAINT unique_parking_spot_number UNIQUE(parking_id, spot_number)
        )
        """

        indexes = [
            ("idx_parking_spots_parking_id", "CREATE INDEX idx_parking_spots_parking_id ON parking_spots(parking_id)"),
            ("idx_parking_spots_status", "CREATE INDEX idx_parking_spots_status ON parking_spots(status)"),
            ("idx_parking_spots_road_vertex_id",
             "CREATE INDEX idx_parking_spots_road_vertex_id ON parking_spots(road_vertex_id)"),
            ("idx_parking_spots_parking_status",
             "CREATE INDEX idx_parking_spots_parking_status ON parking_spots(parking_id, status)")
        ]

        try:
            self.cursor.execute(create_table_sql)
            print(f"✓ Таблица '{table_name}' создана")
            self.migration_history.append(f"created_table_{table_name}")

            for index_name, index_sql in indexes:
                if not self.index_exists(index_name):
                    self.cursor.execute(index_sql)
                    print(f"  ✓ Индекс '{index_name}' создан")
                else:
                    print(f"  Индекс '{index_name}' уже существует, пропускаем")

        except Exception as e:
            print(f"✗ Ошибка создания таблицы {table_name}: {e}")
            raise

    def create_entrances_table(self):
        """Создание таблицы entrances с проверкой существования"""
        table_name = "entrances"

        if self.table_exists(table_name):
            print(f"  Таблица '{table_name}' уже существует, пропускаем создание")
            return

        create_table_sql = """
        CREATE TABLE entrances (
            id BIGSERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            parking_id BIGINT REFERENCES parkings(id) ON DELETE CASCADE,
            road_vertex_id BIGINT NOT NULL REFERENCES road_vertices(id) ON DELETE CASCADE
        )
        """

        indexes = [
            ("idx_entrances_parking_id", "CREATE INDEX idx_entrances_parking_id ON entrances(parking_id)"),
            ("idx_entrances_road_vertex_id", "CREATE INDEX idx_entrances_road_vertex_id ON entrances(road_vertex_id)")
        ]

        try:
            self.cursor.execute(create_table_sql)
            print(f"✓ Таблица '{table_name}' создана")
            self.migration_history.append(f"created_table_{table_name}")

            for index_name, index_sql in indexes:
                if not self.index_exists(index_name):
                    self.cursor.execute(index_sql)
                    print(f"  ✓ Индекс '{index_name}' создан")
                else:
                    print(f"  Индекс '{index_name}' уже существует, пропускаем")

        except Exception as e:
            print(f"✗ Ошибка создания таблицы {table_name}: {e}")
            raise

    def create_parking_occupancy_cache_table(self):
        """Создание таблицы parking_occupancy_cache с проверкой существования"""
        table_name = "parking_occupancy_cache"

        if self.table_exists(table_name):
            print(f"  Таблица '{table_name}' уже существует, пропускаем создание")
            return

        create_table_sql = """
        CREATE TABLE parking_occupancy_cache (
            id BIGSERIAL PRIMARY KEY,
            parking_id BIGINT NOT NULL UNIQUE REFERENCES parkings(id) ON DELETE CASCADE,
            total_spots INTEGER NOT NULL DEFAULT 0 CHECK (total_spots >= 0),
            free_spots INTEGER NOT NULL DEFAULT 0 CHECK (free_spots >= 0),
            occupancy_percentage DECIMAL(5,2) DEFAULT 0.00 CHECK (occupancy_percentage >= 0 AND occupancy_percentage <= 100),
            last_calculated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

            CONSTRAINT free_spots_not_exceed_total CHECK (free_spots <= total_spots)
        )
        """

        indexes = [
            ("idx_parking_occupancy_parking_id",
             "CREATE INDEX idx_parking_occupancy_parking_id ON parking_occupancy_cache(parking_id)"),
            ("idx_parking_occupancy_last_calculated",
             "CREATE INDEX idx_parking_occupancy_last_calculated ON parking_occupancy_cache(last_calculated)")
        ]

        try:
            self.cursor.execute(create_table_sql)
            print(f"✓ Таблица '{table_name}' создана")
            self.migration_history.append(f"created_table_{table_name}")

            for index_name, index_sql in indexes:
                if not self.index_exists(index_name):
                    self.cursor.execute(index_sql)
                    print(f"  ✓ Индекс '{index_name}' создан")
                else:
                    print(f"  Индекс '{index_name}' уже существует, пропускаем")

            # Проверяем существование функции и триггера
            self.cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM pg_proc 
                    WHERE proname = 'update_last_calculated'
                )
            """)
            function_exists = self.cursor.fetchone()[0]

            if not function_exists:
                trigger_sql = """
                CREATE OR REPLACE FUNCTION update_last_calculated()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.last_calculated = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;

                DROP TRIGGER IF EXISTS trigger_update_last_calculated ON parking_occupancy_cache;

                CREATE TRIGGER trigger_update_last_calculated
                    BEFORE UPDATE ON parking_occupancy_cache
                    FOR EACH ROW
                    EXECUTE FUNCTION update_last_calculated();
                """
                self.cursor.execute(trigger_sql)
                print("  ✓ Триггер для 'parking_occupancy_cache' создан")
            else:
                print("  Триггер для 'parking_occupancy_cache' уже существует, пропускаем")

        except Exception as e:
            print(f"✗ Ошибка создания таблицы {table_name}: {e}")
            raise

    def ensure_layout_storage_columns(self):
        """Дополнительные колонки для хранения layout/occupancy не файлами, а в таблицах.

        Старые JSON-файлы layout/occupancy остаются только runtime-кэшем для detector_supervisor,
        а источником истины становятся parkings, road_vertices, road_edges, entrances,
        parking_spots и parking_occupancy_cache.
        """
        if self.table_exists("parkings"):
            columns = [
                ("layout_meta", "ALTER TABLE parkings ADD COLUMN layout_meta JSONB DEFAULT '{}'::jsonb"),
                ("layout_zones", "ALTER TABLE parkings ADD COLUMN layout_zones JSONB DEFAULT '[]'::jsonb"),
                ("layout_calibration", "ALTER TABLE parkings ADD COLUMN layout_calibration JSONB"),
                ("layout_version", "ALTER TABLE parkings ADD COLUMN layout_version INTEGER NOT NULL DEFAULT 1"),
            ]
            for column_name, sql in columns:
                if self.column_exists("parkings", column_name):
                    print(f"  Колонка 'parkings.{column_name}' уже существует, пропускаем")
                    continue
                self.cursor.execute(sql)
                print(f"  ✓ Колонка 'parkings.{column_name}' создана")

        if self.table_exists("road_vertices"):
            columns = [
                ("client_id", "ALTER TABLE road_vertices ADD COLUMN client_id VARCHAR(100)"),
                ("x", "ALTER TABLE road_vertices ADD COLUMN x DOUBLE PRECISION"),
                ("y", "ALTER TABLE road_vertices ADD COLUMN y DOUBLE PRECISION"),
                ("label", "ALTER TABLE road_vertices ADD COLUMN label VARCHAR(100)"),
                ("payload", "ALTER TABLE road_vertices ADD COLUMN payload JSONB DEFAULT '{}'::jsonb"),
            ]
            for column_name, sql in columns:
                if self.column_exists("road_vertices", column_name):
                    print(f"  Колонка 'road_vertices.{column_name}' уже существует, пропускаем")
                    continue
                self.cursor.execute(sql)
                print(f"  ✓ Колонка 'road_vertices.{column_name}' создана")

            if not self.index_exists("uq_road_vertices_parking_client"):
                self.cursor.execute(
                    """
                    CREATE UNIQUE INDEX uq_road_vertices_parking_client
                    ON road_vertices(parking_id, client_id)
                    WHERE client_id IS NOT NULL
                    """
                )
                print("  ✓ Индекс 'uq_road_vertices_parking_client' создан")

        if self.table_exists("road_edges"):
            columns = [
                ("client_id", "ALTER TABLE road_edges ADD COLUMN client_id VARCHAR(100)"),
                ("parking_id",
                 "ALTER TABLE road_edges ADD COLUMN parking_id BIGINT REFERENCES parkings(id) ON DELETE CASCADE"),
                ("payload", "ALTER TABLE road_edges ADD COLUMN payload JSONB DEFAULT '{}'::jsonb"),
            ]
            for column_name, sql in columns:
                if self.column_exists("road_edges", column_name):
                    print(f"  Колонка 'road_edges.{column_name}' уже существует, пропускаем")
                    continue
                self.cursor.execute(sql)
                print(f"  ✓ Колонка 'road_edges.{column_name}' создана")

            # Для старых записей пытаемся восстановить parking_id по source-вершине.
            self.cursor.execute(
                """
                UPDATE road_edges e
                SET parking_id = v.parking_id
                FROM road_vertices v
                WHERE e.source = v.id
                AND e.parking_id IS NULL
                """
            )
            print("  ✓ road_edges.parking_id заполнен для существующих рёбер")

            if not self.index_exists("idx_road_edges_parking_id"):
                self.cursor.execute("CREATE INDEX idx_road_edges_parking_id ON road_edges(parking_id)")
                print("  ✓ Индекс 'idx_road_edges_parking_id' создан")

            if not self.index_exists("uq_road_edges_parking_client"):
                self.cursor.execute(
                    """
                    CREATE UNIQUE INDEX uq_road_edges_parking_client
                    ON road_edges(parking_id, client_id)
                    WHERE client_id IS NOT NULL
                    """
                )
                print("  ✓ Индекс 'uq_road_edges_parking_client' создан")

        if self.table_exists("parking_spots"):
            columns = [
                ("client_id", "ALTER TABLE parking_spots ADD COLUMN client_id VARCHAR(100)"),
                ("label", "ALTER TABLE parking_spots ADD COLUMN label VARCHAR(100)"),
                ("row_index", "ALTER TABLE parking_spots ADD COLUMN row_index INTEGER"),
                ("col_index", "ALTER TABLE parking_spots ADD COLUMN col_index INTEGER"),
                ("zone", "ALTER TABLE parking_spots ADD COLUMN zone VARCHAR(100)"),
                ("zone_id", "ALTER TABLE parking_spots ADD COLUMN zone_id VARCHAR(100)"),
                ("polygon", "ALTER TABLE parking_spots ADD COLUMN polygon JSONB DEFAULT '[]'::jsonb"),
                ("enabled", "ALTER TABLE parking_spots ADD COLUMN enabled BOOLEAN NOT NULL DEFAULT TRUE"),
                ("confidence", "ALTER TABLE parking_spots ADD COLUMN confidence DOUBLE PRECISION"),
                ("vehicle", "ALTER TABLE parking_spots ADD COLUMN vehicle JSONB"),
                ("last_status_at", "ALTER TABLE parking_spots ADD COLUMN last_status_at TIMESTAMP WITH TIME ZONE"),
                ("payload", "ALTER TABLE parking_spots ADD COLUMN payload JSONB DEFAULT '{}'::jsonb"),
            ]
            for column_name, sql in columns:
                if self.column_exists("parking_spots", column_name):
                    print(f"  Колонка 'parking_spots.{column_name}' уже существует, пропускаем")
                    continue
                self.cursor.execute(sql)
                print(f"  ✓ Колонка 'parking_spots.{column_name}' создана")

            self.cursor.execute(
                """
                UPDATE parking_spots
                SET client_id = spot_number
                WHERE client_id IS NULL
                """
            )
            print("  ✓ parking_spots.client_id заполнен из spot_number")

            if not self.index_exists("uq_parking_spots_parking_client"):
                self.cursor.execute(
                    """
                    CREATE UNIQUE INDEX uq_parking_spots_parking_client
                    ON parking_spots(parking_id, client_id)
                    WHERE client_id IS NOT NULL
                    """
                )
                print("  ✓ Индекс 'uq_parking_spots_parking_client' создан")

        if self.table_exists("entrances"):
            columns = [
                ("client_id", "ALTER TABLE entrances ADD COLUMN client_id VARCHAR(100)"),
                ("x", "ALTER TABLE entrances ADD COLUMN x DOUBLE PRECISION"),
                ("y", "ALTER TABLE entrances ADD COLUMN y DOUBLE PRECISION"),
                ("payload", "ALTER TABLE entrances ADD COLUMN payload JSONB DEFAULT '{}'::jsonb"),
            ]
            for column_name, sql in columns:
                if self.column_exists("entrances", column_name):
                    print(f"  Колонка 'entrances.{column_name}' уже существует, пропускаем")
                    continue
                self.cursor.execute(sql)
                print(f"  ✓ Колонка 'entrances.{column_name}' создана")

            if not self.index_exists("uq_entrances_parking_client"):
                self.cursor.execute(
                    """
                    CREATE UNIQUE INDEX uq_entrances_parking_client
                    ON entrances(parking_id, client_id)
                    WHERE client_id IS NOT NULL
                    """
                )
                print("  ✓ Индекс 'uq_entrances_parking_client' создан")

        if self.table_exists("parking_occupancy_cache"):
            columns = [
                ("occupied_spots",
                 "ALTER TABLE parking_occupancy_cache ADD COLUMN occupied_spots INTEGER NOT NULL DEFAULT 0 CHECK (occupied_spots >= 0)"),
                ("unknown_spots",
                 "ALTER TABLE parking_occupancy_cache ADD COLUMN unknown_spots INTEGER NOT NULL DEFAULT 0 CHECK (unknown_spots >= 0)"),
                ("frame_index", "ALTER TABLE parking_occupancy_cache ADD COLUMN frame_index INTEGER"),
                ("timestamp_sec", "ALTER TABLE parking_occupancy_cache ADD COLUMN timestamp_sec DOUBLE PRECISION"),
                ("params", "ALTER TABLE parking_occupancy_cache ADD COLUMN params JSONB DEFAULT '{}'::jsonb"),
                ("source_type", "ALTER TABLE parking_occupancy_cache ADD COLUMN source_type VARCHAR(50)"),
                ("source_path", "ALTER TABLE parking_occupancy_cache ADD COLUMN source_path VARCHAR(500)"),
                ("camera_id",
                 "ALTER TABLE parking_occupancy_cache ADD COLUMN camera_id BIGINT REFERENCES cameras(id) ON DELETE SET NULL"),
            ]
            for column_name, sql in columns:
                if self.column_exists("parking_occupancy_cache", column_name):
                    print(f"  Колонка 'parking_occupancy_cache.{column_name}' уже существует, пропускаем")
                    continue
                self.cursor.execute(sql)
                print(f"  ✓ Колонка 'parking_occupancy_cache.{column_name}' создана")

            self.cursor.execute(
                """
                UPDATE parking_occupancy_cache
                SET occupied_spots = GREATEST(total_spots - free_spots, 0)
                WHERE occupied_spots = 0
                """
            )
            print("  ✓ occupied_spots рассчитан для существующего cache")

    def get_migration_status(self) -> dict:
        """
        Получает статус миграции всех таблиц

        Returns:
            Словарь со статусом каждой таблицы
        """
        tables = [
            'companies', 'users', 'login_attempts', 'parkings', 'road_vertices', 'road_edges',
            'cameras', 'parking_spots', 'entrances', 'parking_occupancy_cache'
        ]

        status = {}
        for table in tables:
            status[table] = self.table_exists(table)

        return status

    def run_all_migrations(self, create_admin: bool = False, force: bool = False):
        """
        Запуск всех миграций

        Args:
            create_admin: Создать ли администратора по умолчанию
            force: Принудительное создание таблиц даже если они существуют
        """
        try:
            self.connect()

            print("\n=== Начало миграции базы данных ===\n")

            # Показываем статус существующих таблиц
            if not force:
                status = self.get_migration_status()
                existing_tables = [name for name, exists in status.items() if exists]
                if existing_tables:
                    print(f"Найдены существующие таблицы: {', '.join(existing_tables)}")
                    print("Будут созданы только отсутствующие таблицы\n")

            # Создаем ENUM типы
            self.create_enums()

            # Создаем таблицы в правильном порядке (с учетом зависимостей)
            self.create_companies_table()
            self.ensure_default_company()

            self.create_users_table()
            self.create_login_attempts_table()
            self.create_parkings_table()
            self.create_road_vertices_table()
            self.create_road_edges_table()
            self.create_cameras_table()
            self.create_parking_spots_table()
            self.create_entrances_table()
            self.create_parking_occupancy_cache_table()

            # Дополнительные поля для хранения layout/occupancy в нормализованных таблицах.
            self.ensure_layout_storage_columns()

            if create_admin:
                self.create_default_admin()

            self.conn.commit()

            print("\n=== Миграция успешно завершена ===\n")

            # Показываем итоговый статус
            final_status = self.get_migration_status()
            print("Итоговый статус таблиц:")
            for table, exists in final_status.items():
                status_icon = "✓" if exists else "✗"
                print(f"  {status_icon} {table}")

        except Exception as e:
            print(f"\n✗ Ошибка при выполнении миграции: {e}")
            if self.conn:
                self.conn.rollback()
            raise
        finally:
            self.disconnect()


def run_migrations(db_url: str, create_admin: bool = False, force: bool = False):
    """
    Функция для запуска миграций

    Args:
        db_url: URL подключения к PostgreSQL
        create_admin: Создать ли администратора по умолчанию
        force: Принудительное создание таблиц даже если они существуют
    """
    migration = DatabaseMigration(db_url)
    migration.run_all_migrations(create_admin=create_admin, force=force)


if __name__ == "__main__":
    # Пример использования
    import os

    # Получаем URL базы данных из переменных окружения
    DATABASE_URL = os.getenv(
        'DATABASE_URL',
        'postgresql://user:password@localhost:5432/parking_db'
    )

    # Запускаем миграции
    # force=False - создаем только отсутствующие таблицы
    # force=True - принудительно создаем все таблицы (удаляем существующие)
    run_migrations(DATABASE_URL, create_admin=True, force=False)
