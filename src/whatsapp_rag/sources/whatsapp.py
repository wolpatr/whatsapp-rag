from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from whatsapp_rag.types import Msg

logger = logging.getLogger(__name__)

_MY_LABEL = "me"
_GROUP_SUFFIX = "@g.us"
_NEWSLETTER_SUFFIX = "@newsletter"
_MY_SELF_SUFFIX = "@s.whatsapp.net"
_LID_SUFFIX = "@lid"


@dataclass(frozen=True)
class _ChatRef:
    phone: str | None
    label: str | None


def _label(sender_id: str) -> str:
    if sender_id.endswith(_MY_SELF_SUFFIX):
        return sender_id[: -len(_MY_SELF_SUFFIX)]
    return sender_id


def _chat_refs(db: Path) -> dict[str, _ChatRef]:
    # Newer msgstore schemas identify DM chats by opaque LIDs, while
    # chat_view.original_jid_row_id still points at the phone-number JID and
    # lid_display_name holds optional user-facing labels.
    with closing(sqlite3.connect(f"file:{db}?mode=ro", uri=True)) as conn:
        chat_view_cols = {row[1] for row in conn.execute("PRAGMA table_info(chat_view)")}
        if "jid_row_id" not in chat_view_cols:
            return {}
        has_original = "original_jid_row_id" in chat_view_cols
        has_names = (
            conn.execute(
                "SELECT 1 FROM sqlite_master WHERE name = 'lid_display_name'"
            ).fetchone()
            is not None
        )
        original = "oj.raw_string" if has_original else "NULL"
        original_join = (
            "LEFT JOIN jid oj ON oj._id = cv.original_jid_row_id" if has_original else ""
        )
        name_columns = "ld.display_name, ld.username" if has_names else "NULL, NULL"
        name_join = (
            "LEFT JOIN lid_display_name ld ON ld.lid_row_id = cv.jid_row_id"
            if has_names
            else ""
        )
        sql = f"""
            SELECT lj.raw_string, {original}, {name_columns}
            FROM chat_view cv
            JOIN jid lj ON lj._id = cv.jid_row_id
            {original_join}
            {name_join}
        """
        refs: dict[str, _ChatRef] = {}
        for raw_lid, phone, display_name, username in conn.execute(sql):
            refs[raw_lid] = _ChatRef(
                phone=phone if phone and phone.endswith(_MY_SELF_SUFFIX) else None,
                label=username or display_name or None,
            )
        return refs


def _configure(db: Path) -> None:
    import my.config

    android_cls = getattr(getattr(my.config, "whatsapp", None), "android", None)
    if android_cls is None:
        whatsapp_ns = getattr(my.config, "whatsapp", None)
        if whatsapp_ns is None:
            whatsapp_ns = type("whatsapp", (), {})
            my.config.whatsapp = whatsapp_ns
        android_cls = type("android", (), {})
        whatsapp_ns.android = android_cls
    android_cls.export_path = str(db)
    android_cls.my_user_id = _MY_LABEL

    import my.whatsapp.android

    my.whatsapp.android.config.export_path = str(db)
    my.whatsapp.android.config.my_user_id = _MY_LABEL


def messages(db: Path) -> Iterator[Msg]:
    _configure(db)
    refs = _chat_refs(db)
    from my.whatsapp.android import Message
    from my.whatsapp.android import messages as wa_messages

    for entity in wa_messages():
        if isinstance(entity, Exception):
            logger.warning("skipped entity: %r", entity)
            continue
        if not isinstance(entity, Message):
            continue
        if entity.chat.id.endswith(_GROUP_SUFFIX):
            continue
        if entity.chat.id.endswith(_NEWSLETTER_SUFFIX):
            continue
        chat_id = entity.chat.id
        chat_name = entity.chat.name
        sender = _label(entity.sender.id)
        if chat_id.endswith(_LID_SUFFIX):
            ref = refs.get(chat_id)
            if ref is not None:
                chat_id = ref.phone or chat_id
                chat_name = chat_name or ref.label
        if sender.endswith(_LID_SUFFIX):
            ref = refs.get(sender)
            if ref is not None and ref.phone is not None:
                sender = _label(ref.phone)
        yield Msg(
            chat_id=chat_id,
            chat_name=chat_name,
            dt=entity.dt,
            sender=sender,
            text=entity.text or "",
        )
