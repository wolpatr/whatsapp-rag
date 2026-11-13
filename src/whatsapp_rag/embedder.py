from __future__ import annotations

from typing import Any

import numpy as np

MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
DIM = 384

_model: Any = None


def load_model() -> Any:
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise RuntimeError(
                "sentence-transformers is not installed; run: uv sync --extra embed"
            ) from e
        _model = SentenceTransformer(MODEL, device="cpu")
    return _model


def embed(texts: list[str]) -> np.ndarray:
    model = load_model()
    encoded = model.encode(
        texts,
        batch_size=256,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=len(texts) > 1024,
    )
    return np.asarray(encoded, dtype=np.float32)


def embed_query(query: str) -> np.ndarray:
    return embed([query])[0]
