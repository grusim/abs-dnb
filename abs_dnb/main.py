"""FastAPI app implementing the Audiobookshelf custom-metadata-provider protocol.

Exposes ``GET /search`` returning ``{"matches": [BookMetadata, ...]}``.

No authentication (see design.md "No authentication"): the service serves only
public DNB data and is intended for trusted/private networks. Any ``Authorization``
header is accepted and ignored. Do not expose this service to the public internet.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Depends, FastAPI, Query

from . import dnb
from .covers import resolve_cover

CoverResolver = Callable[[dict], Awaitable[str | None]]

app = FastAPI(
    title="abs-dnb",
    version="0.1.0",
    description="Audiobookshelf metadata provider backed by the Deutsche Nationalbibliothek.",
)


def get_cover_resolver() -> CoverResolver:
    # Overridable via app.dependency_overrides in tests to avoid live cover lookups.
    return resolve_cover


@app.get("/")
async def health() -> dict:
    return {"status": "ok", "service": "abs-dnb", "version": "0.1.0"}


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
    matches = await dnb.search(
        query, author=author, language=language, book_format=format
    )
    for match in matches:
        cover = await resolve(match)
        if cover:
            match["cover"] = cover
    return {"matches": matches}
