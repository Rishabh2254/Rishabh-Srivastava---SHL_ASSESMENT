"""Embedding generation for catalog records."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.logging import get_logger
from app.models.catalog import AssessmentRecord

logger = get_logger(__name__)


class Embedder:
    def __init__(self, model_name: str) -> None:
        logger.info("Loading embedding model: %s", model_name)
        self.model = SentenceTransformer(model_name)

    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return np.asarray(vectors, dtype=np.float32)

    def encode_one(self, text: str) -> np.ndarray:
        return self.encode([text])[0]


def build_embeddings(records: list[AssessmentRecord], model_name: str) -> tuple[np.ndarray, list[dict]]:
    embedder = Embedder(model_name)
    texts = [r.embedding_text() for r in records]
    vectors = embedder.encode(texts)
    metadata = [r.model_dump() for r in records]
    return vectors, metadata


def save_vectorstore(
    vectors: np.ndarray,
    metadata: list[dict],
    index_path: Path,
    meta_path: Path,
) -> None:
    import faiss

    index_path.parent.mkdir(parents=True, exist_ok=True)
    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)
    faiss.write_index(index, str(index_path))
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    logger.info("Saved FAISS index (%s vectors) to %s", vectors.shape[0], index_path)
