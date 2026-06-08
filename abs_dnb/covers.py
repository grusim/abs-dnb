"""Keyless cover-image resolution chain.

Order (design.md "Cover fallback chain"):
1. Amazon ISBN CDN (primary): ISBN-13 -> ISBN-10, probe the image URL. Amazon
   returns HTTP 200 with a 1x1 placeholder GIF for missing covers, so a real
   cover is distinguished by byte size (>= COVER_MIN_BYTES). Verified live
   2026-06-08: ISBN-10 3785737068 -> 63,665-byte JPEG.
2. iTunes Search API (fallback): keyless; results[].artworkUrl100 upscaled by
   rewriting 100x100bb -> 600x600bb. Verified live 2026-06-08.
3. Omit the cover when both miss -- never return a placeholder/blank URL.

Rejected sources (do not re-investigate): VLB portal (commercially licensed),
DNB portal (Anubis anti-bot wall), DNB SRU MARC (no cover URL), OpenLibrary
(404 on German ISBNs), Google Books by ISBN (429 keyless).
"""

from __future__ import annotations

import logging

import httpx

AMAZON_URL = "https://images-na.ssl-images-amazon.com/images/P/{isbn10}.01._SCLZZZZZZZ_.jpg"
ITUNES_URL = "https://itunes.apple.com/search"
COVER_MIN_BYTES = 1024
DEFAULT_TIMEOUT = 10.0

logger = logging.getLogger("abs_dnb.covers")


def isbn13_to_isbn10(isbn13: str) -> str | None:
    """Convert a 978-prefixed ISBN-13 to its ISBN-10 form, recomputing the
    check digit. Returns None for non-13-digit or non-978 inputs."""
    digits = isbn13.replace("-", "").strip()
    if len(digits) != 13 or not digits.isdigit() or not digits.startswith("978"):
        return None
    core = digits[3:12]  # drop 978 prefix and the ISBN-13 check digit
    total = sum((10 - i) * int(d) for i, d in enumerate(core))
    check = (11 - (total % 11)) % 11
    check_char = "X" if check == 10 else str(check)
    return core + check_char


async def amazon_cover(isbn13: str, client: httpx.AsyncClient) -> str | None:
    isbn10 = isbn13_to_isbn10(isbn13)
    if not isbn10:
        return None
    url = AMAZON_URL.format(isbn10=isbn10)
    try:
        response = await client.get(url)
    except httpx.HTTPError as exc:
        logger.warning("Amazon cover probe failed for %s: %s", isbn10, exc)
        return None
    if response.status_code != 200:
        return None
    if len(response.content) < COVER_MIN_BYTES:
        return None  # 1x1 placeholder GIF
    return url


async def itunes_cover(
    title: str, author: str | None, client: httpx.AsyncClient
) -> str | None:
    term = title if not author else f"{title} {author}"
    params = {"media": "ebook", "country": "DE", "term": term}
    try:
        response = await client.get(ITUNES_URL, params=params)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("iTunes cover lookup failed for %r: %s", term, exc)
        return None
    results = payload.get("results") or []
    if not results:
        return None
    artwork = results[0].get("artworkUrl100")
    if not artwork:
        return None
    return artwork.replace("100x100bb", "600x600bb")


async def resolve_cover(
    record: dict, *, client: httpx.AsyncClient | None = None
) -> str | None:
    """Resolve a cover URL for a BookMetadata dict, or None if unavailable."""
    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, follow_redirects=True)
    try:
        isbn = record.get("isbn")
        if isbn:
            cover = await amazon_cover(isbn, client)
            if cover:
                return cover
        title = record.get("title")
        if title:
            return await itunes_cover(title, record.get("author"), client)
        return None
    finally:
        if owns_client:
            await client.aclose()
