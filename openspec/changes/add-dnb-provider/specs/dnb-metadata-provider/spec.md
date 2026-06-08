## ADDED Requirements

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
