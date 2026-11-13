from __future__ import annotations

import json
import shutil
import subprocess

import click

from whatsapp_rag import chunker, store
from whatsapp_rag.paths import CRYPT14, CRYPT15, KEY_FILE, KEY_TXT, MSGSTORE, VECTORS
from whatsapp_rag.types import Msg


@click.group()
def main() -> None:
    """WhatsApp DM vector memory: decrypt, build, search."""


def _wadecrypt() -> str:
    found = shutil.which("wadecrypt")
    if found is None:
        raise click.ClickException("wadecrypt not found; install with: uv sync --extra decrypt")
    return found


@main.command()
def decrypt() -> None:
    """Decrypt var/msgstore.db.crypt15 (or crypt14) into var/msgstore.db."""
    if CRYPT15.exists():
        src = CRYPT15
        if not KEY_TXT.exists():
            raise click.ClickException(f"missing {KEY_TXT} with the 64-digit backup key")
        key = "".join(KEY_TXT.read_text(encoding="utf-8").split())
    elif CRYPT14.exists():
        src = CRYPT14
        if not KEY_FILE.exists():
            raise click.ClickException(
                f"missing {KEY_FILE}; copy the legacy WhatsApp 'key' file there "
                "(see WhatsApp-Key-DB-Extractor, Android <= 13 only)"
            )
        key = str(KEY_FILE)
    else:
        raise click.ClickException(f"no backup file at {CRYPT15} or {CRYPT14}")
    if not key:
        raise click.ClickException("key is empty")
    subprocess.run([_wadecrypt(), key, str(src), str(MSGSTORE)], check=True)
    click.echo(f"decrypted {src} -> {MSGSTORE}")


@main.command()
def build() -> None:
    """Parse msgstore.db, chunk episodes, embed, rebuild vectors.db."""
    from whatsapp_rag import embedder
    from whatsapp_rag.sources import whatsapp

    if not MSGSTORE.exists():
        raise click.ClickException(f"{MSGSTORE} not found; run: uv run wa-rag decrypt")
    msgs: list[Msg] = []
    chats: set[str] = set()
    for m in whatsapp.messages(MSGSTORE):
        msgs.append(m)
        chats.add(m.chat_id)
    episodes = list(chunker.group(msgs))
    click.echo(
        f"{len(msgs)} messages, {len(chats)} chats -> {len(episodes)} episodes; embedding..."
    )
    embeddings = embedder.embed([e.render() for e in episodes])
    count = store.rebuild(VECTORS, zip(episodes, embeddings, strict=True), dim=embedder.DIM)
    click.echo(f"wrote {count} episodes to {VECTORS}")


@main.command()
@click.argument("query")
@click.option("--chat", default=None, help="chat jid or bare phone number")
@click.option("-n", "--limit", default=10, show_default=True)
@click.option("--after", default=None, help="ISO date/datetime, episodes starting on or after")
@click.option("--before", default=None, help="ISO date/datetime, episodes ending before")
@click.option("--json", "as_json", is_flag=True, help="print raw JSON")
def search_command(
    query: str,
    chat: str | None,
    limit: int,
    after: str | None,
    before: str | None,
    as_json: bool,
) -> None:
    """Search the vector store."""
    from whatsapp_rag import search as search_mod

    hits = search_mod.search(query, chat=chat, n=limit, after=after, before=before)
    if as_json:
        click.echo(json.dumps(hits, indent=2, ensure_ascii=False))
        return
    for i, hit in enumerate(hits, 1):
        click.echo(
            f"{i}. [{hit['distance']:.3f}] {hit['chat_id']} "
            f"{hit['start']} .. {hit['end']} ({', '.join(hit['senders'])})"
        )
        snippet = hit["text"][:600]
        click.echo(f"   {snippet.replace(chr(10), chr(10) + '   ')}")
