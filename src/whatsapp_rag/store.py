from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import sqlite_vec

from whatsapp_rag.types import Episode

_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS episodes ("
    " id INTEGER PRIMARY KEY,"
    " text TEXT NOT NULL,"
    " chat_id TEXT NOT NULL,"
    " chat_name TEXT,"
    " start TEXT NOT NULL,"
    " end TEXT NOT NULL,"
    " senders TEXT NOT NULL)",
    "CREATE INDEX IF NOT EXISTS episodes_chat_start ON episodes(chat_id, start)",
)


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)
    db.execute("PRAGMA journal_mode=WAL")
    return db


def init(db: sqlite3.Connection, dim: int) -> None:
    for stmt in _SCHEMA:
        db.execute(stmt)
    db.execute(
        f"CREATE VIRTUAL TABLE IF NOT EXISTS chunks_vec USING vec0(embedding float[{dim}])"
    )
    db.commit()


def rebuild(path: Path, entries: Iterable[tuple[Episode, np.ndarray]], dim: int) -> int:
    for suffix in ("", "-wal", "-shm"):
        sidecar = Path(str(path) + suffix)
        if sidecar.exists():
            sidecar.unlink()
    db = connect(path)
    try:
        init(db, dim)
        count = 0
        with db:
            for episode, embedding in entries:
                vec = np.ascontiguousarray(embedding, dtype=np.float32)
                cursor = db.execute(
                    "INSERT INTO episodes (text, chat_id, chat_name, start, end, senders)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        episode.render(),
                        episode.chat_id,
                        episode.chat_name,
                        _iso(episode.start),
                        _iso(episode.end),
                        json.dumps(episode.senders),
                    ),
                )
                episode_id = cursor.lastrowid
                assert episode_id is not None
                db.execute(
                    "INSERT INTO chunks_vec (rowid, embedding) VALUES (?, ?)",
                    (episode_id, vec.tobytes()),
                )
                count += 1
        return count
    finally:
        db.close()


def search(
    db: sqlite3.Connection,
    query: np.ndarray,
    n: int = 10,
    chat: str | None = None,
    after: datetime | date | str | None = None,
    before: datetime | date | str | None = None,
    headroom: int = 4,
) -> list[dict[str, Any]]:
    vec = np.ascontiguousarray(query, dtype=np.float32)
    k = min(max(n * headroom, n), 500)
    rows = db.execute(
        "SELECT rowid, distance FROM chunks_vec WHERE embedding MATCH ? AND k = ?"
        " ORDER BY distance",
        (vec.tobytes(), k),
    ).fetchall()
    hits: list[dict[str, Any]] = []
    for episode_id, distance in rows:
        row = db.execute(
            "SELECT text, chat_id, chat_name, start, end, senders FROM episodes WHERE id = ?",
            (episode_id,),
        ).fetchone()
        if row is None:
            continue
        if chat is not None and row["chat_id"] != chat:
            continue
        if after is not None and row["start"] < _after_iso(after):
            continue
        if before is not None and row["end"] >= _before_iso(before):
            continue
        hits.append(
            {
                "text": row["text"],
                "chat_id": row["chat_id"],
                "chat_name": row["chat_name"],
                "start": row["start"],
                "end": row["end"],
                "senders": json.loads(row["senders"]),
                "distance": distance,
            }
        )
        if len(hits) >= n:
            break
    return hits


def _iso(value: datetime | date) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat(timespec="seconds")
    return value.isoformat()


def _after_iso(value: datetime | date | str) -> str:
    if isinstance(value, str):
        return value
    return _iso(value)


def _before_iso(value: datetime | date | str) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return _iso(value)
    return (value + timedelta(days=1)).isoformat()
