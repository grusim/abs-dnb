# Harden /search: never-500, precise query, concurrent covers (v0.1.2)

## Why

Driven by the consuming ContainerPlatform sidecar:

- **Bug C (500).** `query=Harry Potter` returned HTTP 500 — a `700` field with
  `$4=aut` but no `$a` hit a bare `field["a"]`, raising `KeyError` that crashed
  the whole search. The ABS protocol requires `{"matches": [...]}`, never a 500.
- **Bug A (recall).** The all-words `WOE=` index missed records the precise
  `TIT=`/`PER=` indices find (e.g. Paglieri 0→5, Ebert 0→25).
- **Bug B (latency).** Covers were resolved sequentially; a many-result query
  with slow cover sources could take many seconds, and one slow cover blocked
  the entire response.

## What Changes

- MARC field access is null-safe (`.get()`); each record is parsed in a guard so
  one malformed record is skipped, not fatal. The `/search` route has a
  top-level guard that always returns `{"matches": [...]}` (possibly `[]`).
- CQL becomes `TIT=<title> and PER=<author>` (or `TIT=<title>`), with a
  `TIT=`-only retry when the combined query returns nothing.
- Covers resolve concurrently (`asyncio.gather`) with a per-item timeout; results
  are capped (~15). A slow/failing cover is omitted, never failing the response.

## Impact

- No protocol or dependency changes. Released as `grusim/abs-dnb:0.1.2`.
- Higher recall; bounded, lower `/search` latency; no 500s.
