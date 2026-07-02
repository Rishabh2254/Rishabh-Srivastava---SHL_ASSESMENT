"""SHL Individual Test Solutions catalog scraper."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.logging import get_logger
from app.models.catalog import AssessmentRecord
from app.utils.url import canonicalize_shl_url

logger = get_logger(__name__)

BASE_URL = "https://www.shl.com/solutions/products/product-catalog/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

TEST_TYPE_MAP = {
    "A": "Ability",
    "B": "Behavioral",
    "C": "Cognitive",
    "D": "Development",
    "E": "Assessment",
    "K": "Knowledge & Skills",
    "P": "Personality & Behavior",
    "S": "Situational",
}

CATEGORY_KEYWORDS = {
    "java": ["java", "j2ee", "spring"],
    "python": ["python"],
    "personality": ["opq", "personality", "mq", "motivation"],
    "cognitive": ["verify", "cognitive", "inductive", "numerical", "deductive"],
    "leadership": ["leadership", "manager", "executive"],
    "language": ["language", "english", "french", "german", "spanish"],
}


class CatalogScraper:
    def __init__(self, request_delay: float = 0.8) -> None:
        self.request_delay = request_delay
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def _get(self, url: str) -> requests.Response:
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        return response

    def scrape_listing_pages(self, max_pages: int = 40) -> list[dict]:
        items: list[dict] = []
        empty_streak = 0
        for page in range(max_pages):
            offset = page * 12
            url = f"{BASE_URL}?start={offset}&type=1"
            logger.info("Scraping catalog page offset=%s", offset)
            response = self._get(url)
            soup = BeautifulSoup(response.text, "html.parser")
            table = soup.find("table")
            if not table:
                empty_streak += 1
                if empty_streak >= 2:
                    break
                time.sleep(self.request_delay)
                continue
            page_items = self._parse_table(table)
            if not page_items:
                empty_streak += 1
                if empty_streak >= 2:
                    break
            else:
                empty_streak = 0
                items.extend(page_items)
            time.sleep(self.request_delay)
        return items

    def _parse_table(self, table) -> list[dict]:
        rows = table.find_all("tr")[1:]
        parsed: list[dict] = []
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 4:
                continue
            link = cols[0].find("a", href=True)
            if not link:
                continue
            href = link["href"]
            url = href if href.startswith("http") else urljoin("https://www.shl.com", href)
            remote = "Yes" if cols[1].find("span", class_="catalogue__circle -yes") else "No"
            adaptive = "Yes" if cols[2].find("span", class_="catalogue__circle -yes") else "No"
            keys = cols[3].find_all("span", class_="product-catalogue__key")
            codes = [k.get_text(strip=True) for k in keys]
            test_types = [TEST_TYPE_MAP.get(c, c) for c in codes]
            parsed.append(
                {
                    "name": link.get_text(strip=True),
                    "url": canonicalize_shl_url(url),
                    "remote_support": remote,
                    "adaptive_support": adaptive,
                    "test_type_codes": codes,
                    "test_type": ", ".join(test_types) if test_types else "",
                }
            )
        return parsed

    def enrich_record(self, base: dict) -> AssessmentRecord:
        url = base["url"]
        try:
            response = self._get(url)
            soup = BeautifulSoup(response.text, "html.parser")
        except Exception as exc:
            logger.warning("Detail fetch failed for %s: %s", url, exc)
            return AssessmentRecord(**base)

        description = self._extract_description(soup)
        duration = self._extract_duration(soup, description)
        languages = self._extract_list_field(soup, "language")
        job_levels = self._extract_list_field(soup, "job level")
        skills, competencies, keywords = self._derive_tags(base["name"], description)
        category = self._infer_category(base["name"], description, base.get("test_type", ""))

        return AssessmentRecord(
            name=base["name"],
            url=canonicalize_shl_url(url),
            description=description,
            test_type=base.get("test_type", ""),
            test_type_codes=base.get("test_type_codes", []),
            duration=duration,
            remote_support=base.get("remote_support", ""),
            adaptive_support=base.get("adaptive_support", ""),
            languages=languages,
            job_levels=job_levels,
            category=category,
            skills=skills,
            competencies=competencies,
            keywords=keywords,
            source="individual_test",
        )

    def _extract_description(self, soup: BeautifulSoup) -> str:
        selectors = [
            ".product-detail__description",
            ".product-detail__section",
            "article p",
            ".ss-rte p",
        ]
        chunks: list[str] = []
        for selector in selectors:
            for node in soup.select(selector):
                text = node.get_text(" ", strip=True)
                if len(text) > 40 and text not in chunks:
                    chunks.append(text)
        return " ".join(chunks[:3])

    def _extract_duration(self, soup: BeautifulSoup, description: str) -> str:
        for section in soup.select(".product-detail__section, .ss-rte"):
            text = section.get_text(" ", strip=True).lower()
            match = re.search(r"(\d+)\s*(?:min|minute)", text)
            if match:
                return f"{match.group(1)} minutes"
        match = re.search(r"(\d+)\s*(?:min|minute)", description.lower())
        if match:
            return f"{match.group(1)} minutes"
        return ""

    def _extract_list_field(self, soup: BeautifulSoup, label: str) -> list[str]:
        values: list[str] = []
        for section in soup.select(".product-detail__section, li, p"):
            text = section.get_text(" ", strip=True)
            if label in text.lower() and ":" in text:
                _, rhs = text.split(":", 1)
                values.extend([v.strip() for v in re.split(r"[,;]", rhs) if v.strip()])
        return values[:10]

    def _derive_tags(self, name: str, description: str) -> tuple[list[str], list[str], list[str]]:
        blob = f"{name} {description}".lower()
        skills: list[str] = []
        keywords: list[str] = []
        for key, terms in CATEGORY_KEYWORDS.items():
            if any(t in blob for t in terms):
                skills.append(key)
                keywords.extend(terms)
        competencies = []
        for term in ["problem solving", "communication", "teamwork", "leadership", "analytical"]:
            if term in blob:
                competencies.append(term)
        return skills, competencies, sorted(set(keywords))

    def _infer_category(self, name: str, description: str, test_type: str) -> str:
        blob = f"{name} {description} {test_type}".lower()
        if any(k in blob for k in ["opq", "personality", "motivation"]):
            return "Personality"
        if any(k in blob for k in ["verify", "cognitive", "ability", "numerical", "inductive"]):
            return "Cognitive"
        if any(k in blob for k in ["java", "python", "sql", "programming", "technical", "it "]):
            return "Technical Skills"
        if "situational" in blob or "sjt" in blob:
            return "Behavioral"
        if "language" in blob:
            return "Language"
        return "General"

    def scrape(self, enrich: bool = True, max_pages: int = 40) -> list[AssessmentRecord]:
        listing = self.scrape_listing_pages(max_pages=max_pages)
        logger.info("Listing scrape found %s items", len(listing))
        records: list[AssessmentRecord] = []
        for idx, item in enumerate(listing, start=1):
            if enrich:
                record = self.enrich_record(item)
                time.sleep(self.request_delay)
            else:
                record = AssessmentRecord(**item)
            records.append(record)
            if idx % 25 == 0:
                logger.info("Enriched %s/%s records", idx, len(listing))
        return records


def save_catalog(records: list[AssessmentRecord], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [r.model_dump() for r in records]
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.info("Saved %s catalog records to %s", len(records), output_path)


def load_catalog(path: Path) -> list[AssessmentRecord]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [AssessmentRecord.model_validate(item) for item in data]
