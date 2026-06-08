"""FastAPI app implementing the Audiobookshelf custom-metadata-provider protocol.

Exposes ``GET /search`` returning ``{"matches": [BookMetadata, ...]}``.

No authentication (see design.md "No authentication"): the service serves only
public DNB data and is intended for trusted/private networks. Any ``Authorization``
header is accepted and ignored. Do not expose this service to the public internet.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from importlib.metadata import PackageNotFoundError, version

from fastapi import Depends, FastAPI, Query

from . import dnb
from .covers import resolve_cover

CoverResolver = Callable[[dict], Awaitable[str | None]]

logger = logging.getLogger("abs_dnb.main")

# Cap results presented to ABS and bound per-cover latency so one slow/missing
# cover never delays or breaks the whole response.
MAX_RESULTS = 15
COVER_TIMEOUT = 8.0

try:
    APP_VERSION = version("abs-dnb")  # single source of truth: pyproject.toml
except PackageNotFoundError:  # running from source without an install
    APP_VERSION = "0+unknown"

app = FastAPI(
    title="abs-dnb",
    version=APP_VERSION,
    description="Audiobookshelf metadata provider backed by the Deutsche Nationalbibliothek.",
)


def get_cover_resolver() -> CoverResolver:
    # Overridable via app.dependency_overrides in tests to avoid live cover lookups.
    return resolve_cover


@app.get("/")
async def root() -> dict:
    return {"status": "ok", "service": "abs-dnb", "version": APP_VERSION}


@app.get("/health")
async def health() -> dict:
    # Pure liveness check: always 200, never touches DNB/Amazon/iTunes. An
    # upstream outage must not mark the container unhealthy (liveness != deps).
    return {"status": "ok"}


@app.get("/search")
async def search(
    query: str = Query(..., description="Title (and optionally author) search terms"),
    author: str | None = Query(None, description="Optional author to refine the query"),
    language: str | None = Query(
        None, description="Optional ISO language filter, e.g. 'ger' (opt-in)"
    ),
    format: str | None = Query(
        None,
        description="Optional medium filter: audiobook | ebook | print "
        "(aliases: Hörbuch, Taschenbuch). Unrecognised values are ignored.",
    ),
    resolve: CoverResolver = Depends(get_cover_resolver),
) -> dict:
    # The protocol requires {"matches": [...]} — never a 500. Any unexpected
    # failure degrades to an empty list.
    try:
        matches = await dnb.search(
            query, author=author, language=language, book_format=format
        )
    except Exception as exc:
        logger.warning("search failed for %r: %s", query, exc)
        return {"matches": []}

    matches = matches[:MAX_RESULTS]

    async def _attach_cover(match: dict) -> None:
        try:
            cover = await asyncio.wait_for(resolve(match), timeout=COVER_TIMEOUT)
        except Exception as exc:  # slow/failing cover -> omit it, keep the match
            logger.info("cover lookup failed for %r: %s", match.get("title"), exc)
            cover = None
        if cover:
            match["cover"] = cover

    # Resolve all covers concurrently; bounded by COVER_TIMEOUT per item.
    await asyncio.gather(*(_attach_cover(m) for m in matches))
    return {"matches": matches}
