# Contributing

Contributions are welcome. This project uses
[OpenSpec](openspec/) for requirements tracking and design decisions.

## OpenSpec and PRs

The project is developed with OpenSpec, but **you are not required to use it**.
PRs without openspec artifacts are welcome — the maintainer can backfill specs.

If you do want to propose a change via OpenSpec, see the existing change under
[`openspec/changes/add-dnb-provider/`](openspec/changes/add-dnb-provider/) as
a worked example.

## Development workflow

1. Fork and clone the repo.
2. `uv sync` to install dependencies.
3. `uv run pre-commit install --install-hooks` to enable the git hooks
   (gitleaks, ruff, hadolint, conventional-commit check). With mise:
   `mise run setup`.
4. Write tests first (fixtures are in `tests/fixtures/` — do not delete them).
5. `uv run pytest` (or `mise run test`) — keep it green.
6. Open a PR with a clear description of what changes and why.

## Commit style

Conventional Commits, terse subject (≤ 50 chars), short body if needed.
This is enforced by a `commit-msg` pre-commit hook and feeds the
git-cliff-generated `CHANGELOG.md`.
