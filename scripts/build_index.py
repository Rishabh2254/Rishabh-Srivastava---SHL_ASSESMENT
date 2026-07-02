"""Build FAISS vector index from catalog JSON."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.retrieval.embedder import build_embeddings, save_vectorstore
from scraper.catalog_scraper import load_catalog


def main() -> None:
    setup_logging()
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Build FAISS index from SHL catalog")
    parser.add_argument("--catalog", type=Path, default=settings.catalog_path)
    parser.add_argument("--index", type=Path, default=settings.vectorstore_path)
    parser.add_argument("--meta", type=Path, default=settings.vectorstore_meta_path)
    parser.add_argument("--model", type=str, default=settings.embedding_model)
    args = parser.parse_args()

    records = load_catalog(args.catalog)
    if not records:
        raise SystemExit(f"No catalog records found at {args.catalog}")

    vectors, metadata = build_embeddings(records, args.model)
    save_vectorstore(vectors, metadata, args.index, args.meta)
    print(f"Indexed {len(records)} assessments")


if __name__ == "__main__":
    main()
