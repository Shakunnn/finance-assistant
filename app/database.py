from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import BASE_DIR, settings

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

EXPECTED_TABLES: tuple[str, ...] = (
    "departments",
    "dict_items",
    "users",
    "auth_sessions",
    "categories",
    "files",
    "documents",
    "document_chunks",
    "sync_jobs",
    "reimbursement_standards",
    "approval_flows",
    "special_expense_rules",
    "faq",
    "conversations",
    "messages",
    "qa_logs",
    "browse_history",
)


def _normalize_sqlite_url(database_url: str) -> str:
    if database_url.startswith("sqlite:///"):
        raw_path = database_url.replace("sqlite:///", "", 1)
        if raw_path != ":memory:":
            path_obj = Path(raw_path)
            if not path_obj.is_absolute():
                path_obj = (BASE_DIR / path_obj).resolve()
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{path_obj.as_posix()}"
    return database_url


def build_engine(database_url: str | None = None) -> Engine:
    """构建 SQLAlchemy Engine，并为 SQLite 连接统一启用 WAL、foreign_keys 和 busy_timeout。"""
    resolved_url = _normalize_sqlite_url(database_url or settings.database_url)
    eng = create_engine(
        resolved_url,
        connect_args={
            "check_same_thread": False,
            "timeout": max(settings.sqlite_busy_timeout_ms / 1000.0, 5.0),
        },
        future=True,
    )

    @event.listens_for(eng, "connect")
    def _set_sqlite_pragma(dbapi_connection: Any, _connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute("PRAGMA journal_mode = WAL;")
        cursor.execute(f"PRAGMA busy_timeout = {int(settings.sqlite_busy_timeout_ms)};")
        cursor.close()

    return eng


engine: Engine = build_engine()
SessionLocal = sessionmaker(bind=engine, class_=Session, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖项：提供 SQLAlchemy Session（只使用 Session + text()）。"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _split_sql_statements(sql_script: str) -> list[str]:
    """按分号切分 schema.sql 中的 DDL 语句（忽略纯注释行和空语句）。"""
    cleaned_lines: list[str] = []
    for line in sql_script.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        cleaned_lines.append(line)
    joined = "\n".join(cleaned_lines)
    statements = [stmt.strip() for stmt in joined.split(";") if stmt.strip()]
    return statements


def init_db(target_engine: Engine | None = None) -> dict[str, Any]:
    """
    幂等初始化数据库（17 张业务表及全部索引）。
    只通过 SQLAlchemy Session + text() 执行 schema.sql，不引入 ORM 模型。
    """
    settings.ensure_dirs()
    active_engine = target_engine or engine
    sql_script = SCHEMA_PATH.read_text(encoding="utf-8")
    statements = _split_sql_statements(sql_script)

    local_session_factory = sessionmaker(
        bind=active_engine, class_=Session, autoflush=False, autocommit=False, future=True
    )

    with local_session_factory() as session:
        session.execute(text("PRAGMA foreign_keys = ON"))
        for stmt in statements:
            session.execute(text(stmt))
        session.commit()

        rows = session.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
                "ORDER BY name"
            )
        ).scalars().all()
        fk_violations = session.execute(text("PRAGMA foreign_key_check")).fetchall()
        fk_enabled = session.execute(text("PRAGMA foreign_keys")).scalar()
        journal_mode = session.execute(text("PRAGMA journal_mode")).scalar()

    missing = [t for t in EXPECTED_TABLES if t not in rows]
    if missing:
        raise RuntimeError(f"数据库初始化缺失表: {missing}")
    if fk_violations:
        raise RuntimeError(f"外键完整性检查未通过: {fk_violations}")

    return {
        "table_count": len(rows),
        "tables": list(rows),
        "foreign_keys_enabled": int(fk_enabled or 0),
        "foreign_key_violations": [tuple(r) for r in fk_violations],
        "journal_mode": str(journal_mode),
    }


if __name__ == "__main__":
    result = init_db()
    print(f"init_db completed: {result['table_count']} tables initialized.")
