"""Catalog ingestion pipeline CLI."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.logging import setup_logging
from scraper.catalog_scraper import CatalogScraper, load_catalog, save_catalog


def run(catalog_path: Path, max_pages: int, skip_enrich: bool) -> int:
    setup_logging()
    scraper = CatalogScraper()
    records = scraper.scrape(enrich=not skip_enrich, max_pages=max_pages)
    if not records and catalog_path.exists():
        existing = load_catalog(catalog_path)
        if existing:
            print(f"No new scrape results; keeping existing catalog ({len(existing)} records)")
            return 0
    if not records:
        raise SystemExit(
            "Scrape returned 0 records. SHL may be blocking automated access. "
            "Retry later or run from a different network."
        )
    save_catalog(records, catalog_path)
    print(f"Saved {len(records)} assessments to {catalog_path}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape SHL Individual Test Solutions catalog")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("catalog/data/shl_catalog.json"),
    )
    parser.add_argument("--max-pages", type=int, default=40)
    parser.add_argument("--skip-enrich", action="store_true")
    args = parser.parse_args()
    raise SystemExit(run(args.output, args.max_pages, args.skip_enrich))


if __name__ == "__main__":
    main()
