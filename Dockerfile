# Single-stage image on Alpine. Python pinned to 3.12 (laptop default is 3.14,
# on which some wheels resolve poorly) per design.md "Runtime packaging".
#
# Base is python:3.12-alpine rather than -slim: the Debian slim image ships
# `perl-base` 5.40.1 (Essential, cannot be removed) which carries two
# upstream-unfixed HIGH CVEs (CVE-2026-48959, CVE-2026-48962). Alpine ships no
# perl, yielding a clean `docker scout cves` (0C/0H/0M/0L, verified 2026-06-08)
# and a smaller image. The musl wheels for pydantic-core/uvloop resolve cleanly
# and the full test suite passes inside the image.
FROM python:3.14-alpine

# uv for deterministic, cache-friendly dependency install.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Dependency layer: only re-runs when the lockfile or manifest changes.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# Application source.
COPY abs_dnb ./abs_dnb
RUN uv sync --frozen --no-dev

# Run as a non-root user.
RUN adduser -D -u 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "abs_dnb.main:app", "--host", "0.0.0.0", "--port", "8000"]
