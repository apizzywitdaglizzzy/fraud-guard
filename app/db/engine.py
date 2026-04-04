from __future__ import annotations

import os
import aiosqlite

_db_path: str = ""


def get_db_path() -> str:
    return _db_path


def set_db_path(path: str):
    global _db_path
    _db_path = path


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(_db_path)
    db.row_factory = aiosqlite.Row
    return db
