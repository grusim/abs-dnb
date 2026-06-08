## ADDED Requirements

### Requirement: Service SHALL expose a dependency-free liveness endpoint

The service SHALL expose `GET /health` that returns HTTP 200 with body
`{"status": "ok"}` unconditionally. This endpoint MUST NOT call DNB, Amazon, or
iTunes, so that an upstream outage never marks the container unhealthy
(liveness, not a dependency check).

#### Scenario: Health endpoint returns 200 without upstream calls

- **WHEN** `GET /health` is requested
- **THEN** the response SHALL be HTTP 200 with body `{"status": "ok"}`
- **AND** no request SHALL be made to DNB, Amazon, or iTunes

#### Scenario: Health endpoint succeeds while upstreams are down

- **WHEN** DNB/Amazon/iTunes are unreachable
- **AND** `GET /health` is requested
- **THEN** the response SHALL still be HTTP 200

---

### Requirement: Author SHALL fall back to the first contributor

The service SHALL populate `BookMetadata.author` from the first `700 $a`
contributor when a MARC record has no `100 $a` and no `700 $a` with `$4=aut`,
as a best-effort value rather than omitting the field.

#### Scenario: Author derived from first contributor on ctb-only records

- **WHEN** a record has no `100` field and every `700` carries `$4=ctb`
- **THEN** `BookMetadata.author` SHALL be set to the first `700 $a` value

#### Scenario: Explicit author still takes precedence

- **WHEN** a record has `100 $a` or a `700 $a` with `$4=aut`
- **THEN** that name SHALL be used as `author` (the fallback is not applied)
