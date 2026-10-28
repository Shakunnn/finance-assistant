from app.database import (
    EXPECTED_TABLES,
    SCHEMA_PATH,
    SessionLocal,
    build_engine,
    engine,
    get_db,
    init_db,
)

__all__ = [
    "EXPECTED_TABLES",
    "SCHEMA_PATH",
    "SessionLocal",
    "build_engine",
    "engine",
    "get_db",
    "init_db",
]

if __name__ == "__main__":
    info = init_db()
    print(info)
