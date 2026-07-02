"""Text normalization and lightweight NLP helpers."""

import re

WHITESPACE_RE = re.compile(r"\s+")
NON_ALNUM_RE = re.compile(r"[^a-z0-9\s]+")


def normalize_text(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text.strip().lower())


def tokenize(text: str) -> list[str]:
    cleaned = NON_ALNUM_RE.sub(" ", normalize_text(text))
    return [t for t in cleaned.split() if len(t) > 1]


def truncate(text: str, max_chars: int = 4000) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."
