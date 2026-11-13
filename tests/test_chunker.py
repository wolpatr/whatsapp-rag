from datetime import UTC, datetime, timedelta

from whatsapp_rag.chunker import group
from whatsapp_rag.types import Msg

_BASE = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)


def _msg(chat: str, minutes: int, sender: str = "me", text: str = "x") -> Msg:
    return Msg(
        chat_id=chat,
        chat_name=None,
        dt=_BASE + timedelta(minutes=minutes),
        sender=sender,
        text=text,
    )


def test_short_burst_single_episode():
    msgs = [_msg("+49170", 0), _msg("+49170", 5, "them"), _msg("+49170", 10)]
    episodes = list(group(msgs))
    assert len(episodes) == 1
    assert len(episodes[0].msgs) == 3


def test_gap_splits():
    msgs = [_msg("a", 0), _msg("a", 31)]
    assert len(list(group(msgs))) == 2


def test_gap_boundary_single():
    msgs = [_msg("a", 0), _msg("a", 30)]
    assert len(list(group(msgs))) == 1


def test_chats_never_merge():
    msgs = [_msg("a", 0), _msg("b", 5), _msg("a", 10)]
    episodes = list(group(msgs))
    assert len(episodes) == 2
    assert {e.chat_id for e in episodes} == {"a", "b"}


def test_render_and_metadata():
    msgs = [_msg("a", 0, "me", "hello"), _msg("a", 2, "them", "hi there")]
    (ep,) = list(group(msgs))
    assert "hello" in ep.render()
    assert "hi there" in ep.render()
    assert ep.senders == ["me", "them"]
    assert ep.start < ep.end


def test_unsorted_input():
    msgs = [_msg("a", 40), _msg("a", 0)]
    assert len(list(group(msgs))) == 2


def test_chat_name_filled_later():
    early = Msg(chat_id="a", chat_name=None, dt=_BASE, sender="me", text="a")
    late = Msg(
        chat_id="a",
        chat_name="Alice",
        dt=_BASE + timedelta(minutes=1),
        sender="them",
        text="b",
    )
    (ep,) = list(group([early, late]))
    assert ep.chat_name == "Alice"
