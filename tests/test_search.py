"""Integration tests for the /search route, mocking the DNB SRU endpoint.

Cover resolution is overridden to a no-op so these tests exercise only the
search + parse + protocol-shaping path (covers are tested in test_covers.py).
"""

import httpx
import pytest
import respx
from httpx import ASGITransport, AsyncClient

from abs_dnb.dnb import SRU_BASE
from abs_dnb.main import app, get_cover_resolver


async def _noop_cover(_record):
    return None


@pytest.fixture
def client():
    app.dependency_overrides[get_cover_resolver] = lambda: _noop_cover
    transport = ASGITransport(app=app)
    yield AsyncClient(transport=transport, base_url="http://test")
    app.dependency_overrides.clear()


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
        resp = await c.get("/search", params={"query": "Tintenherz", "format": "Taschenbuch"})
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
async def test_language_filter_opt_in(client, saeulen):
    respx.get(SRU_BASE).mock(return_value=httpx.Response(200, content=saeulen))
    async with client as c:
        resp = await c.get(
            "/search", params={"query": "Säulen", "language": "ger"}
        )
    body = resp.json()
    assert resp.status_code == 200
    assert len(body["matches"]) == 3  # all saeulen records are 'ger'
    assert all(m["language"] == "ger" for m in body["matches"])
