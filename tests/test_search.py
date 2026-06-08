"""Integration tests for the /search route, mocking the DNB SRU endpoint.

Cover resolution is overridden to a no-op so these tests exercise only the
search + parse + protocol-shaping path (covers are tested in test_covers.py).
"""

import asyncio
import time

import httpx
import pytest
import respx
from httpx import ASGITransport, AsyncClient

from abs_dnb.dnb import SRU_BASE, build_cql
from abs_dnb.main import app, get_cover_resolver


def test_build_cql_title_only():
    assert build_cql("Tintenherz") == "TIT=Tintenherz"


def test_build_cql_title_and_person():
    assert build_cql("Tintenherz", "Funke") == "TIT=Tintenherz and PER=Funke"


async def _noop_cover(_record):
    return None


@pytest.fixture
def client():
    app.dependency_overrides[get_cover_resolver] = lambda: _noop_cover
    transport = ASGITransport(app=app)
    yield AsyncClient(transport=transport, base_url="http://test")
    app.dependency_overrides.clear()


async def test_health_is_pure_liveness(client):
    # No network mock: /health must return 200 without touching any upstream.
    async with client as c:
        resp = await c.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_missing_query_returns_422(client):
    async with client as c:
        resp = await c.get("/search")
    assert resp.status_code == 422


