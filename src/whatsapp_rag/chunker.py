from __future__ import annotations

from collections.abc import Iterable, Iterator
from datetime import timedelta

from whatsapp_rag.types import Episode, Msg

GAP_MINUTES = 30


def group(messages: Iterable[Msg], gap_minutes: int = GAP_MINUTES) -> Iterator[Episode]:
    gap = timedelta(minutes=gap_minutes)
    current: Episode | None = None
    for m in sorted(messages, key=lambda x: (x.chat_id, x.dt)):
        belongs = (
            current is not None
            and m.chat_id == current.chat_id
            and m.dt - current.msgs[-1].dt <= gap
        )
        if not belongs:
            if current is not None:
                yield current
            current = Episode(chat_id=m.chat_id, chat_name=m.chat_name, msgs=[])
        assert current is not None
        if m.chat_name and not current.chat_name:
            current.chat_name = m.chat_name
        current.msgs.append(m)
    if current is not None:
        yield current
