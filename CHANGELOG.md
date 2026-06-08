# Changelog

All notable changes to this project will be documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
Versioning: [Semantic Versioning](https://semver.org/)

## [Unreleased]

## [0.1.0] - planned

### Added

- `GET /search` endpoint conforming to ABS custom-metadata-provider protocol
- DNB SRU MARC21-xml metadata sourcing (title, author, narrator, publisher,
  year, ISBN, series, language, genres)
- Narrator populated from MARC21 relator code `$4 nrt`
- Keyless cover chain: Amazon (ISBN-10) → iTunes Search API fallback
- Placeholder-GIF rejection (byte-size guard)
- Multi-arch Docker image (`linux/amd64`, `linux/arm64`)
- GitHub Actions publish workflow with provenance, SBOM, cosign signing
