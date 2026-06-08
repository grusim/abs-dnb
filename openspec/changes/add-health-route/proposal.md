# Add /health liveness route + best-effort author fallback (v0.1.1)

## Why

- **Liveness probe.** Orchestrators and Docker `HEALTHCHECK` conventionally probe
  `GET /health`. The service only exposed `GET /` (a richer status object). A
  dedicated, dependency-free liveness route lets a container be restarted on
  process death without coupling health to upstream availability.
- **Author hole.** Records with no `100` and no `700 $4=aut` (e.g. the Iles
  audiobook `leises-gift`, whose contributors are all `$4=ctb`) returned no
  `author`. ABS matching is weaker without it. The original design omitted
  author rather than guess; this change reverses that to a best-effort fallback.

## What Changes

- Add `GET /health` returning HTTP 200 `{"status": "ok"}` unconditionally — no
  DNB/Amazon/iTunes calls (liveness, not a dependency check).
- Author extraction gains a final fallback: when there is no `100 $a` and no
  `700 $4=aut`, use the first `700 $a` contributor.
- Single-source the app version from package metadata; bump to `0.1.1`.

## Impact

- New route; existing `/` and `/search` unchanged.
- `author` is now populated on more records. Trade-off: the first-contributor
  heuristic can misattribute when a record lists a narrator/translator first.
- No new dependencies. Released as `grusim/abs-dnb:0.1.1`.
