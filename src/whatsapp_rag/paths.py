from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VAR = ROOT / "var"
KEY_TXT = VAR / "key.txt"
KEY_FILE = VAR / "key"
MSGSTORE = VAR / "msgstore.db"
VECTORS = VAR / "vectors.db"
CRYPT15 = VAR / "msgstore.db.crypt15"
CRYPT14 = VAR / "msgstore.db.crypt14"


def backup_file() -> Path:
    for candidate in (CRYPT15, CRYPT14):
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"no backup file at {CRYPT15} or {CRYPT14}")
