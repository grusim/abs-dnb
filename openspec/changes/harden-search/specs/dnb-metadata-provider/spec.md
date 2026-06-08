## ADDED Requirements

### Requirement: Search SHALL never return a server error

The `GET /search` endpoint SHALL always respond with HTTP 200 and a body of the
shape `{"matches": [...]}` (possibly empty). A record that fails to parse SHALL
be skipped rather than failing the request, and MARC subfield access SHALL be
null-safe (no bare key access that can raise).

#### Scenario: Record with a relator field missing its name does not 500

- **WHEN** a returned record has a `700` field with `$4=aut` but no `$a` subfield
- **THEN** `GET /search` SHALL respond HTTP 200 with `{"matches": [...]}`
- **AND** the offending record SHALL be skipped while other records are returned

#### Scenario: Unexpected upstream failure degrades to empty matches

- **WHEN** the DNB query or parsing raises an unexpected error
- **THEN** the response SHALL be HTTP 200 with `{"matches": []}` (never 500)

---

### Requirement: Search SHALL query precise title and person indices

The service SHALL build the CQL query as `TIT=<title> and PER=<author>` when an
author is provided, otherwise `TIT=<title>`. When the combined query returns no
records, the service SHALL retry with `TIT=<title>` alone before returning empty.

#### Scenario: Combined title+person query is used when author is present

- **WHEN** `GET /search?query=Tintenherz&author=Funke` is requested
- **THEN** the CQL sent to DNB SHALL be `TIT=Tintenherz and PER=Funke`

#### Scenario: Falls back to title-only when the combined query is empty

- **WHEN** `TIT=<title> and PER=<author>` returns zero records
- **THEN** the service SHALL retry `TIT=<title>` and return its matches

---

### Requirement: Cover resolution SHALL be concurrent and bounded

The service SHALL resolve cover images for the returned matches concurrently
with a per-item timeout, and SHALL cap the number of presented matches. A cover
that is slow or fails SHALL be omitted without delaying or failing the response.

#### Scenario: A slow cover does not block the whole response

- **WHEN** several matches are returned and one cover lookup is slow
- **THEN** the response SHALL return without waiting on covers sequentially
- **AND** the slow match SHALL be returned without a `cover` field
