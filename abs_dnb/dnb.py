"""Deutsche Nationalbibliothek SRU client.

Endpoint: https://services.dnb.de/sru/dnb (SRU 1.1, CQL, MARC21-xml, keyless).

CQL strategy: the precise indices ``TIT=<title>`` (title) and ``PER=<person>``
(author). Verified live 2026-06-09 that these beat the all-words ``WOE=`` index
on both recall and the failure case: "Kein Espresso für Commissario Luciani" /
Paglieri returned 0 under ``WOE`` but 5 under ``TIT=… and PER=…`` (and existing
probes returned more, e.g. Leises Gift / Iles 1 -> 10). When an author is given
and the combined query yields nothing (the author may be a name variant or
absent from the record), the search retries with ``TIT=`` alone before giving up.

Language filter: opt-in via the ``language`` argument, applied client-side on
the parsed MARC 041 $a value rather than guessing a DNB CQL language index.

Graceful degradation: any network error, timeout, or non-200 response returns an
empty list (the route surfaces HTTP 200 with ``{"matches": []}``). DNB publishes
no SLA, so a transient outage must not fault the ABS provider protocol.
"""

from __future__ import annotations

import logging

import httpx

from .marc import parse_records

SRU_BASE = "https://services.dnb.de/sru/dnb"
DEFAULT_MAX_RECORDS = 20
DEFAULT_TIMEOUT = 10.0

logger = logging.getLogger("abs_dnb.dnb")


# User-facing format aliases -> canonical mediaType produced by marc._media_type.
_FORMAT_ALIASES = {
    "audiobook": "audiobook",
    "hörbuch": "audiobook",
    "hoerbuch": "audiobook",
    "horbuch": "audiobook",
    "ebook": "ebook",
    "e-book": "ebook",
    "print": "print",
    "taschenbuch": "print",
    "buch": "print",
    "book": "print",
    "paperback": "print",
    "hardcover": "print",
}


def normalize_format(value: str | None) -> str | None:
    """Map a user-supplied ``format`` value to a canonical mediaType, or None."""
    if not value:
        return None
    return _FORMAT_ALIASES.get(value.strip().lower())


def build_cql(query: str, author: str | None = None) -> str:
    title = query.strip()
    if author and author.strip():
        return f"TIT={title} and PER={author.strip()}"
    return f"TIT={title}"


async def _fetch(cql: str, max_records: int, client: httpx.AsyncClient) -> list[dict]:
    params = {
        "version": "1.1",
        "operation": "searchRetrieve",
        "query": cql,  # httpx URL-encodes the value (= -> %3D, spaces -> %20)
        "recordSchema": "MARC21-xml",
        "maximumRecords": str(max_records),
    }
    response = await client.get(SRU_BASE, params=params)
    response.raise_for_status()
    return parse_records(response.content)


async def search(
    query: str,
    author: str | None = None,
    language: str | None = None,
    book_format: str | None = None,
    max_records: int = DEFAULT_MAX_RECORDS,
    *,
    client: httpx.AsyncClient | None = None,
) -> list[dict]:
    """Query DNB SRU and return parsed ABS BookMetadata dicts (no cover).

    ``book_format`` (e.g. "audiobook", "ebook", "print" or a German alias such as
    "Hörbuch"/"Taschenbuch") filters results client-side on the parsed mediaType.
    An unrecognised format value is ignored (no filtering applied).
    """
    has_author = bool(author and author.strip())
    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT)
    try:
        records = await _fetch(build_cql(query, author), max_records, client)
        if not records and has_author:
            # TIT+PER too strict (author variant/missing) -> retry title alone.
            records = await _fetch(build_cql(query), max_records, client)
    except httpx.HTTPError as exc:
        logger.warning("DNB SRU request failed: %s", exc)
        return []
    finally:
        if owns_client:
            await client.aclose()

    if language:
        wanted = language.strip().lower()
        records = [r for r in records if r.get("language", "").lower() == wanted]

    wanted_format = normalize_format(book_format)
    if wanted_format:
        records = [r for r in records if r.get("mediaType") == wanted_format]
    return records
