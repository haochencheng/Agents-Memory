"""agents_memory/web/renderer.py — Markdown → sanitised HTML converter."""

from __future__ import annotations

import re

import markdown as _md

# Extensions that are safe and useful for documentation rendering
_EXTENSIONS = [
    "fenced_code",
    "codehilite",
    "tables",
    "toc",
    "nl2br",
    "sane_lists",
]

_EXTENSION_CONFIGS = {
    "codehilite": {
        "guess_lang": False,
        "noclasses": True,
    }
}

# Tags/attributes allowed after conversion (basic allow-list XSS guard)
_DANGEROUS_PATTERNS = [
    re.compile(r"<script[\s\S]*?</script>", re.IGNORECASE),
    re.compile(r"<iframe[\s\S]*?</iframe>", re.IGNORECASE),
    re.compile(r"on\w+\s*=\s*[\"'][^\"']*[\"']", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
]


def md_to_html(content: str) -> str:
    """Convert *content* (Markdown string) to sanitised HTML.

    Returns an empty string for empty or whitespace-only input.
    Strips dangerous patterns (<script>, <iframe>, inline handlers)
    to prevent stored XSS when content is rendered in a browser.
    """
    if not content or not content.strip():
        return ""
    try:
        html: str = _md.markdown(
            content,
            extensions=_EXTENSIONS,
            extension_configs=_EXTENSION_CONFIGS,
        )
    except Exception:
        # Fallback: wrap raw content in a <pre> if markdown library fails
        html = f"<pre>{content}</pre>"

    for pattern in _DANGEROUS_PATTERNS:
        html = pattern.sub("", html)

    return html
