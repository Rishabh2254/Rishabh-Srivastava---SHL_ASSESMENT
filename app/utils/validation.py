"""Response and recommendation validation against catalog."""

from urllib.parse import quote_plus, urlparse

import requests

from app.models.catalog import AssessmentRecord
from app.models.schemas import ChatResponse, RecommendationItem
from app.utils.url import canonicalize_shl_url, url_slug


class CatalogRegistry:
    def __init__(self, records: list[AssessmentRecord], resolve_urls: bool = False) -> None:
        self._by_url: dict[str, AssessmentRecord] = {}
        self._by_slug: dict[str, AssessmentRecord] = {}
        self._by_name: dict[str, AssessmentRecord] = {}
        self._resolve_urls = resolve_urls
        self._resolved_url_cache: dict[str, str] = {}
        for record in records:
            url = canonicalize_shl_url(record.url)
            self._by_url[url] = record
            self._by_slug[url_slug(url)] = record
            self._by_name[record.name.lower()] = record

    @property
    def records(self) -> list[AssessmentRecord]:
        return list(self._by_url.values())

    def get_by_url(self, url: str) -> AssessmentRecord | None:
        return self._by_url.get(canonicalize_shl_url(url))

    def get_by_name(self, name: str) -> AssessmentRecord | None:
        return self._by_name.get(name.lower())

    def get_by_slug(self, slug: str) -> AssessmentRecord | None:
        return self._by_slug.get(slug.lower())

    def validate_recommendations(
        self, items: list[RecommendationItem], max_items: int = 10
    ) -> list[RecommendationItem]:
        validated: list[RecommendationItem] = []
        seen: set[str] = set()
        for item in items[:max_items]:
            record = self.get_by_url(item.url) or self.get_by_name(item.name)
            if record is None:
                continue
            key = record.slug()
            if key in seen:
                continue
            seen.add(key)
            validated.append(
                RecommendationItem(
                    name=record.name,
                    url=self._public_url_for(record),
                    test_type=record.test_type or item.test_type,
                )
            )
        return validated

    def enforce_response(self, response: ChatResponse) -> ChatResponse:
        validated = self.validate_recommendations(response.recommendations)
        if response.recommendations and not validated:
            return ChatResponse(
                reply=(
                    response.reply
                    + " I could not ground the recommendations in the SHL catalog, "
                    "so I am withholding product suggestions until retrieval confidence improves."
                ),
                recommendations=[],
                end_of_conversation=response.end_of_conversation,
            )
        return ChatResponse(
            reply=response.reply,
            recommendations=validated,
            end_of_conversation=response.end_of_conversation,
        )

    def _public_url_for(self, record: AssessmentRecord) -> str:
        canonical = canonicalize_shl_url(record.url)
        if not self._resolve_urls:
            return canonical
        cached = self._resolved_url_cache.get(canonical)
        if cached:
            return cached
        resolved = self._resolve_public_url(canonical, record.name)
        self._resolved_url_cache[canonical] = resolved
        return resolved

    def _resolve_public_url(self, canonical_url: str, assessment_name: str) -> str:
        try:
            response = requests.get(
                canonical_url,
                allow_redirects=True,
                timeout=8,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            final_url = canonicalize_shl_url(response.url)
            if self._is_generic_landing_url(canonical_url, final_url):
                return self._search_url(assessment_name)
            return final_url
        except requests.RequestException:
            return self._search_url(assessment_name)

    @staticmethod
    def _search_url(assessment_name: str) -> str:
        return f"https://www.shl.com/search/?q={quote_plus(assessment_name)}"

    @staticmethod
    def _is_generic_landing_url(original_url: str, final_url: str) -> bool:
        original_path = urlparse(original_url).path.lower()
        final_path = urlparse(final_url).path.lower().rstrip("/")
        if final_path == "":
            return True
        generic_paths = {
            "/products",
            "/products/assessments",
            "/products/assessments/job-focused-assessments",
            "/products/assessments/skills-and-simulations",
            "/products/assessments/skills-and-simulations/technical-skills",
            "/products/assessments/personality-assessment",
            "/products/assessments/behavioral-assessments",
        }
        if final_path in generic_paths:
            return True
        original_slug = original_path.rstrip("/").split("/")[-1]
        return bool(original_slug) and original_slug not in final_path
