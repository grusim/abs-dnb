# Tasks: harden /search (v0.1.2)

- [x] Null-safe MARC access (`.get()`); per-record parse guard in `parse_records`.
- [x] Top-level `/search` guard — always `{"matches": [...]}`, never 500.
- [x] CQL `TIT=`/`PER=` with `TIT=`-only fallback (verified WOE 0 → TIT/PER 5/25).
- [x] Covers concurrent (`asyncio.gather`) + per-item timeout + cap (15).
- [x] Tests: Harry Potter → 200; Hebamme/Ebert, Paglieri → ≥1; many-result < 2s
      (concurrency). Fixtures captured. `uv run pytest` green (41).
- [x] Update `design.md` query strategy + resolve the open question.
- [ ] Bump `0.1.2`, regenerate changelog, tag `v0.1.2` → CI publishes.
