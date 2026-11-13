from __future__ import annotations

from pathlib import Path
from typing import Any

from whatsapp_rag import store
from whatsapp_rag.embedder import embed_query
from whatsapp_rag.paths import VECTORS


def search(
    query: str,
    chat: str | None = None,
    n: int = 10,
    after: str | None = None,
    before: str | None = None,
    db: Path = VECTORS,
) -> list[dict[str, Any]]:
    conn = store.connect(db)
    try:
        return store.search(
            conn,
            embed_query(query),
            n=n,
            chat=_chat_jid(chat) if chat is not None else None,
            after=after,
            before=before,
        )
    finally:
        conn.close()


def _chat_jid(chat: str) -> str:
    if "@" in chat:
        return chat
    return f"{chat}@s.whatsapp.net"
