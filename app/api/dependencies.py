"""FastAPI dependency injection wiring."""

from functools import lru_cache

from app.core.config import get_settings
from app.llm.factory import get_llm_client
from app.retrieval.retriever import AssessmentRetriever
from app.services.agent import AssessmentAgent
from app.utils.validation import CatalogRegistry
from scraper.catalog_scraper import load_catalog


@lru_cache
def get_catalog_registry() -> CatalogRegistry:
    settings = get_settings()
    records = load_catalog(settings.catalog_path)
    return CatalogRegistry(records, resolve_urls=True)


@lru_cache
def get_retriever() -> AssessmentRetriever:
    return AssessmentRetriever(get_settings())


@lru_cache
def get_agent() -> AssessmentAgent:
    settings = get_settings()
    return AssessmentAgent(
        settings=settings,
        retriever=get_retriever(),
        llm=get_llm_client(),
        registry=get_catalog_registry(),
    )
