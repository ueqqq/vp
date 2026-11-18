"""Pull a vote count out of a vote site's HTML. Pure functions, no network, easy to test."""

from __future__ import annotations

import re


def parse_count(html: str, patterns: list[str]) -> int | None:
    """Return the first match as an int. Handles thousands separators ('13,456' -> 13456).

    The old scraper used (\\d+), which would read '13,456' as 13.
    """
    for pattern in patterns:
        try:
            match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        except re.error:
            continue
        if match:
            digits = match.group(1).replace(",", "")
            if digits.isdigit():
                return int(digits)
    return None