@respx.mock
async def test_leises_gift_returns_one_match(client, leises_gift):
    respx.get(SRU_BASE).mock(return_value=httpx.Response(200, content=leises_gift))
    async with client as c:
        resp = await c.get("/search", params={"query": "Leises Gift", "author": "Iles"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    body = resp.json()
    assert len(body["matches"]) == 1
    assert body["matches"][0]["title"] == "Leises Gift"


@respx.mock
async def test_saeulen_returns_multiple_with_narrator(client, saeulen):
    respx.get(SRU_BASE).mock(return_value=httpx.Response(200, content=saeulen))
    async with client as c:
        resp = await c.get("/search", params={"query": "Die Säulen der Erde"})
    body = resp.json()
    assert resp.status_code == 200
    assert len(body["matches"]) == 3
    assert body["matches"][0]["narrator"] == "Kerzel, Joachim"


@respx.mock
async def test_no_results_returns_empty_matches(client):
    empty = (
        b'<?xml version="1.0"?>'
        b'<searchRetrieveResponse xmlns="http://www.loc.gov/zing/srw/">'
        b"<numberOfRecords>0</numberOfRecords><records></records>"
        b"</searchRetrieveResponse>"
    )
    respx.get(SRU_BASE).mock(return_value=httpx.Response(200, content=empty))
    async with client as c:
        resp = await c.get("/search", params={"query": "zzznoresultsxyz"})
    assert resp.status_code == 200
    assert resp.json() == {"matches": []}


@respx.mock
async def test_dnb_timeout_degrades_to_empty_matches(client):
    respx.get(SRU_BASE).mock(side_effect=httpx.TimeoutException("timeout"))
    async with client as c:
        resp = await c.get("/search", params={"query": "anything"})
    assert resp.status_code == 200
    assert resp.json() == {"matches": []}


@respx.mock
async def test_authorization_header_ignored_not_rejected(client, leises_gift):
    respx.get(SRU_BASE).mock(return_value=httpx.Response(200, content=leises_gift))
    async with client as c:
        resp = await c.get(
            "/search",
            params={"query": "Leises Gift"},
            headers={"Authorization": "Bearer dummy"},
        )
    assert resp.status_code == 200


@respx.mock
async def test_format_filter_audiobook_keeps_all_saeulen(client, saeulen):
    respx.get(SRU_BASE).mock(return_value=httpx.Response(200, content=saeulen))
    async with client as c:
        resp = await c.get("/search", params={"query": "Säulen", "format": "audiobook"})
    body = resp.json()
    assert resp.status_code == 200
    assert len(body["matches"]) == 3
    assert all(m["mediaType"] == "audiobook" for m in body["matches"])


@respx.mock
async def test_format_filter_ebook_excludes_audiobooks(client, saeulen):
    respx.get(SRU_BASE).mock(return_value=httpx.Response(200, content=saeulen))
    async with client as c:
        resp = await c.get("/search", params={"query": "Säulen", "format": "ebook"})
    assert resp.status_code == 200
    assert resp.json()["matches"] == []


@respx.mock
async def test_format_filter_german_alias_taschenbuch(client, tintenherz):
    respx.get(SRU_BASE).mock(return_value=httpx.Response(200, content=tintenherz))
    async with client as c:
        resp = await c.get(
            "/search", params={"query": "Tintenherz", "format": "Taschenbuch"}
        )
    body = resp.json()
    assert resp.status_code == 200
    assert len(body["matches"]) == 5
    assert all(m["mediaType"] == "print" for m in body["matches"])


@respx.mock
async def test_unknown_format_is_ignored(client, tintenherz):
    respx.get(SRU_BASE).mock(return_value=httpx.Response(200, content=tintenherz))
    async with client as c:
        resp = await c.get("/search", params={"query": "Tintenherz", "format": "vinyl"})
    assert resp.status_code == 200
    assert len(resp.json()["matches"]) == 5  # unrecognised -> no filtering


@respx.mock
async def test_author_fallback_to_title_only(client, espresso_luciani):
    # TIT+PER (author present) yields 0 -> retry TIT-only, which finds 5.
    empty = (
        b'<?xml version="1.0"?>'
        b'<searchRetrieveResponse xmlns="http://www.loc.gov/zing/srw/">'
        b"<numberOfRecords>0</numberOfRecords><records></records>"
        b"</searchRetrieveResponse>"
    )

    def responder(request):
        if "PER=" in request.url.params.get("query", ""):
            return httpx.Response(200, content=empty)
        return httpx.Response(200, content=espresso_luciani)

    respx.get(SRU_BASE).mock(side_effect=responder)
    async with client as c:
        resp = await c.get(
            "/search",
            params={
                "query": "Kein Espresso für Commissario Luciani",
                "author": "Mismatch",
            },
        )
    body = resp.json()
    assert resp.status_code == 200
    assert len(body["matches"]) == 5


@respx.mock
async def test_no_author_does_not_retry(client):
    empty = (
        b'<?xml version="1.0"?>'
        b'<searchRetrieveResponse xmlns="http://www.loc.gov/zing/srw/">'
        b"<numberOfRecords>0</numberOfRecords><records></records>"
        b"</searchRetrieveResponse>"
    )
    route = respx.get(SRU_BASE).mock(return_value=httpx.Response(200, content=empty))
    async with client as c:
        resp = await c.get("/search", params={"query": "zzznoresults"})
    assert resp.status_code == 200
    assert resp.json() == {"matches": []}
    assert route.call_count == 1  # no author -> single query, no fallback


@respx.mock
async def test_harry_potter_query_never_500(client, fixture_bytes):
    # A record with 700 $4=aut but no $a must not 500 the search.
    respx.get(SRU_BASE).mock(
        return_value=httpx.Response(
            200, content=fixture_bytes("missing-subfield-a.xml")
        )
    )
    async with client as c:
        resp = await c.get("/search", params={"query": "Harry Potter"})
    assert resp.status_code == 200
    body = resp.json()
    assert "matches" in body
    assert body["matches"][0]["title"] == "Harry Potter Test"


@respx.mock
async def test_covers_resolved_concurrently_under_2s(tintenherz):
    # 5 records, each cover lookup sleeps 0.5s: sequential = 2.5s, concurrent ~0.5s.
    async def slow_cover(_match):
        await asyncio.sleep(0.5)
        return None

    app.dependency_overrides[get_cover_resolver] = lambda: slow_cover
    try:
        respx.get(SRU_BASE).mock(return_value=httpx.Response(200, content=tintenherz))
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            start = time.perf_counter()
            resp = await c.get("/search", params={"query": "Tintenherz"})
            elapsed = time.perf_counter() - start
        assert resp.status_code == 200
        assert len(resp.json()["matches"]) == 5
        assert elapsed < 2.0  # would be ~2.5s if covers ran sequentially
    finally:
        app.dependency_overrides.clear()


@respx.mock
async def test_language_filter_opt_in(client, saeulen):
    respx.get(SRU_BASE).mock(return_value=httpx.Response(200, content=saeulen))
    async with client as c:
        resp = await c.get("/search", params={"query": "Säulen", "language": "ger"})
    body = resp.json()
    assert resp.status_code == 200
    assert len(body["matches"]) == 3  # all saeulen records are 'ger'
    assert all(m["language"] == "ger" for m in body["matches"])
