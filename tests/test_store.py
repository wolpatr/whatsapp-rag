from datetime import UTC, datetime

import numpy as np

from whatsapp_rag import store
from whatsapp_rag.types import Episode, Msg


def _episode(chat: str, text: str, minute: int = 0) -> Episode:
    dt = datetime(2024, 1, 1, 12, minute, tzinfo=UTC)
    return Episode(
        chat_id=chat,
        chat_name=chat.upper(),
        msgs=[Msg(chat_id=chat, chat_name=chat.upper(), dt=dt, sender="me", text=text)],
    )


def test_rebuild_and_search(tmp_path):
    ep1 = _episode("a@s.whatsapp.net", "hello world")
    ep2 = _episode("b@s.whatsapp.net", "other topic")
    entries = [
        (ep1, np.array([1.0, 0.0], dtype=np.float32)),
        (ep2, np.array([0.0, 1.0], dtype=np.float32)),
    ]
    path = tmp_path / "vectors.db"
    assert store.rebuild(path, entries, dim=2) == 2
    db = store.connect(path)
    try:
        hits = store.search(db, np.array([1.0, 0.0], dtype=np.float32), n=2)
        assert [h["chat_id"] for h in hits] == ["a@s.whatsapp.net", "b@s.whatsapp.net"]
        assert hits[0]["text"] == ep1.render()
        assert hits[0]["senders"] == ["me"]
        assert hits[0]["distance"] < hits[1]["distance"]
    finally:
        db.close()


def test_chat_filter(tmp_path):
    ep1 = _episode("a", "hello world")
    ep2 = _episode("b", "other topic")
    entries = [
        (ep1, np.array([1.0, 0.0], dtype=np.float32)),
        (ep2, np.array([0.0, 1.0], dtype=np.float32)),
    ]
    path = tmp_path / "vectors.db"
    store.rebuild(path, entries, dim=2)
    db = store.connect(path)
    try:
        hits = store.search(db, np.array([1.0, 0.0], dtype=np.float32), n=2, chat="b")
        assert [h["chat_id"] for h in hits] == ["b"]
    finally:
        db.close()


def test_rebuild_replaces_file(tmp_path):
    path = tmp_path / "vectors.db"
    store.rebuild(path, [(_episode("a", "hello"), np.array([1.0, 0.0], dtype=np.float32))], dim=2)
    store.rebuild(path, [(_episode("a", "again"), np.array([0.0, 1.0], dtype=np.float32))], dim=2)
    db = store.connect(path)
    try:
        rows = db.execute("SELECT COUNT(*) AS c FROM episodes").fetchall()
        assert rows[0]["c"] == 1
    finally:
        db.close()
