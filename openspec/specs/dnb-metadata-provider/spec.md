# dnb-metadata-provider Specification

## Purpose
TBD - created by archiving change add-dnb-provider. Update Purpose after archive.
## Requirements
### Requirement: Search endpoint conforms to ABS custom-provider protocol

The service SHALL expose `GET /search` accepting `query` (string, required)
and `author` (string, optional) query parameters and returning HTTP 200 with
a JSON body `{"matches": [...]}` where each element is a `BookMetadata`
object as defined by the ABS custom-metadata-provider OpenAPI schema.

#### Scenario: Well-formed query returns matches array

- **WHEN** `GET /search?query=Leises+Gift&author=Iles` is requested
- **THEN** the response SHALL be HTTP 200 with `Content-Type: application/json`
- **AND** the body SHALL contain `{"matches": [...]}` where each element
  includes at least `title`

#### Scenario: Query with no results returns empty array

- **WHEN** `GET /search?query=zzznoresultsxyz` is requested
- **THEN** the response SHALL be HTTP 200
- **AND** `matches` SHALL be an empty array `[]`

#### Scenario: Missing query parameter returns 422

- **WHEN** `GET /search` is requested without the `query` parameter
- **THEN** the response SHALL be HTTP 422

---

### Requirement: Metadata MUST be sourced from the DNB SRU API

The service MUST query `https://services.dnb.de/sru/dnb` using SRU 1.1 /
CQL with `recordSchema=MARC21-xml` and parse the returned MARC21 XML to
populate `BookMetadata` fields.

#### Scenario: Title and author extracted from MARC21

- **WHEN** the DNB SRU response contains a record with MARC field 245 $a
  and 100 $a ($4=aut)
- **THEN** the corresponding `BookMetadata.title` and `BookMetadata.author`
  SHALL be populated from those fields

#### Scenario: Narrator populated from relator code

- **WHEN** a MARC record contains 700 $a with $4=`nrt`
- **THEN** `BookMetadata.narrator` SHALL be populated with that name

#### Scenario: ISBN absent on net-publication records does not crash

- **WHEN** a MARC record has no 020 field (only a 024 URN)
- **THEN** `BookMetadata.isbn` SHALL be absent (not null, not empty string)
- **AND** all other populated fields SHALL be returned normally

---

### Requirement: Cover image MUST be sourced from keyless fallback chain

The service MUST attempt to resolve a cover URL via Amazon (primary) then
iTunes Search API (fallback) before omitting the `cover` field. The service
MUST NOT return a placeholder/blank image URL.

#### Scenario: Amazon cover returned when byte-size exceeds threshold

- **WHEN** the Amazon image URL for the ISBN-10 returns a response body
  larger than 1 KB
- **THEN** `BookMetadata.cover` SHALL be set to that Amazon URL

#### Scenario: Amazon placeholder GIF rejected

- **WHEN** the Amazon image URL returns a response body smaller than 1 KB
  (1×1 placeholder GIF)
- **THEN** the service SHALL NOT set `cover` to that URL and SHALL try iTunes

#### Scenario: iTunes fallback used when Amazon rejects

- **WHEN** Amazon returns a placeholder and iTunes Search API returns at
  least one result with `artworkUrl100`
- **THEN** `BookMetadata.cover` SHALL be set to the artwork URL with
  `100x100bb` rewritten to a higher resolution variant

#### Scenario: Cover omitted when all sources miss

- **WHEN** Amazon returns a placeholder and iTunes returns zero results
- **THEN** `cover` SHALL be absent from the `BookMetadata` object

---

### Requirement: Media type SHALL be classified and filterable

The service SHALL classify each record's medium from MARC RDA content/carrier
fields (336 $b, 338 $b) and the leader, expose it as `mediaType`
(`audiobook` | `ebook` | `print`), and accept an optional `format` query
parameter that filters results to that medium. The `format` parameter SHALL
accept German aliases (`Hörbuch` → audiobook, `Taschenbuch` → print) and SHALL
ignore unrecognised values (returning unfiltered results).

