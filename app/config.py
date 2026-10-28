from __future__ import annotations

import os
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=False)

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
YUAN_PATTERN = re.compile(r"^\d+(\.\d{1,2})?$")


def shanghai_now() -> datetime:
    """返回当前 Asia/Shanghai 时区时间对象。"""
    return datetime.now(SHANGHAI_TZ)


def shanghai_now_str() -> str:
    """返回当前 Asia/Shanghai 本地时间字符串，统一格式 YYYY-MM-DD HH:MM:SS。"""
    return shanghai_now().strftime(DATETIME_FORMAT)


def shanghai_today_str() -> str:
    """返回当前 Asia/Shanghai 本地日期字符串，格式 YYYY-MM-DD。"""
    return shanghai_now().strftime(DATE_FORMAT)


def yuan_to_cents(amount_yuan: str | int | float | Decimal) -> int:
    """将人民币元（最多两位小数）转换为库内整数分，禁止浮点误差。"""
    s = str(amount_yuan).strip()
    if not YUAN_PATTERN.match(s):
        raise ValueError(f"非法的金额格式: {amount_yuan}")
    try:
        dec = Decimal(s)
    except InvalidOperation as exc:
        raise ValueError(f"非法的金额数值: {amount_yuan}") from exc
    if dec < 0:
        raise ValueError("金额不能为负数")
    cents = int((dec * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return cents


def cents_to_yuan(amount_cents: int | None) -> str | None:
    """将库内整数分转换为两位小数人民币元字符串。"""
    if amount_cents is None:
        return None
    if not isinstance(amount_cents, int):
        amount_cents = int(amount_cents)
    dec = (Decimal(amount_cents) / Decimal("100")).quantize(Decimal("0.01"))
    return f"{dec:.2f}"


class Settings(BaseModel):
    app_name: str = os.getenv("APP_NAME", "财务报销制度智能咨询助手")
    app_code: str = os.getenv("APP_CODE", "FA")
    app_env: str = os.getenv("APP_ENV", "development")
    app_host: str = os.getenv("APP_HOST", "127.0.0.1")
    app_port: int = int(os.getenv("APP_PORT", "8000"))
    timezone: str = os.getenv("TIMEZONE", "Asia/Shanghai")

    database_url: str = os.getenv(
        "DATABASE_URL", f"sqlite:///{(BASE_DIR / 'data' / 'app.db').as_posix()}"
    )
    sqlite_busy_timeout_ms: int = int(os.getenv("SQLITE_BUSY_TIMEOUT_MS", "5000"))
    upload_dir: Path = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "data" / "uploads")))
    backup_dir: Path = Path(os.getenv("BACKUP_DIR", str(BASE_DIR / "data" / "backups")))

    chroma_host: str = os.getenv("CHROMA_HOST", "127.0.0.1")
    chroma_port: int = int(os.getenv("CHROMA_PORT", "8001"))
    chroma_persist_dir: Path = Path(
        os.getenv("CHROMA_PERSIST_DIR", str(BASE_DIR / "data" / "chroma"))
    )
    chroma_collection: str = os.getenv("CHROMA_COLLECTION", "fa_knowledge_chunks")

    bge_model_name: str = os.getenv("BGE_MODEL_NAME", "BAAI/bge-small-zh-v1.5")
    bge_model_revision: str = os.getenv("BGE_MODEL_REVISION", "BAAI/bge-small-zh-v1.5@384d")
    bge_embedding_dim: int = int(os.getenv("BGE_EMBEDDING_DIM", "384"))

    jwt_secret: str = os.getenv("JWT_SECRET", "dev-placeholder-jwt-secret-change-in-env")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "120"))

    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
    tavily_search_url: str = os.getenv("TAVILY_SEARCH_URL", "https://api.tavily.com/search")

    initial_admin_username: str = os.getenv("INITIAL_ADMIN_USERNAME", "admin")
    initial_admin_password: str = os.getenv("INITIAL_ADMIN_PASSWORD", "admin123")

    def ensure_dirs(self) -> None:
        """确保本地数据目录、上传目录、向量目录和备份目录存在。"""
        if self.database_url.startswith("sqlite:///"):
            raw_db_path = self.database_url.replace("sqlite:///", "", 1)
            db_path = Path(raw_db_path)
            if not db_path.is_absolute():
                db_path = (BASE_DIR / db_path).resolve()
            db_path.parent.mkdir(parents=True, exist_ok=True)
        for directory in (self.upload_dir, self.backup_dir, self.chroma_persist_dir):
            target = directory if directory.is_absolute() else (BASE_DIR / directory).resolve()
            target.mkdir(parents=True, exist_ok=True)


settings = Settings()
