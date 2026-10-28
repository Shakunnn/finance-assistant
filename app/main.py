from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings, shanghai_now_str
from app.database import get_db, init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """应用启动生命周期：幂等初始化 17 张数据库表及本地存储目录。"""
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.0.1",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def attach_request_id(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = req_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = req_id
    return response


def ok_response(data: Any = None, message: str = "成功", status_code: int = 200, request_id: str | None = None) -> JSONResponse:
    """统一成功响应结构：{code:'OK', message:'成功', data:..., request_id:UUID}。"""
    return JSONResponse(
        status_code=status_code,
        content={
            "code": "OK",
            "message": message,
            "data": data,
            "request_id": request_id or str(uuid.uuid4()),
        },
    )


@app.get("/api/health")
def health_check(request: Request, db: Session = Depends(get_db)) -> JSONResponse:
    """系统维护健康探针（不回显密钥或本地敏感路径）。"""
    table_count = db.execute(
        text(
            "SELECT count(*) FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    ).scalar()
    fk_violations = db.execute(text("PRAGMA foreign_key_check")).fetchall()
    return ok_response(
        data={
            "status": "ok" if (table_count == 17 and not fk_violations) else "degraded",
            "table_count": int(table_count or 0),
            "fk_check_empty": len(fk_violations) == 0,
            "timestamp": shanghai_now_str(),
        },
        request_id=getattr(request.state, "request_id", str(uuid.uuid4())),
    )
