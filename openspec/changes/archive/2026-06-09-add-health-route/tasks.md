# Tasks: /health route + author fallback (v0.1.1)

- [x] Add `GET /health` returning `{"status": "ok"}` (no upstream calls).
- [x] Rename the `/` handler off the `health` name; single-source app version
      from package metadata; bump `pyproject.toml` to `0.1.1`.
- [x] Author fallback: first `700 $a` contributor when no `100`/`700 $4=aut`.
- [x] Tests: `test_health_is_pure_liveness`; update leises-gift author test to
      expect the contributor fallback. `uv run pytest` green (32).
- [x] Update `marc.py` mapping docstring to describe the fallback.
- [x] Regenerate `CHANGELOG.md` for `0.1.1`.
- [x] Tag `v0.1.1` → CI builds+pushes `grusim/abs-dnb:0.1.1` + GitHub Release.
