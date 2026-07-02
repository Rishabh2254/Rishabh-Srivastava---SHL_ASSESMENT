"""Bootstrap catalog from public SHL assessment dataset when live scrape is blocked."""

import json
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.models.catalog import AssessmentRecord
from app.utils.url import canonicalize_shl_url

SOURCE_URL = (
    "https://raw.githubusercontent.com/prachi911/"
    "Assessment-Recommendation-System/main/shl_assessments.json"
)

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


def is_individual_test(url: str, name: str) -> bool:
    path = urlparse(url).path.lower()
    if "product-catalog/view" not in path:
        return False
    if name.lower().endswith("solution") and "job focused" not in name.lower():
        return False
    return True


def transform_item(item: dict) -> AssessmentRecord:
    test_types = item.get("test_types") or []
    if isinstance(test_types, list):
        test_type = ", ".join(test_types)
    else:
        test_type = str(test_types)
    description = item.get("description") or ""
    name = item["name"]
    blob = f"{name} {description}".lower()
    category = "General"
    if any(k in blob for k in ["personality", "opq", "motivation"]):
        category = "Personality"
    elif any(k in blob for k in ["verify", "cognitive", "ability"]):
        category = "Cognitive"
    elif any(k in blob for k in ["java", "python", "programming", "technical"]):
        category = "Technical Skills"

    skills = []
    for key in ["java", "python", "sql", "leadership", "personality", "cognitive"]:
        if key in blob:
            skills.append(key)

    duration = item.get("duration") or ""
    remote_support = item.get("remote_testing_support") or item.get("remote_support") or ""
    adaptive_support = item.get("adaptive_irt_support") or item.get("adaptive_support") or ""

    return AssessmentRecord(
        name=name,
        url=canonicalize_shl_url(item["url"]),
        description=description,
        test_type=test_type,
        duration=duration,
        remote_support=remote_support,
        adaptive_support=adaptive_support,
        category=category,
        skills=skills,
        keywords=skills,
        source="individual_test",
    )


def bootstrap(output: Path) -> int:
    response = requests.get(SOURCE_URL, timeout=60)
    response.raise_for_status()
    raw = response.json()
    records = [
        transform_item(item)
        for item in raw
        if is_individual_test(item.get("url", ""), item.get("name", ""))
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps([r.model_dump() for r in records], indent=2),
        encoding="utf-8",
    )
    print(f"Bootstrapped {len(records)} individual test records to {output}")
    return len(records)


if __name__ == "__main__":
    bootstrap(Path("catalog/data/shl_catalog.json"))
