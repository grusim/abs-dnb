"""Unit tests for the cover fallback chain (Amazon -> iTunes -> omit)."""

import httpx
import respx

from abs_dnb.covers import (
    AMAZON_URL,
    ITUNES_URL,
    isbn13_to_isbn10,
    resolve_cover,
)

# A real DNB ISBN-13 and its correct ISBN-10 (verified: 9783785737064 -> 3785737068).
ISBN13 = "9783785737064"
ISBN10 = "3785737068"
AMAZON_FOR_ISBN = AMAZON_URL.format(isbn10=ISBN10)


def test_isbn13_to_isbn10_recomputes_check_digit():
    assert isbn13_to_isbn10(ISBN13) == ISBN10
    assert isbn13_to_isbn10("9783785783443") == "3785783442"


def test_isbn13_to_isbn10_rejects_non_isbn13():
    assert isbn13_to_isbn10("3785737068") is None  # already ISBN-10
    assert isbn13_to_isbn10("") is None


@respx.mock
async def test_amazon_returned_when_above_threshold():
    big = b"\xff\xd8\xff" + b"\x00" * 2000  # ~2 KB pseudo-JPEG
    respx.get(AMAZON_FOR_ISBN).mock(return_value=httpx.Response(200, content=big))
    cover = await resolve_cover({"isbn": ISBN13, "title": "Leises Gift"})
    assert cover == AMAZON_FOR_ISBN


@respx.mock
async def test_amazon_placeholder_rejected_then_itunes_used():
    placeholder = b"GIF89a" + b"\x00" * 30  # < 1 KB
    respx.get(AMAZON_FOR_ISBN).mock(
        return_value=httpx.Response(200, content=placeholder)
    )
    respx.get(ITUNES_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {"artworkUrl100": "https://is1.mzstatic.com/image/100x100bb.jpg"}
                ]
            },
        )
    )
    cover = await resolve_cover(
        {"isbn": ISBN13, "title": "Leises Gift", "author": "Iles"}
    )
    assert cover == "https://is1.mzstatic.com/image/600x600bb.jpg"


@respx.mock
async def test_cover_omitted_when_all_sources_miss():
    placeholder = b"GIF89a" + b"\x00" * 10
    respx.get(AMAZON_FOR_ISBN).mock(
        return_value=httpx.Response(200, content=placeholder)
    )
    respx.get(ITUNES_URL).mock(return_value=httpx.Response(200, json={"results": []}))
    cover = await resolve_cover({"isbn": ISBN13, "title": "Nope", "author": "Nobody"})
    assert cover is None


@respx.mock
async def test_no_isbn_goes_straight_to_itunes():
    respx.get(ITUNES_URL).mock(
        return_value=httpx.Response(
            200,
            json={"results": [{"artworkUrl100": "https://x/100x100bb.png"}]},
        )
    )
    cover = await resolve_cover({"title": "Die Säulen der Erde", "author": "Follett"})
    assert cover == "https://x/600x600bb.png"
