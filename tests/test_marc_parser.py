"""Unit tests for the MARC21 -> ABS BookMetadata parser.

Expectations are derived from the real DNB records captured in tests/fixtures/.
"""

from abs_dnb.marc import parse_records


def test_leises_gift_single_record_title_and_isbn(leises_gift):
    records = parse_records(leises_gift)
    assert len(records) == 1
    rec = records[0]
    assert rec["title"] == "Leises Gift"
    assert rec["isbn"] == "9783785737064"
    assert rec["language"] == "ger"


def test_leises_gift_author_omitted_when_only_contributors(leises_gift):
    # All 700 entries carry $4=ctb (Mitwirkender); no 100 and no $4=aut.
    # Author cannot be disambiguated, so it is omitted rather than guessed.
    rec = parse_records(leises_gift)[0]
    assert "author" not in rec
    assert "narrator" not in rec


def test_title_strips_marc_nonsort_control_chars(saeulen):
    rec = parse_records(saeulen)[0]
    assert rec["title"] == "Die Säulen der Erde"
    assert "\x98" not in rec["title"]
    assert "\x9c" not in rec["title"]


def test_saeulen_author_and_narrator_from_relator_codes(saeulen):
    rec = parse_records(saeulen)[0]
    assert rec["author"] == "Follett, Ken"  # 100 $a $4=aut
    assert rec["narrator"] == "Kerzel, Joachim"  # 700 $a $4=nrt


def test_saeulen_net_publication_has_no_isbn_but_other_fields(saeulen):
    records = parse_records(saeulen)
    assert len(records) == 3
    rec0 = records[0]
    assert "isbn" not in rec0  # net-pub record carries only 024 URN
    assert rec0["title"] == "Die Säulen der Erde"
    assert rec0["language"] == "ger"
    # genres come from 655 $a
    assert "Hörbuch" in rec0["genres"]


def test_saeulen_prefers_isbn13_when_both_present(saeulen):
    # rec1 carries 020 $a with both 9783785783443 (13) and 3785783442 (10).
    rec1 = parse_records(saeulen)[1]
    assert rec1["isbn"] == "9783785783443"


def test_saeulen_publisher_and_year(saeulen):
    rec1 = parse_records(saeulen)[1]
    assert rec1["publisher"] == "Lübbe Audio"
    assert rec1["publishedYear"] == "2020"  # extracted from "[2020]"


def test_tintenherz_author_isbn_series(tintenherz):
    records = parse_records(tintenherz)
    assert len(records) == 5
    rec0 = records[0]
    assert rec0["author"] == "Funke, Cornelia"
    assert rec0["isbn"] == "9783126741347"
    assert rec0["series"] == [{"series": "Deutsch - leichter lesen"}]


def test_vorleser_all_records_have_title(vorleser):
    records = parse_records(vorleser)
    assert len(records) == 5
    assert all(r["title"] for r in records)


def test_media_type_audiobook_from_spw(leises_gift):
    # 336 $b = spw (gesprochenes Wort), leader/06 = i
    assert parse_records(leises_gift)[0]["mediaType"] == "audiobook"


def test_media_type_audiobook_even_when_online(saeulen):
    # rec0 is spw with 338 $b = cr (downloadable Hörbuch) -> still audiobook
    assert parse_records(saeulen)[0]["mediaType"] == "audiobook"


def test_media_type_print_from_txt_volume(tintenherz):
    # 336 $b = txt, 338 $b = nc (volume) -> print
    assert all(r["mediaType"] == "print" for r in parse_records(tintenherz))


def test_media_type_ebook_from_txt_online(vorleser):
    # 336 $b = txt, 338 $b = cr (online) -> ebook; the one nc (volume) -> print
    types = [r["mediaType"] for r in parse_records(vorleser)]
    assert types == ["ebook", "ebook", "ebook", "ebook", "print"]


def test_empty_response_yields_no_records():
    empty = (
        b'<?xml version="1.0"?>'
        b'<searchRetrieveResponse xmlns="http://www.loc.gov/zing/srw/">'
        b"<version>1.1</version><numberOfRecords>0</numberOfRecords>"
        b"<records></records></searchRetrieveResponse>"
    )
    assert parse_records(empty) == []
