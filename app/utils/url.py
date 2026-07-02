"""URL helpers and catalog URL validation."""

from urllib.parse import urlparse


SHL_HOSTS = {"www.shl.com", "shl.com"}


def canonicalize_shl_url(url: str) -> str:
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower()
    if host not in SHL_HOSTS:
        return url.strip()
    path = parsed.path.rstrip("/") + "/"
    return f"https://www.shl.com{path}" if not parsed.netloc else f"https://{host}{path}"


def url_slug(url: str) -> str:
    return canonicalize_shl_url(url).rstrip("/").split("/")[-1].lower()


def is_shl_catalog_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc.lower() not in SHL_HOSTS:
        return False
    return "product-catalog/view" in parsed.path or "/products/assessments/" in parsed.path
