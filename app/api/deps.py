from __future__ import annotations

from fastapi import HTTPException

from app.config import Settings, load_settings
from app.db import connect, init_db
from app.repository import Repository


settings = load_settings()
init_db(settings.db_path)
connection = connect(settings.db_path)


def get_settings() -> Settings:
    return settings


def get_repo() -> Repository:
    return Repository(connection)


def not_found(error: KeyError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(error))
