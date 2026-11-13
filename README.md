# whatsapp-rag

Vector memory over WhatsApp direct messages. All personal data stays local in `var/` (gitignored).

Pipeline: backup file -> decrypted `msgstore.db` -> `personal-api` parser -> episode chunks (30-minute gap rule) -> multilingual MiniLM embeddings -> sqlite-vec store -> `wa-rag search`.

## Setup

    uv sync --all-extras

- `embed`: sentence-transformers (`paraphrase-multilingual-MiniLM-L12-v2`, CPU).
- `decrypt`: wa-crypt-tools (GPL-3.0), invoked as an external CLI only.

## Commands

    uv run wa-rag decrypt
    uv run wa-rag build
    uv run wa-rag search "your query" --chat 4912345678 -n 10 --json

## Files in `var/`

- `msgstore.db.crypt15` or `msgstore.db.crypt14`: backup copied from the phone.
- `key.txt`: 64-digit end-to-end backup key, one line (crypt15).
- `key`: legacy WhatsApp account key file (crypt14 fallback route).
- `msgstore.db`: decrypted database, produced by `decrypt`.
- `vectors.db`: rebuilt vector store, produced by `build`.

## Hermes contract

`whatsapp_rag.search.search(query, chat=None, n=10, after=None, before=None)` returns ranked episode dicts with `text`, `chat_id`, `chat_name`, `start`, `end`, `senders`, `distance`. This signature stays stable for the Hermes integration in a later version.
