import sqlite3
from pathlib import Path

from whatsapp_rag.sources import whatsapp


def _make_db(path: Path) -> None:
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE chat_view (_id INTEGER, raw_string_jid TEXT, subject TEXT);
        CREATE TABLE jid (_id INTEGER, raw_string TEXT);
        CREATE TABLE message (
            _id INTEGER, key_id INTEGER, timestamp INTEGER, chat_row_id INTEGER,
            sender_jid_row_id INTEGER, from_me INTEGER, text_data TEXT,
            message_type INTEGER
        );
        CREATE TABLE message_media (message_row_id INTEGER, file_path TEXT, file_size INTEGER);
        INSERT INTO chat_view VALUES (1, '+4917000000000@s.whatsapp.net', 'Alice');
        INSERT INTO chat_view VALUES (2, '99-99-99@g.us', 'Some Group');
        INSERT INTO chat_view VALUES (3, '12345@newsletter', 'Some Channel');
        INSERT INTO jid VALUES (0, '+4917000000000@s.whatsapp.net');
        INSERT INTO message VALUES (1, 1, 1700000000000, 1, 0, 1, 'hello there', 0);
        INSERT INTO message VALUES (2, 2, 1700000100000, 1, 0, 0, 'a reply', 0);
        INSERT INTO message VALUES (3, 3, 1700000200000, 2, 0, 1, 'group noise', 0);
        INSERT INTO message VALUES (4, -1, 1700000300000, 1, 0, 1, 'placeholder', 0);
        INSERT INTO message VALUES (5, 5, 1700000400000, 3, 0, 1, 'channel noise', 0);
        """
    )
    db.commit()
    db.close()


def _make_db_2024(path: Path) -> None:
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE chat_view (
            _id INTEGER, jid_row_id INTEGER, original_jid_row_id INTEGER, subject TEXT
        );
        CREATE TABLE lid_display_name (lid_row_id INTEGER, display_name TEXT, username TEXT);
        CREATE TABLE jid (_id INTEGER, raw_string TEXT);
        CREATE TABLE message (
            _id INTEGER, key_id INTEGER, timestamp INTEGER, chat_row_id INTEGER,
            sender_jid_row_id INTEGER, from_me INTEGER, text_data TEXT,
            message_type INTEGER
        );
        CREATE TABLE message_media (message_row_id INTEGER, file_path TEXT, file_size INTEGER);
        INSERT INTO jid VALUES (10, '17858490835194@lid');
        INSERT INTO jid VALUES (11, '4931234567@s.whatsapp.net');
        INSERT INTO jid VALUES (12, '888999888@lid');
        INSERT INTO chat_view VALUES (1, 10, 11, NULL);
        INSERT INTO chat_view VALUES (2, 12, NULL, NULL);
        INSERT INTO lid_display_name VALUES (10, '', 'some.person');
        INSERT INTO message VALUES (1, 1, 1700000000000, 1, 10, 0, 'hello lid', 0);
        INSERT INTO message VALUES (2, 2, 1700000100000, 1, 0, 1, 'my note', 0);
        INSERT INTO message VALUES (3, 3, 1700000200000, 2, 12, 0, 'unmapped lid', 0);
        """
    )
    db.commit()
    db.close()


def test_lid_chats_resolve_to_phone_and_label(tmp_path):
    db = tmp_path / "msgstore.db"
    _make_db_2024(db)
    msgs = list(whatsapp.messages(db))
    by_text = {m.text: m for m in msgs}
    resolved = by_text["hello lid"]
    assert resolved.chat_id == "4931234567@s.whatsapp.net"
    assert resolved.sender == "4931234567"
    assert resolved.chat_name == "some.person"
    mine = by_text["my note"]
    assert mine.sender == "me"
    assert mine.chat_id == "4931234567@s.whatsapp.net"
    unmapped = by_text["unmapped lid"]
    assert unmapped.chat_id == "888999888@lid"
    assert unmapped.sender == "888999888@lid"
    assert unmapped.chat_name is None


def test_dm_messages_parsed_with_me_label(tmp_path):
    db = tmp_path / "msgstore.db"
    _make_db(db)
    msgs = list(whatsapp.messages(db))
    by_text = {m.text: m for m in msgs}
    assert "group noise" not in by_text
    assert "channel noise" not in by_text
    assert "placeholder" not in by_text
    mine = by_text["hello there"]
    assert mine.sender == "me"
    assert mine.chat_id == "+4917000000000@s.whatsapp.net"
    assert mine.chat_name == "Alice"
    theirs = by_text["a reply"]
    assert theirs.sender == "+4917000000000"
    assert mine.dt.year == 2023
