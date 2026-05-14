import os

import bcrypt
import psycopg2


class DatabaseMigration:
    """Класс для управления миграциями базы данных"""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.conn = None
        self.cursor = None
        self.migration_history = []

    def connect(self):
        try:
            self.conn = psycopg2.connect(self.db_url)
            self.cursor = self.conn.cursor()
            print("✓ Соединение с базой данных установлено")
        except Exception as e:
            print(f"✗ Ошибка подключения к БД: {e}")
            raise

    def disconnect(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("✓ Соединение с БД закрыто")

    def table_exists(self, table_name: str) -> bool:
        try:
            self.cursor.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = %s
                )
                """,
                (table_name,),
            )
            return self.cursor.fetchone()[0]
        except Exception as e:
            print(f"  Ошибка при проверке таблицы {table_name}: {e}")
            return False

    def enum_exists(self, enum_name: str) -> bool:
        try:
            self.cursor.execute(
                """
                SELECT EXISTS (
                    SELECT FROM pg_type
                    WHERE typname = %s
                )
                """,
                (enum_name.lower(),),
            )
            return self.cursor.fetchone()[0]
        except Exception as e:
            print(f"  Ошибка при проверке ENUM {enum_name}: {e}")
            return False

    def enum_value_exists(self, enum_name: str, enum_value: str) -> bool:
        try:
            self.cursor.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM pg_type t
                    JOIN pg_enum e ON t.oid = e.enumtypid
                    WHERE t.typname = %s
                    AND e.enumlabel = %s
                )
                """,
                (enum_name.lower(), enum_value),
            )
            return self.cursor.fetchone()[0]
        except Exception as e:
            print(f"  Ошибка при проверке значения ENUM {enum_name}.{enum_value}: {e}")
            return False

    def index_exists(self, index_name: str) -> bool:
        try:
            self.cursor.execute(
                """
                SELECT EXISTS (
                    SELECT FROM pg_indexes
                    WHERE indexname = %s
                )
                """,
                (index_name,),
            )
            return self.cursor.fetchone()[0]
        except Exception as e:
            print(f"  Ошибка при проверке индекса {index_name}: {e}")
            return False

    def column_exists(self, table_name: str, column_name: str) -> bool:
        try:
            self.cursor.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.columns
                    WHERE table_schema = 'public'
                    AND table_name = %s
                    AND column_name = %s
                )
                """,
                (table_name, column_name),
            )
            return self.cursor.fetchone()[0]
        except Exception as e:
            print(f"  Ошибка при проверке колонки {table_name}.{column_name}: {e}")
            return False

    def create_index_if_not_exists(self, index_name: str, index_sql: str):
        if not self.index_exists(index_name):
            self.cursor.execute(index_sql)
            print(f"  ✓ Индекс '{index_name}' создан")
        else:
            print(f"  Индекс '{index_name}' уже существует, пропускаем")

    def add_column_if_not_exists(self, table_name: str, column_name: str, sql: str):
        if self.column_exists(table_name, column_name):
            print(f"  Колонка '{table_name}.{column_name}' уже существует, пропускаем")
            return

        self.cursor.execute(sql)
        print(f"  ✓ Колонка '{table_name}.{column_name}' создана")

    def create_enums(self):
        enums = [
            (
                "userrole",
                "CREATE TYPE UserRole AS ENUM ('super_admin', 'admin', 'user')",
                ["super_admin", "admin", "user"],
            ),
            (
                "camerastatus",
                "CREATE TYPE CameraStatus AS ENUM ('online', 'offline', 'error')",
                ["online", "offline", "error"],
            ),
            (
                "spotstatus",
                "CREATE TYPE SpotStatus AS ENUM ('free', 'occupied', 'unknown')",
                ["free", "occupied", "unknown"],
            ),
        ]

        for enum_name, enum_sql, values in enums:
            if not self.enum_exists(enum_name):
                self.cursor.execute(enum_sql)
                print(f"✓ ENUM тип '{enum_name}' создан")
                self.migration_history.append(f"created_enum_{enum_name}")
                continue

            print(f"  ENUM тип '{enum_name}' уже существует, проверяем значения")

            for value in values:
                if not self.enum_value_exists(enum_name, value):
                    self.cursor.execute(
                        f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS %s",
                        (value,),
                    )
                    print(f"  ✓ Значение ENUM '{enum_name}.{value}' добавлено")

    def create_companies_table(self):
        table_name = "companies"

        if self.table_exists(table_name):
            print(f"  Таблица '{table_name}' уже существует, пропускаем создание")
            self.ensure_companies_table_columns()
            return

        self.cursor.execute(
            """
            CREATE TABLE companies (
                id BIGSERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                slug VARCHAR(100) UNIQUE NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE
            )
            """
        )

        print(f"✓ Таблица '{table_name}' создана")
        self.migration_history.append(f"created_table_{table_name}")
        self.ensure_companies_table_columns()

    def ensure_companies_table_columns(self):
        table_name = "companies"

        alter_statements = [
            ("name", "ALTER TABLE companies ADD COLUMN name VARCHAR(255)"),
            ("slug", "ALTER TABLE companies ADD COLUMN slug VARCHAR(100)"),
            ("is_active", "ALTER TABLE companies ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE"),
            ("created_at", "ALTER TABLE companies ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
            ("updated_at", "ALTER TABLE companies ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE"),
        ]

        for column_name, sql in alter_statements:
            self.add_column_if_not_exists(table_name, column_name, sql)

        self.create_index_if_not_exists(
            "idx_companies_slug",
            "CREATE INDEX idx_companies_slug ON companies(slug)",
        )
        self.create_index_if_not_exists(
            "idx_companies_is_active",
            "CREATE INDEX idx_companies_is_active ON companies(is_active)",
        )

    def create_users_table(self):
        table_name = "users"

        if self.table_exists(table_name):
            print(f"  Таблица '{table_name}' уже существует, пропускаем создание")
            self.ensure_users_table_columns()
            return

        self.cursor.execute(
            """
            CREATE TABLE users (
                id BIGSERIAL PRIMARY KEY,
                company_id BIGINT REFERENCES companies(id) ON DELETE SET NULL,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL DEFAULT 'user',
                full_name VARCHAR(255),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                failed_attempts INTEGER NOT NULL DEFAULT 0,
                locked_until TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE,

                CONSTRAINT username_min_length CHECK (LENGTH(username) >= 3)
            )
            """
        )

        print(f"✓ Таблица '{table_name}' создана")
        self.migration_history.append(f"created_table_{table_name}")
        self.ensure_users_table_columns()

    def ensure_users_table_columns(self):
        table_name = "users"

        alter_statements = [
            ("company_id", "ALTER TABLE users ADD COLUMN company_id BIGINT REFERENCES companies(id) ON DELETE SET NULL"),
            ("role", "ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'"),
            ("full_name", "ALTER TABLE users ADD COLUMN full_name VARCHAR(255)"),
            ("is_active", "ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE"),
            ("failed_attempts", "ALTER TABLE users ADD COLUMN failed_attempts INTEGER NOT NULL DEFAULT 0"),
            ("locked_until", "ALTER TABLE users ADD COLUMN locked_until TIMESTAMP WITH TIME ZONE"),
            ("created_at", "ALTER TABLE users ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
            ("updated_at", "ALTER TABLE users ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE"),
        ]

        for column_name, sql in alter_statements:
            self.add_column_if_not_exists(table_name, column_name, sql)

        self.create_index_if_not_exists("idx_users_company_id", "CREATE INDEX idx_users_company_id ON users(company_id)")
        self.create_index_if_not_exists("idx_users_username", "CREATE INDEX idx_users_username ON users(username)")
        self.create_index_if_not_exists("idx_users_email", "CREATE INDEX idx_users_email ON users(email)")
        self.create_index_if_not_exists("idx_users_is_active", "CREATE INDEX idx_users_is_active ON users(is_active)")
        self.create_index_if_not_exists("idx_users_locked_until", "CREATE INDEX idx_users_locked_until ON users(locked_until)")

    def create_login_attempts_table(self):
        table_name = "login_attempts"

        if self.table_exists(table_name):
            print(f"  Таблица '{table_name}' уже существует, пропускаем создание")
            return

        self.cursor.execute(
            """
            CREATE TABLE login_attempts (
                id BIGSERIAL PRIMARY KEY,
                ip_address VARCHAR(45) NOT NULL,
                login VARCHAR(255) NOT NULL,
                was_successful BOOLEAN NOT NULL DEFAULT FALSE,
                attempted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
            """
        )

        print(f"✓ Таблица '{table_name}' создана")
        self.migration_history.append(f"created_table_{table_name}")

        self.create_index_if_not_exists(
            "idx_login_attempts_ip_address",
            "CREATE INDEX idx_login_attempts_ip_address ON login_attempts(ip_address)",
        )
        self.create_index_if_not_exists(
            "idx_login_attempts_login",
            "CREATE INDEX idx_login_attempts_login ON login_attempts(login)",
        )
        self.create_index_if_not_exists(
            "idx_login_attempts_attempted_at",
            "CREATE INDEX idx_login_attempts_attempted_at ON login_attempts(attempted_at)",
        )

    def create_default_company(self) -> int:
        company_name = os.getenv("INITIAL_COMPANY_NAME", "Default Company")
        company_slug = os.getenv("INITIAL_COMPANY_SLUG", "default-company")

        self.cursor.execute(
            """
            INSERT INTO companies (name, slug, is_active)
            VALUES (%s, %s, TRUE)
            ON CONFLICT (slug) DO UPDATE
            SET name = EXCLUDED.name,
                is_active = TRUE
            RETURNING id
            """,
            (company_name, company_slug),
        )

        company_id = self.cursor.fetchone()[0]
        print(f"✓ Компания по умолчанию создана или уже существует: {company_slug}")
        return company_id

    def create_default_admin(self):
        username = os.getenv("INITIAL_ADMIN_USERNAME")
        email = os.getenv("INITIAL_ADMIN_EMAIL")
        password = os.getenv("INITIAL_ADMIN_PASSWORD")
        full_name = os.getenv("INITIAL_ADMIN_FULL_NAME")

        if not username or not email or not password:
            print("  Начальный администратор не настроен через env, пропускаем создание")
            return

        company_id = self.create_default_company()

        self.cursor.execute(
            "SELECT id, company_id FROM users WHERE username = %s OR email = %s LIMIT 1",
            (username, email),
        )

        existing_user = self.cursor.fetchone()

        if existing_user:
            user_id = existing_user[0]
            existing_company_id = existing_user[1]

            if existing_company_id is None:
                self.cursor.execute(
                    """
                    UPDATE users
                    SET company_id = %s
                    WHERE id = %s
                    """,
                    (company_id, user_id),
                )
                print("  Начальный администратор уже существует, company_id заполнен")
            else:
                print("  Начальный администратор уже существует, company_id уже задан")

            return

        password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(),
        ).decode("utf-8")

        self.cursor.execute(
            """
            INSERT INTO users (
                company_id,
                username,
                email,
                password_hash,
                role,
                full_name,
                is_active,
                failed_attempts,
                locked_until
            )
            VALUES (%s, %s, %s, %s, 'admin', %s, TRUE, 0, NULL)
            """,
            (company_id, username, email, password_hash, full_name),
        )

        print("✓ Начальный администратор создан")

    def create_parkings_table(self):
        table_name = "parkings"

        if self.table_exists(table_name):
            print(f"  Таблица '{table_name}' уже существует, пропускаем создание")
            self.ensure_parkings_table_columns()
            return

        self.cursor.execute(
            """
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
                layout_meta JSONB NOT NULL DEFAULT '{}'::jsonb,
                layout_zones JSONB NOT NULL DEFAULT '[]'::jsonb,
                layout_calibration JSONB,
                layout_version INTEGER NOT NULL DEFAULT 0,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE
            )
            """
        )

        print(f"✓ Таблица '{table_name}' создана")
        self.migration_history.append(f"created_table_{table_name}")
        self.ensure_parkings_table_columns()

    def ensure_parkings_table_columns(self):
        table_name = "parkings"

        alter_statements = [
            ("company_id", "ALTER TABLE parkings ADD COLUMN company_id BIGINT REFERENCES companies(id) ON DELETE CASCADE"),
            ("slug", "ALTER TABLE parkings ADD COLUMN slug VARCHAR(100)"),
            ("layout_file_path", "ALTER TABLE parkings ADD COLUMN layout_file_path VARCHAR(500)"),
            ("map_file_path", "ALTER TABLE parkings ADD COLUMN map_file_path VARCHAR(500)"),
            ("occupancy_file_path", "ALTER TABLE parkings ADD COLUMN occupancy_file_path VARCHAR(500)"),
            ("screenshot_file_path", "ALTER TABLE parkings ADD COLUMN screenshot_file_path VARCHAR(500)"),
            ("debug_frame_path", "ALTER TABLE parkings ADD COLUMN debug_frame_path VARCHAR(500)"),
            ("layout_meta", "ALTER TABLE parkings ADD COLUMN layout_meta JSONB NOT NULL DEFAULT '{}'::jsonb"),
            ("layout_zones", "ALTER TABLE parkings ADD COLUMN layout_zones JSONB NOT NULL DEFAULT '[]'::jsonb"),
            ("layout_calibration", "ALTER TABLE parkings ADD COLUMN layout_calibration JSONB"),
            ("layout_version", "ALTER TABLE parkings ADD COLUMN layout_version INTEGER NOT NULL DEFAULT 0"),
            ("is_active", "ALTER TABLE parkings ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE"),
            ("created_at", "ALTER TABLE parkings ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
            ("updated_at", "ALTER TABLE parkings ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE"),
        ]

        for column_name, sql in alter_statements:
            self.add_column_if_not_exists(table_name, column_name, sql)

        self.create_index_if_not_exists("idx_parkings_company_id", "CREATE INDEX idx_parkings_company_id ON parkings(company_id)")
        self.create_index_if_not_exists("idx_parkings_name", "CREATE INDEX idx_parkings_name ON parkings(name)")
        self.create_index_if_not_exists("idx_parkings_slug", "CREATE INDEX idx_parkings_slug ON parkings(slug)")
        self.create_index_if_not_exists("idx_parkings_is_active", "CREATE INDEX idx_parkings_is_active ON parkings(is_active)")

    def create_road_vertices_table(self):
        table_name = "road_vertices"

        if self.table_exists(table_name):
            print(f"  Таблица '{table_name}' уже существует, пропускаем создание")
            self.ensure_road_vertices_table_columns()
            return

        self.cursor.execute(
            """
            CREATE TABLE road_vertices (
                id BIGSERIAL PRIMARY KEY,
                parking_id BIGINT REFERENCES parkings(id) ON DELETE CASCADE,
                client_id VARCHAR(100),
                x FLOAT,
                y FLOAT,
                label VARCHAR(255),
                is_spot BOOLEAN NOT NULL DEFAULT FALSE,
                is_entrance BOOLEAN NOT NULL DEFAULT FALSE,
                payload JSONB NOT NULL DEFAULT '{}'::jsonb
            )
            """
        )

        print(f"✓ Таблица '{table_name}' создана")
        self.migration_history.append(f"created_table_{table_name}")
        self.ensure_road_vertices_table_columns()

    def ensure_road_vertices_table_columns(self):
        table_name = "road_vertices"

        alter_statements = [
            ("parking_id", "ALTER TABLE road_vertices ADD COLUMN parking_id BIGINT REFERENCES parkings(id) ON DELETE CASCADE"),
            ("client_id", "ALTER TABLE road_vertices ADD COLUMN client_id VARCHAR(100)"),
            ("x", "ALTER TABLE road_vertices ADD COLUMN x FLOAT"),
            ("y", "ALTER TABLE road_vertices ADD COLUMN y FLOAT"),
            ("label", "ALTER TABLE road_vertices ADD COLUMN label VARCHAR(255)"),
            ("is_spot", "ALTER TABLE road_vertices ADD COLUMN is_spot BOOLEAN NOT NULL DEFAULT FALSE"),
            ("is_entrance", "ALTER TABLE road_vertices ADD COLUMN is_entrance BOOLEAN NOT NULL DEFAULT FALSE"),
            ("payload", "ALTER TABLE road_vertices ADD COLUMN payload JSONB NOT NULL DEFAULT '{}'::jsonb"),
        ]

        for column_name, sql in alter_statements:
            self.add_column_if_not_exists(table_name, column_name, sql)

        self.create_index_if_not_exists("idx_road_vertices_parking_id", "CREATE INDEX idx_road_vertices_parking_id ON road_vertices(parking_id)")
        self.create_index_if_not_exists("idx_road_vertices_client_id", "CREATE INDEX idx_road_vertices_client_id ON road_vertices(client_id)")
        self.create_index_if_not_exists("idx_road_vertices_is_spot", "CREATE INDEX idx_road_vertices_is_spot ON road_vertices(is_spot)")
        self.create_index_if_not_exists("idx_road_vertices_is_entrance", "CREATE INDEX idx_road_vertices_is_entrance ON road_vertices(is_entrance)")

    def create_road_edges_table(self):
        table_name = "road_edges"

        if self.table_exists(table_name):
            print(f"  Таблица '{table_name}' уже существует, пропускаем создание")
            self.ensure_road_edges_table_columns()
            return

        self.cursor.execute(
            """
            CREATE TABLE road_edges (
                id BIGSERIAL PRIMARY KEY,
                parking_id BIGINT REFERENCES parkings(id) ON DELETE CASCADE,
                client_id VARCHAR(100),
                source BIGINT REFERENCES road_vertices(id) ON DELETE CASCADE,
                destination BIGINT REFERENCES road_vertices(id) ON DELETE CASCADE,
                length_meters FLOAT NOT NULL,
                one_way BOOLEAN NOT NULL DEFAULT FALSE,
                is_bidirectional BOOLEAN NOT NULL DEFAULT TRUE,
                payload JSONB NOT NULL DEFAULT '{}'::jsonb,

                CONSTRAINT source_destination_diff CHECK (source IS NULL OR destination IS NULL OR source != destination),
                CONSTRAINT length_meters_positive CHECK (length_meters > 0)
            )
            """
        )

        print(f"✓ Таблица '{table_name}' создана")
        self.migration_history.append(f"created_table_{table_name}")
        self.ensure_road_edges_table_columns()

    def ensure_road_edges_table_columns(self):
        table_name = "road_edges"

        alter_statements = [
            ("parking_id", "ALTER TABLE road_edges ADD COLUMN parking_id BIGINT REFERENCES parkings(id) ON DELETE CASCADE"),
            ("client_id", "ALTER TABLE road_edges ADD COLUMN client_id VARCHAR(100)"),
            ("source", "ALTER TABLE road_edges ADD COLUMN source BIGINT REFERENCES road_vertices(id) ON DELETE CASCADE"),
            ("destination", "ALTER TABLE road_edges ADD COLUMN destination BIGINT REFERENCES road_vertices(id) ON DELETE CASCADE"),
            ("one_way", "ALTER TABLE road_edges ADD COLUMN one_way BOOLEAN NOT NULL DEFAULT FALSE"),
            ("is_bidirectional", "ALTER TABLE road_edges ADD COLUMN is_bidirectional BOOLEAN NOT NULL DEFAULT TRUE"),
            ("payload", "ALTER TABLE road_edges ADD COLUMN payload JSONB NOT NULL DEFAULT '{}'::jsonb"),
        ]

        for column_name, sql in alter_statements:
            self.add_column_if_not_exists(table_name, column_name, sql)

        self.create_index_if_not_exists("idx_road_edges_parking_id", "CREATE INDEX idx_road_edges_parking_id ON road_edges(parking_id)")
        self.create_index_if_not_exists("idx_road_edges_client_id", "CREATE INDEX idx_road_edges_client_id ON road_edges(client_id)")
        self.create_index_if_not_exists("idx_road_edges_source", "CREATE INDEX idx_road_edges_source ON road_edges(source)")
        self.create_index_if_not_exists("idx_road_edges_destination", "CREATE INDEX idx_road_edges_destination ON road_edges(destination)")
        self.create_index_if_not_exists("idx_road_edges_source_dest", "CREATE INDEX idx_road_edges_source_dest ON road_edges(source, destination)")

    def create_cameras_table(self):
        table_name = "cameras"

        if self.table_exists(table_name):
            print(f"  Таблица '{table_name}' уже существует, пропускаем создание")
            self.ensure_cameras_table_columns()
            return

        self.cursor.execute(
            """
            CREATE TABLE cameras (
                id BIGSERIAL PRIMARY KEY,
                parking_id BIGINT NOT NULL REFERENCES parkings(id) ON DELETE CASCADE,
                name VARCHAR(100) NOT NULL,
                source_type VARCHAR(20) NOT NULL DEFAULT 'rtsp',
                source_url VARCHAR(1000),
                test_video_path VARCHAR(500),
                status VARCHAR(20) NOT NULL DEFAULT 'offline',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                last_snapshot_path VARCHAR(500),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE
            )
            """
        )

        print(f"✓ Таблица '{table_name}' создана")
        self.migration_history.append(f"created_table_{table_name}")
        self.ensure_cameras_table_columns()

    def ensure_cameras_table_columns(self):
        table_name = "cameras"

        if self.column_exists(table_name, "rtsp_url") and not self.column_exists(table_name, "source_url"):
            self.cursor.execute("ALTER TABLE cameras RENAME COLUMN rtsp_url TO source_url")
            print("  ✓ Колонка 'cameras.rtsp_url' переименована в 'source_url'")

        alter_statements = [
            ("parking_id", "ALTER TABLE cameras ADD COLUMN parking_id BIGINT REFERENCES parkings(id) ON DELETE CASCADE"),
            ("source_type", "ALTER TABLE cameras ADD COLUMN source_type VARCHAR(20) NOT NULL DEFAULT 'rtsp'"),
            ("source_url", "ALTER TABLE cameras ADD COLUMN source_url VARCHAR(1000)"),
            ("test_video_path", "ALTER TABLE cameras ADD COLUMN test_video_path VARCHAR(500)"),
            ("status", "ALTER TABLE cameras ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'offline'"),
            ("is_active", "ALTER TABLE cameras ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE"),
            ("last_snapshot_path", "ALTER TABLE cameras ADD COLUMN last_snapshot_path VARCHAR(500)"),
            ("created_at", "ALTER TABLE cameras ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
            ("updated_at", "ALTER TABLE cameras ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE"),
        ]

        for column_name, sql in alter_statements:
            self.add_column_if_not_exists(table_name, column_name, sql)

        self.create_index_if_not_exists("idx_cameras_parking_id", "CREATE INDEX idx_cameras_parking_id ON cameras(parking_id)")
        self.create_index_if_not_exists("idx_cameras_status", "CREATE INDEX idx_cameras_status ON cameras(status)")
        self.create_index_if_not_exists("idx_cameras_source_type", "CREATE INDEX idx_cameras_source_type ON cameras(source_type)")
        self.create_index_if_not_exists("idx_cameras_is_active", "CREATE INDEX idx_cameras_is_active ON cameras(is_active)")

    def create_parking_spots_table(self):
        table_name = "parking_spots"

        if self.table_exists(table_name):
            print(f"  Таблица '{table_name}' уже существует, пропускаем создание")
            self.ensure_parking_spots_table_columns()
            return

        self.cursor.execute(
            """
            CREATE TABLE parking_spots (
                id BIGSERIAL PRIMARY KEY,
                parking_id BIGINT REFERENCES parkings(id) ON DELETE CASCADE,
                client_id VARCHAR(100),
                label VARCHAR(255),
                spot_number VARCHAR(20) NOT NULL,
                status SpotStatus NOT NULL DEFAULT 'free',
                road_vertex_id BIGINT REFERENCES road_vertices(id) ON DELETE SET NULL,
                row_index INTEGER,
                col_index INTEGER,
                zone VARCHAR(100),
                zone_id VARCHAR(100),
                polygon JSONB NOT NULL DEFAULT '[]'::jsonb,
                enabled BOOLEAN NOT NULL DEFAULT TRUE,
                confidence FLOAT,
                vehicle JSONB,
                last_status_at TIMESTAMP WITH TIME ZONE,
                payload JSONB NOT NULL DEFAULT '{}'::jsonb,

                CONSTRAINT unique_parking_spot_number UNIQUE(parking_id, spot_number)
            )
            """
        )

        print(f"✓ Таблица '{table_name}' создана")
        self.migration_history.append(f"created_table_{table_name}")
        self.ensure_parking_spots_table_columns()

    def ensure_parking_spots_table_columns(self):
        table_name = "parking_spots"

        alter_statements = [
            ("parking_id", "ALTER TABLE parking_spots ADD COLUMN parking_id BIGINT REFERENCES parkings(id) ON DELETE CASCADE"),
            ("client_id", "ALTER TABLE parking_spots ADD COLUMN client_id VARCHAR(100)"),
            ("label", "ALTER TABLE parking_spots ADD COLUMN label VARCHAR(255)"),
            ("spot_number", "ALTER TABLE parking_spots ADD COLUMN spot_number VARCHAR(20)"),
            ("road_vertex_id", "ALTER TABLE parking_spots ADD COLUMN road_vertex_id BIGINT REFERENCES road_vertices(id) ON DELETE SET NULL"),
            ("row_index", "ALTER TABLE parking_spots ADD COLUMN row_index INTEGER"),
            ("col_index", "ALTER TABLE parking_spots ADD COLUMN col_index INTEGER"),
            ("zone", "ALTER TABLE parking_spots ADD COLUMN zone VARCHAR(100)"),
            ("zone_id", "ALTER TABLE parking_spots ADD COLUMN zone_id VARCHAR(100)"),
            ("polygon", "ALTER TABLE parking_spots ADD COLUMN polygon JSONB NOT NULL DEFAULT '[]'::jsonb"),
            ("enabled", "ALTER TABLE parking_spots ADD COLUMN enabled BOOLEAN NOT NULL DEFAULT TRUE"),
            ("confidence", "ALTER TABLE parking_spots ADD COLUMN confidence FLOAT"),
            ("vehicle", "ALTER TABLE parking_spots ADD COLUMN vehicle JSONB"),
            ("last_status_at", "ALTER TABLE parking_spots ADD COLUMN last_status_at TIMESTAMP WITH TIME ZONE"),
            ("payload", "ALTER TABLE parking_spots ADD COLUMN payload JSONB NOT NULL DEFAULT '{}'::jsonb"),
        ]

        for column_name, sql in alter_statements:
            self.add_column_if_not_exists(table_name, column_name, sql)

        self.create_index_if_not_exists("idx_parking_spots_parking_id", "CREATE INDEX idx_parking_spots_parking_id ON parking_spots(parking_id)")
        self.create_index_if_not_exists("idx_parking_spots_client_id", "CREATE INDEX idx_parking_spots_client_id ON parking_spots(client_id)")
        self.create_index_if_not_exists("idx_parking_spots_status", "CREATE INDEX idx_parking_spots_status ON parking_spots(status)")
        self.create_index_if_not_exists("idx_parking_spots_road_vertex_id", "CREATE INDEX idx_parking_spots_road_vertex_id ON parking_spots(road_vertex_id)")
        self.create_index_if_not_exists("idx_parking_spots_parking_status", "CREATE INDEX idx_parking_spots_parking_status ON parking_spots(parking_id, status)")

    def create_entrances_table(self):
        table_name = "entrances"

        if self.table_exists(table_name):
            print(f"  Таблица '{table_name}' уже существует, пропускаем создание")
            self.ensure_entrances_table_columns()
            return

        self.cursor.execute(
            """
            CREATE TABLE entrances (
                id BIGSERIAL PRIMARY KEY,
                parking_id BIGINT REFERENCES parkings(id) ON DELETE CASCADE,
                client_id VARCHAR(100),
                name VARCHAR(100) NOT NULL,
                road_vertex_id BIGINT NOT NULL REFERENCES road_vertices(id) ON DELETE CASCADE,
                x FLOAT,
                y FLOAT,
                payload JSONB NOT NULL DEFAULT '{}'::jsonb
            )
            """
        )

        print(f"✓ Таблица '{table_name}' создана")
        self.migration_history.append(f"created_table_{table_name}")
        self.ensure_entrances_table_columns()

    def ensure_entrances_table_columns(self):
        table_name = "entrances"

        alter_statements = [
            ("parking_id", "ALTER TABLE entrances ADD COLUMN parking_id BIGINT REFERENCES parkings(id) ON DELETE CASCADE"),
            ("client_id", "ALTER TABLE entrances ADD COLUMN client_id VARCHAR(100)"),
            ("name", "ALTER TABLE entrances ADD COLUMN name VARCHAR(100)"),
            ("road_vertex_id", "ALTER TABLE entrances ADD COLUMN road_vertex_id BIGINT REFERENCES road_vertices(id) ON DELETE CASCADE"),
            ("x", "ALTER TABLE entrances ADD COLUMN x FLOAT"),
            ("y", "ALTER TABLE entrances ADD COLUMN y FLOAT"),
            ("payload", "ALTER TABLE entrances ADD COLUMN payload JSONB NOT NULL DEFAULT '{}'::jsonb"),
        ]

        for column_name, sql in alter_statements:
            self.add_column_if_not_exists(table_name, column_name, sql)

        self.create_index_if_not_exists("idx_entrances_parking_id", "CREATE INDEX idx_entrances_parking_id ON entrances(parking_id)")
        self.create_index_if_not_exists("idx_entrances_client_id", "CREATE INDEX idx_entrances_client_id ON entrances(client_id)")
        self.create_index_if_not_exists("idx_entrances_road_vertex_id", "CREATE INDEX idx_entrances_road_vertex_id ON entrances(road_vertex_id)")

    def create_parking_occupancy_cache_table(self):
        table_name = "parking_occupancy_cache"

        if self.table_exists(table_name):
            print(f"  Таблица '{table_name}' уже существует, пропускаем создание")
            self.ensure_parking_occupancy_cache_table_columns()
            return

        self.cursor.execute(
            """
            CREATE TABLE parking_occupancy_cache (
                id BIGSERIAL PRIMARY KEY,
                parking_id BIGINT UNIQUE REFERENCES parkings(id) ON DELETE CASCADE,
                total_spots INTEGER NOT NULL DEFAULT 0,
                free_spots INTEGER NOT NULL DEFAULT 0,
                occupied_spots INTEGER NOT NULL DEFAULT 0,
                unknown_spots INTEGER NOT NULL DEFAULT 0,
                occupancy_percentage FLOAT NOT NULL DEFAULT 0.0,
                last_calculated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                frame_index INTEGER,
                timestamp_sec FLOAT,
                params JSONB NOT NULL DEFAULT '{}'::jsonb,
                source_type VARCHAR(20),
                source_path VARCHAR(1000),
                camera_id BIGINT REFERENCES cameras(id) ON DELETE SET NULL,

                CONSTRAINT total_spots_non_negative CHECK (total_spots >= 0),
                CONSTRAINT free_spots_non_negative CHECK (free_spots >= 0),
                CONSTRAINT occupied_spots_non_negative CHECK (occupied_spots >= 0),
                CONSTRAINT unknown_spots_non_negative CHECK (unknown_spots >= 0),
                CONSTRAINT occupancy_percentage_range CHECK (occupancy_percentage >= 0 AND occupancy_percentage <= 100)
            )
            """
        )

        print(f"✓ Таблица '{table_name}' создана")
        self.migration_history.append(f"created_table_{table_name}")
        self.ensure_parking_occupancy_cache_table_columns()

    def ensure_parking_occupancy_cache_table_columns(self):
        table_name = "parking_occupancy_cache"

        alter_statements = [
            ("parking_id", "ALTER TABLE parking_occupancy_cache ADD COLUMN parking_id BIGINT UNIQUE REFERENCES parkings(id) ON DELETE CASCADE"),
            ("total_spots", "ALTER TABLE parking_occupancy_cache ADD COLUMN total_spots INTEGER NOT NULL DEFAULT 0"),
            ("free_spots", "ALTER TABLE parking_occupancy_cache ADD COLUMN free_spots INTEGER NOT NULL DEFAULT 0"),
            ("occupied_spots", "ALTER TABLE parking_occupancy_cache ADD COLUMN occupied_spots INTEGER NOT NULL DEFAULT 0"),
            ("unknown_spots", "ALTER TABLE parking_occupancy_cache ADD COLUMN unknown_spots INTEGER NOT NULL DEFAULT 0"),
            ("occupancy_percentage", "ALTER TABLE parking_occupancy_cache ADD COLUMN occupancy_percentage FLOAT NOT NULL DEFAULT 0.0"),
            ("last_calculated", "ALTER TABLE parking_occupancy_cache ADD COLUMN last_calculated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP"),
            ("frame_index", "ALTER TABLE parking_occupancy_cache ADD COLUMN frame_index INTEGER"),
            ("timestamp_sec", "ALTER TABLE parking_occupancy_cache ADD COLUMN timestamp_sec FLOAT"),
            ("params", "ALTER TABLE parking_occupancy_cache ADD COLUMN params JSONB NOT NULL DEFAULT '{}'::jsonb"),
            ("source_type", "ALTER TABLE parking_occupancy_cache ADD COLUMN source_type VARCHAR(20)"),
            ("source_path", "ALTER TABLE parking_occupancy_cache ADD COLUMN source_path VARCHAR(1000)"),
            ("camera_id", "ALTER TABLE parking_occupancy_cache ADD COLUMN camera_id BIGINT REFERENCES cameras(id) ON DELETE SET NULL"),
        ]

        for column_name, sql in alter_statements:
            self.add_column_if_not_exists(table_name, column_name, sql)

        self.create_index_if_not_exists(
            "idx_parking_occupancy_parking_id",
            "CREATE INDEX idx_parking_occupancy_parking_id ON parking_occupancy_cache(parking_id)",
        )
        self.create_index_if_not_exists(
            "idx_parking_occupancy_last_calculated",
            "CREATE INDEX idx_parking_occupancy_last_calculated ON parking_occupancy_cache(last_calculated)",
        )
        self.create_index_if_not_exists(
            "idx_parking_occupancy_camera_id",
            "CREATE INDEX idx_parking_occupancy_camera_id ON parking_occupancy_cache(camera_id)",
        )

        self.cursor.execute(
            """
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
        )

        print("  ✓ Триггер для 'parking_occupancy_cache' создан или обновлён")

    def create_event_logs_table(self):
        table_name = "event_logs"

        if self.table_exists(table_name):
            print(f"  Таблица '{table_name}' уже существует, пропускаем создание")
            self.ensure_event_logs_table_columns()
            return

        self.cursor.execute(
            """
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
        )

        print(f"✓ Таблица '{table_name}' создана")
        self.migration_history.append(f"created_table_{table_name}")
        self.ensure_event_logs_table_columns()

    def ensure_event_logs_table_columns(self):
        table_name = "event_logs"

        alter_statements = [
            ("timestamp", "ALTER TABLE event_logs ADD COLUMN timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()"),
            ("event_type", "ALTER TABLE event_logs ADD COLUMN event_type VARCHAR(64) NOT NULL DEFAULT 'unknown'"),
            ("severity", "ALTER TABLE event_logs ADD COLUMN severity VARCHAR(20) NOT NULL DEFAULT 'info'"),
            ("entity_type", "ALTER TABLE event_logs ADD COLUMN entity_type VARCHAR(20) NOT NULL DEFAULT 'system'"),
            ("entity_id", "ALTER TABLE event_logs ADD COLUMN entity_id BIGINT"),
            ("actor_user_id", "ALTER TABLE event_logs ADD COLUMN actor_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL"),
            ("parking_id", "ALTER TABLE event_logs ADD COLUMN parking_id BIGINT REFERENCES parkings(id) ON DELETE SET NULL"),
            ("description", "ALTER TABLE event_logs ADD COLUMN description TEXT NOT NULL DEFAULT ''"),
            ("details", "ALTER TABLE event_logs ADD COLUMN details JSONB NOT NULL DEFAULT '{}'::jsonb"),
        ]

        for column_name, sql in alter_statements:
            self.add_column_if_not_exists(table_name, column_name, sql)

        self.create_index_if_not_exists("idx_event_logs_timestamp", "CREATE INDEX idx_event_logs_timestamp ON event_logs(timestamp DESC)")
        self.create_index_if_not_exists("idx_event_logs_event_type", "CREATE INDEX idx_event_logs_event_type ON event_logs(event_type)")
        self.create_index_if_not_exists("idx_event_logs_severity", "CREATE INDEX idx_event_logs_severity ON event_logs(severity)")
        self.create_index_if_not_exists("idx_event_logs_entity_type", "CREATE INDEX idx_event_logs_entity_type ON event_logs(entity_type)")
        self.create_index_if_not_exists("idx_event_logs_entity_id", "CREATE INDEX idx_event_logs_entity_id ON event_logs(entity_id)")
        self.create_index_if_not_exists("idx_event_logs_actor_user_id", "CREATE INDEX idx_event_logs_actor_user_id ON event_logs(actor_user_id)")
        self.create_index_if_not_exists("idx_event_logs_parking_id", "CREATE INDEX idx_event_logs_parking_id ON event_logs(parking_id)")

    def get_migration_status(self) -> dict:
        tables = [
            "companies",
            "users",
            "login_attempts",
            "parkings",
            "road_vertices",
            "road_edges",
            "cameras",
            "parking_spots",
            "entrances",
            "parking_occupancy_cache",
            "event_logs",
        ]

        status = {}
        for table in tables:
            status[table] = self.table_exists(table)

        return status

    def run_all_migrations(self, create_admin: bool = False, force: bool = False):
        try:
            self.connect()

            print("\n=== Начало миграции базы данных ===\n")

            if not force:
                status = self.get_migration_status()
                existing_tables = [name for name, exists in status.items() if exists]

                if existing_tables:
                    print(f"Найдены существующие таблицы: {', '.join(existing_tables)}")
                    print("Будут созданы только отсутствующие таблицы и недостающие колонки\n")

            self.create_enums()

            self.create_companies_table()
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
    migration = DatabaseMigration(db_url)
    migration.run_all_migrations(create_admin=create_admin, force=force)


if __name__ == "__main__":
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost:5432/parking_db",
    )

    run_migrations(DATABASE_URL, create_admin=True, force=False)