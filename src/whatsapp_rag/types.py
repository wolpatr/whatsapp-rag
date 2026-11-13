from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Msg:
    chat_id: str
    chat_name: str | None
    dt: datetime
    sender: str
    text: str


@dataclass
class Episode:
    chat_id: str
    chat_name: str | None
    msgs: list[Msg]

    @property
    def start(self) -> datetime:
        return self.msgs[0].dt

    @property
    def end(self) -> datetime:
        return self.msgs[-1].dt

    @property
    def senders(self) -> list[str]:
        return sorted({m.sender for m in self.msgs})

    def render(self) -> str:
        return "\n".join(f"{m.dt:%Y-%m-%d %H:%M} {m.sender}: {m.text}" for m in self.msgs)
