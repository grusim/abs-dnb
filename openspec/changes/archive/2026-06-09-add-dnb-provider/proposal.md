## Why

Audiobookshelf ships no built-in German metadata provider. The Deutsche
Nationalbibliothek (DNB) offers a keyless SRU/MARC21 API covering the full
German ISBN space, including audiobooks, and exposes narrator relator codes
(`$4 nrt`) that ABS cannot source from English-language providers.
A lightweight FastAPI sidecar fills this gap without requiring any API key or
third-party account.

## What Changes

A new standalone HTTP service (`abs-dnb`) is introduced. It implements the
ABS custom-metadata-provider protocol (`GET /search?query=&author=`) backed
by the DNB SRU endpoint and a keyless cover-image chain (Amazon → iTunes).
No existing service is modified.

## Capabilities

### New Capabilities

- **DNB metadata provider** — search-by-title/author, returns `BookMetadata`
  array conforming to the ABS custom-provider OpenAPI schema; sources title,
  subtitle, author, narrator, publisher, year, ISBN, series, language, and
  genre tags from MARC21 records.
- **Keyless cover chain** — Amazon (ISBN-10 primary) with placeholder-GIF
  rejection, iTunes Search API fallback; `cover` field omitted when both miss.
- **Published Docker image** — `grusim/abs-dnb`, multi-arch (amd64/arm64),
  provenance + SBOM attestations, cosign keyless signing via GitHub OIDC.

## Impact

- No changes to existing services.
- Operator must expose the container on their ABS host network and configure
  ABS to use the provider URL. No API keys required.
- MIT license — public, no warranty.