#### Scenario: Audiobook classified from spoken-word content type

- **WHEN** a record has 336 $b = `spw` (gesprochenes Wort) or leader/06 = `i`
- **THEN** its `mediaType` SHALL be `audiobook`

#### Scenario: Print vs ebook distinguished by carrier type

- **WHEN** a record has 336 $b = `txt` and 338 $b = `cr` (online resource)
- **THEN** its `mediaType` SHALL be `ebook`
- **AND WHEN** 338 $b is `nc` (volume) instead
- **THEN** its `mediaType` SHALL be `print`

#### Scenario: Format parameter filters by medium

- **WHEN** `GET /search?query=Tintenherz&format=taschenbuch` is requested
- **THEN** every returned match SHALL have `mediaType` equal to `print`

#### Scenario: Unrecognised format value is ignored

- **WHEN** `GET /search?query=Tintenherz&format=vinyl` is requested
- **THEN** results SHALL NOT be filtered by medium (HTTP 200)

---

### Requirement: The service SHALL operate without authentication

The service SHALL NOT require an API key, token, or any `Authorization`
header from callers. The service SHALL accept and silently ignore any
`Authorization` header if provided (for ABS compatibility).

#### Scenario: Request without Authorization succeeds

- **WHEN** `GET /search?query=test` is sent with no `Authorization` header
- **THEN** the response SHALL be HTTP 200 (or HTTP 200 empty matches)

#### Scenario: Request with Authorization header not rejected

- **WHEN** `GET /search?query=test` is sent with `Authorization: Bearer dummy`
- **THEN** the response SHALL be HTTP 200 (not 401 or 403)

---

### Requirement: Published image MUST carry provenance and signing attestations

The `grusim/abs-dnb` Docker image published to Docker Hub MUST be built with
`provenance: true` and `sbom: true` attestations and MUST be signed via
cosign keyless signing using GitHub OIDC as the identity provider.

#### Scenario: Provenance attestation present on published image

- **WHEN** `docker buildx imagetools inspect grusim/abs-dnb:<tag>` is run
- **THEN** the output SHALL contain a provenance attestation manifest

#### Scenario: Cosign verification succeeds

- **WHEN** `cosign verify` is run against the published image with the
  GitHub Actions OIDC issuer and the `grusim/abs-dnb` repository identity
- **THEN** verification SHALL succeed with exit code 0

### Requirement: Service SHALL expose a dependency-free liveness endpoint

The service SHALL expose `GET /health` that returns HTTP 200 with body
`{"status": "ok"}` unconditionally. This endpoint MUST NOT call DNB, Amazon, or
iTunes, so that an upstream outage never marks the container unhealthy
(liveness, not a dependency check).

#### Scenario: Health endpoint returns 200 without upstream calls

- **WHEN** `GET /health` is requested
- **THEN** the response SHALL be HTTP 200 with body `{"status": "ok"}`
- **AND** no request SHALL be made to DNB, Amazon, or iTunes

#### Scenario: Health endpoint succeeds while upstreams are down

- **WHEN** DNB/Amazon/iTunes are unreachable
- **AND** `GET /health` is requested
- **THEN** the response SHALL still be HTTP 200

---

### Requirement: Author SHALL fall back to the first contributor

The service SHALL populate `BookMetadata.author` from the first `700 $a`
contributor when a MARC record has no `100 $a` and no `700 $a` with `$4=aut`,
as a best-effort value rather than omitting the field.

#### Scenario: Author derived from first contributor on ctb-only records

- **WHEN** a record has no `100` field and every `700` carries `$4=ctb`
- **THEN** `BookMetadata.author` SHALL be set to the first `700 $a` value

#### Scenario: Explicit author still takes precedence

- **WHEN** a record has `100 $a` or a `700 $a` with `$4=aut`
- **THEN** that name SHALL be used as `author` (the fallback is not applied)

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
