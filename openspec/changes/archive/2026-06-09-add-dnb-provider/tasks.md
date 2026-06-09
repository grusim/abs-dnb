# Build Runbook: abs-dnb v0.1.0

## 1. Project bootstrap

- [x] Create `pyproject.toml` with `[project]` metadata (name `abs-dnb`,
      version `0.1.0`, Python ≥ 3.12, MIT license) and dependencies:
      `fastapi`, `uvicorn[standard]`, `httpx`, `pymarc`.
- [x] Add `[dependency-groups] dev = ["pytest", "pytest-asyncio", "httpx",
      "respx"]`.
- [x] Run `uv sync` to generate `uv.lock`.
- [x] Confirm `uv run uvicorn abs_dnb.main:app --reload` starts on port 8000.

## 2. Core app: TDD against captured fixtures

All tests run against `tests/fixtures/` (do NOT delete these files):
`leises-gift.xml`, `saeulen.xml`, `tintenherz.xml`, `vorleser.xml`,
`dnb-explain.xml`.

- [x] Write `tests/test_marc_parser.py` — unit tests for the MARC21 parser:
  - Extract title (245 $a + $b) from each fixture.
  - Extract author (100 $a $4=aut), narrator (700 $a $4=nrt).
  - Extract publisher/year (264 $b/$c), ISBN (020 $a, may be absent).
  - Extract series (490 $a, 830 $v), language (041 $a), genres (655 $a).
  - Verify that records without 020 do not crash (net-publication records).
- [x] Implement `abs_dnb/marc.py` until `pytest tests/test_marc_parser.py`
      passes.
- [x] Write `tests/test_search.py` — integration tests mocking DNB SRU:
  - Mock `httpx` responses with fixture XML using `respx`.
  - `GET /search?query=Leises+Gift&author=Iles` → 1 match with correct fields.
  - `GET /search?query=Die+Säulen+der+Erde` → multiple matches, narrator
    populated from $4=nrt where present.
  - Query with no results → empty `matches` array, HTTP 200.
  - DNB SRU timeout → HTTP 503 or empty matches (choose and document).
- [x] Implement `abs_dnb/dnb.py` (SRU client) until tests pass.
- [x] Write `tests/test_covers.py` — unit tests for cover chain:
  - Amazon: byte-size < threshold → rejected; ≥ threshold → URL returned.
  - iTunes: `artworkUrl100` rewrite to higher res.
  - Both miss → `cover` key absent from result dict.
  - Mock HTTP with `respx`; use real fixture bytes for pass/fail cases.
- [x] Implement `abs_dnb/covers.py` until tests pass.
- [x] Wire everything into `abs_dnb/main.py` (FastAPI app, `/search` route,
      optional health `GET /`).
- [x] Evaluate CQL strategy: test `WOE=<words>` vs `TIT=<title> AND VER=<author>`
      against fixtures; document chosen strategy in a comment in `dnb.py`.
- [x] Decide on `language` filter default (opt-in vs always-`ger`); add
      `?language=ger` query param if opt-in chosen.
- [x] `uv run pytest` — all tests green.

## 3. Dockerfile

- [x] Write `Dockerfile` (single-stage, `python:3.12-slim`):
  - Install `uv`, copy `pyproject.toml` + `uv.lock`, run `uv sync --no-dev`.
  - Copy `abs_dnb/` source.
  - `CMD ["uv", "run", "uvicorn", "abs_dnb.main:app", "--host", "0.0.0.0",
    "--port", "8000"]`.
  - Non-root user (`appuser`).
- [x] `docker build -t abs-dnb:local .` — builds cleanly.
- [x] `docker run --rm -p 8000:8000 abs-dnb:local` + manual
      `curl http://localhost:8000/search?query=test` → valid JSON response.

## 4. CI workflow: publish v0.1.0

- [x] Create `.github/workflows/publish.yml`:
  - Trigger: `on: push: tags: ['v*']`
  - Steps: checkout, `docker/setup-qemu-action`, `docker/setup-buildx-action`,
    `docker/login-action` (secrets `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN`),
    `docker/metadata-action` (tags from git tag), `docker/build-push-action`
    with `platforms: linux/amd64,linux/arm64`, `provenance: true`, `sbom: true`.
  - Add cosign keyless signing step after push:
    `cosign sign --yes docker.io/grusim/abs-dnb@<digest>` (GitHub OIDC).
  - Document required repo secrets in README `## CI / Publishing` section.
- [x] Push `v0.1.0` tag — confirm Actions run completes and image appears on
      Docker Hub.

## 5. Verify published image

- [x] `docker pull grusim/abs-dnb:0.1.0` on a clean machine (or CI artifact).
- [x] `docker run --rm -p 8000:8000 grusim/abs-dnb:0.1.0` starts without error.
- [x] `curl "http://localhost:8000/search?query=Leises+Gift+Iles"` → 1 match,
      `title` populated, `narrator` present, `cover` is a valid JPEG URL.
- [x] `cosign verify docker.io/grusim/abs-dnb:0.1.0 --certificate-identity-regexp
      'github.com/grusim/abs-dnb' --certificate-oidc-issuer
      'https://token.actions.githubusercontent.com'` → verification OK.
- [x] `docker sbom grusim/abs-dnb:0.1.0` (or `docker buildx imagetools inspect`)
      — SBOM attestation present.
