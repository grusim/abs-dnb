# Changelog

All notable changes to this project will be documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
Versioning: [Semantic Versioning](https://semver.org/)
## [0.1.0] - 2026-06-08

### Added

- Seed abs-dnb provider (openspec + scaffolding)
- MARC21-xml to BookMetadata parser
- Keyless cover chain (Amazon, iTunes)
- DNB SRU client + search API

### Fixed

- Let uv own python, drop from mise

### Documentation

- README + openspec design/spec
- Auto-generate changelog via git-cliff
- Document pre-commit + mise setup

### Build & CI

- Scaffold project + deps
- Alpine container image
- Publish signed multi-arch image on tags
- Cut GitHub Release on tag publish
- Pin actions to commit SHA (supply chain)
- Add Dependabot (actions, uv, docker)
- Add pre-commit hooks
- Add mise dev tooling + tasks
- Bump runtime to Python 3.14
- Add ruff format task + venv ruff
