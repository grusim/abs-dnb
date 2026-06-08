"""MARC21-xml -> ABS BookMetadata mapping.

Field mapping derived from real DNB SRU records (fixtures captured 2026-06-08):

| ABS field     | MARC source                                              |
| ------------- | -------------------------------------------------------- |
| title         | 245 $a (+ $b subtitle)                                   |
| author        | 100 $a; else first 700 $a with $4=aut; else omitted      |
| narrator      | first 700 $a with $4=nrt                                 |
| publisher     | first 264 carrying $b -> $b                              |
| publishedYear | first 264 $c (4-digit year extracted)                    |
| isbn          | 020 $a (prefer 13-digit; may be absent on net-pub recs)  |
| series        | 490 $a (name); 830 $v (sequence, when present)           |
| language      | 041 $a                                                   |
| genres        | 655 $a (deduplicated)                                    |

Notes from fixtures:
- pymarc.parse_xml_to_array yields ``None`` for the SRW wrapper elements; drop them.
- Titles carry MARC non-sort control chars (U+0098 NSB / U+009C NSE) that must be
  stripped (e.g. "\\x98Die\\x9c Saeulen der Erde" -> "Die Saeulen der Erde").
- author is omitted (not guessed) when there is no 100 and no 700 $4=aut: such
  records (e.g. ``leises-gift``) carry only $4=ctb contributors that cannot be
  disambiguated into author/narrator/translator.
"""

from __future__ import annotations

import io
import re
import unicodedata

from pymarc import marcxml

# C1 control range; covers MARC non-sort markers \x98 (NSB) and \x9c (NSE).
_C1 = re.compile(r"[\x80-\x9f]")
_YEAR = re.compile(r"\d{4}")


def _clean(value: str | None) -> str:
    if not value:
        return ""
    # DNB delivers decomposed (NFD) Unicode; normalise to NFC so "ä" -> "ä".
    normalised = unicodedata.normalize("NFC", value)
    return _C1.sub("", normalised).strip()


def _first_subfield(record, tag: str, code: str) -> str:
    field = record.get(tag)
    if field is None:
        return ""
    return _clean(field.get(code))


def _name_with_relator(record, relator: str) -> str:
    for field in record.get_fields("700"):
        if relator in field.get_subfields("4"):
            return _clean(field["a"])
    return ""


def _author(record) -> str:
    main = _first_subfield(record, "100", "a")
    if main:
        return main
    return _name_with_relator(record, "aut")


def _publisher(record) -> str:
    for field in record.get_fields("264"):
        pub = field.get_subfields("b")
        if pub:
            return _clean(pub[0])
    return ""


def _published_year(record) -> str:
    for field in record.get_fields("264"):
        raw = field.get_subfields("c")
        if raw:
            match = _YEAR.search(raw[0])
            if match:
                return match.group(0)
    return ""


def _isbn(record) -> str:
    candidates: list[str] = []
    for field in record.get_fields("020"):
        for value in field.get_subfields("a"):
            cleaned = value.strip()
            if cleaned:
                candidates.append(cleaned)
    if not candidates:
        return ""
    for value in candidates:
        if len(value.replace("-", "")) == 13:
            return value
    return candidates[0]


def _series(record) -> list[dict]:
    name = _first_subfield(record, "490", "a")
    if not name:
        return []
    sequence = _first_subfield(record, "830", "v")
    entry: dict[str, str] = {"series": name}
    if sequence:
        entry["sequence"] = sequence
    return [entry]


def _genres(record) -> list[str]:
    seen: list[str] = []
    for field in record.get_fields("655"):
        for value in field.get_subfields("a"):
            cleaned = _clean(value)
            if cleaned and cleaned not in seen:
                seen.append(cleaned)
    return seen


def _media_type(record) -> str | None:
    """Classify the medium from RDA content/carrier types and the leader.

    Signal (100% consistent across the captured fixtures):
    - 336 $b ``spw`` (gesprochenes Wort) or leader/06 ``i`` -> ``audiobook``
    - 336 $b ``txt`` (Text) or leader/06 ``a``:
        - 338 $b ``cr`` (online resource)  -> ``ebook``
        - otherwise (``nc`` volume, etc.)  -> ``print`` (Taschenbuch/Hardcover)
    """
    content = {
        v.strip()
        for field in record.get_fields("336")
        for v in field.get_subfields("b")
    }
    carrier = {
        v.strip()
        for field in record.get_fields("338")
        for v in field.get_subfields("b")
    }
    leader = str(record.leader or "")
    leader6 = leader[6] if len(leader) > 6 else ""

    if "spw" in content or leader6 == "i":
        return "audiobook"
    if "txt" in content or leader6 == "a":
        return "ebook" if "cr" in carrier else "print"
    return None


def _map_record(record) -> dict | None:
    field245 = record.get("245")
    if field245 is None:
        return None
    title = _clean(field245.get("a"))
    if not title:
        return None

    metadata: dict = {"title": title}

    subtitle = _clean(field245.get("b"))
    if subtitle:
        metadata["subtitle"] = subtitle

    author = _author(record)
    if author:
        metadata["author"] = author

    narrator = _name_with_relator(record, "nrt")
    if narrator:
        metadata["narrator"] = narrator

    publisher = _publisher(record)
    if publisher:
        metadata["publisher"] = publisher

    year = _published_year(record)
    if year:
        metadata["publishedYear"] = year

    isbn = _isbn(record)
    if isbn:
        metadata["isbn"] = isbn

    language = _first_subfield(record, "041", "a")
    if language:
        metadata["language"] = language

    series = _series(record)
    if series:
        metadata["series"] = series

    genres = _genres(record)
    if genres:
        metadata["genres"] = genres

    media_type = _media_type(record)
    if media_type:
        metadata["mediaType"] = media_type

    return metadata


def parse_records(xml: bytes | str) -> list[dict]:
    """Parse a DNB SRU MARC21-xml response into ABS BookMetadata dicts.

    Records without a usable 245 $a title are dropped, as are the ``None``
    entries pymarc emits for the surrounding SRW wrapper elements.
    """
    if isinstance(xml, str):
        xml = xml.encode("utf-8")
    records = marcxml.parse_xml_to_array(io.BytesIO(xml))
    out: list[dict] = []
    for record in records:
        if record is None:
            continue
        mapped = _map_record(record)
        if mapped is not None:
            out.append(mapped)
    return out
