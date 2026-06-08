## Context

Audiobookshelf supports pluggable custom metadata providers via a documented
OpenAPI protocol (`GET /search` → `{matches:[BookMetadata]}`). Existing
community providers target English-language sources. German audiobook/ebook
collections are under-served: ISBNs resolve poorly on Open Library, and
Google Books keyless access is rate-limited (429 observed live, 2026-06-08).

The Deutsche Nationalbibliothek publishes its full catalogue via a free,
keyless SRU 1.1 / CQL / MARC21-xml interface at
`https://services.dnb.de/sru/dnb`. This is the authoritative source for
German-edition ISBNs and includes narrator relator codes absent from most
English-language APIs.

## Goals

- Conform to the ABS custom-provider OpenAPI protocol with no modifications.
- Source all metadata from keyless public APIs (no operator signup required).
- Provide a single-command Docker deployment (`docker run`).
- Publish provenance-attested, cosign-signed images for supply-chain auditability.

### Non-Goals

- No ABS UI modifications.
- No authentication beyond what the ABS protocol optionally provides; the
  service is designed for trusted/private network deployment.
- No cover scraping from VLB or the DNB portal (both blocked: VLB is
  commercially licensed; DNB portal is behind Anubis anti-bot challenge,
  confirmed live 2026-06-08).
- No indexing or local caching layer in v0.1.0.

## Decisions

### DNB as metadata source and CQL query strategy

DNB SRU endpoint: `https://services.dnb.de/sru/dnb`, SRU 1.1, CQL,
`recordSchema=MARC21-xml`, `maximumRecords` ≤ 100. Keyless; no registration.

Verified live (2026-06-08): `WOE=<title author words>` all-words index
returns correct records (probe "Leises Gift Iles" → 1 hit, MARC21-xml
delivered). Precise title (`TIT=`) / creator (`VER=`) index refinement is
deferred to the build agent; the builder should test both strategies against
fixtures (`leises-gift.xml`, `saeulen.xml`, `tintenherz.xml`, `vorleser.xml`)
and pick the one with the best precision/recall trade-off.

### MARC21 → ABS BookMetadata mapping

Derived from real DNB records (fixtures captured 2026-06-08):

| ABS field       | MARC21 source                                    | Notes |
|-----------------|--------------------------------------------------|-------|
| `title`         | 245 $a (+ $b subtitle)                           |       |
| `author`        | 100 $a where $4=`aut`; else first 700 $a $4=`aut`|       |
| `narrator`      | 700 $a where $4=`nrt` (Erzähler)                 | relator code enables this |
| `publisher`     | 264 $b (first occurrence)                        |       |
| `publishedYear` | 264 $c                                           |       |
| `isbn`          | 020 $a                                           | absent on net-pub records (only 024 URN) |
| `series`        | 490 $a (name); 830 $v (sequence when present)    |       |
| `language`      | 041 $a (e.g. `ger`)                              |       |
| `genres`/`tags` | 655 $a (e.g. "Hörbuch", "Historische Romane")    |       |

Translator (700 $4=`trl`) has no ABS field; fold into tags or discard.

### Cover fallback chain (keyless, no rejected sources)

1. **Amazon** (primary): ISBN-13 → ISBN-10 (strip check digit, recompute).
   URL: `https://images-na.ssl-images-amazon.com/images/P/<ISBN10>.01._SCLZZZZZZZ_.jpg`
   Amazon returns HTTP 200 for missing ISBNs with a 1×1 GIF placeholder;
   reject by byte-size threshold (< 1 KB). Verified live: ISBN-10 `3785737068`
   returned a real JPEG, 63,665 bytes (2026-06-08).
2. **iTunes Search API** (fallback): keyless, no account required.
   `https://itunes.apple.com/search?media=ebook&country=DE&term=<title+author>`
   → `results[].artworkUrl100`; rewrite `100x100bb` → `600x600bb` for
   higher resolution. Verified live: "Leises Gift" / Greg Iles returned
   artwork (mzstatic CDN) (2026-06-08).
3. **Omit `cover`** if both sources miss — never return a blank/broken URL.

**Rejected sources (documented to prevent re-investigation):**
- VLB portal covers: VLB-licensed, commercial re-use requires VLB contact.
- DNB portal covers: Anubis anti-bot wall returned challenge HTML, not image
  (confirmed live 2026-06-08).
- DNB SRU MARC record: carries no cover URL field.
- OpenLibrary: 404 on German ISBNs tested (2026-06-08).
- Google Books by ISBN: 429 rate-limited keyless (2026-06-08).

### No authentication

The ABS custom-provider `api_key` scheme is optional per the ABS spec.
`abs-dnb` serves only public data and is designed for trusted/private network
deployment. The service accepts and ignores any `Authorization` header.
The README must prominently warn against public internet exposure.

### Runtime packaging: Python / FastAPI / uv / Docker

- **Python 3.12** + **FastAPI** + **uvicorn** — minimal, matches ABS plugin
  ecosystem conventions and keeps the image small.
- **httpx** for async HTTP (DNB SRU + cover probing).
- **pymarc** for MARC21-xml parsing (battle-tested, well-maintained).
- **uv** for deterministic dependency management and fast Docker layer caching.
- Single-stage Dockerfile; multi-arch (`linux/amd64`, `linux/arm64`) via
  `docker buildx`.

### Docker image + CI provenance / SBOM / cosign

Published as `docker.io/grusim/abs-dnb`. GitHub Actions workflow triggers on
`v*` tags:
- `docker/build-push-action` with `provenance: true`, `sbom: true`.
- cosign keyless signing via GitHub OIDC (no long-lived signing key stored in
  repo secrets).
- Operator must add two repo secrets: `DOCKERHUB_USERNAME` and
  `DOCKERHUB_TOKEN` (read+write scoped PAT).

### MIT license

Public project. Copyright (c) 2026 grusim. No warranty.

## Risks / Trade-offs

- **DNB SRU stability**: DNB is a national library; the SRU endpoint is
  production infrastructure, but has no published SLA. Service interruptions
  would return empty results rather than errors (graceful degradation).
- **Amazon cover URL**: undocumented, unofficial endpoint. May change without
  notice. The byte-size guard prevents silent blank covers but not URL rot.
- **iTunes Search API**: unofficial use for cover art. Rate limits are
  undocumented; a busy ABS instance could trigger throttling.
- **No auth = no abuse mitigation**: acceptable for private networks; document
  clearly.

## Open Questions

- Should precise DNB CQL indexes (`TIT=`, `VER=`) replace `WOE=` for better
  recall? Build agent to test against fixtures and decide.
- Should a `language` query parameter filter results to `ger` by default, or
  leave filtering to ABS? Lean toward opt-in filter; evaluate during build.
- Should translator (700 $4=`trl`) be surfaced as a tag or silently dropped?
  Decide during build; lean toward dropping to avoid noise.
