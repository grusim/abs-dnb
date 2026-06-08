# abs-dnb

An [Audiobookshelf](https://www.audiobookshelf.org/) custom metadata provider
for German-edition books. Sources bibliographic data from the
[Deutsche Nationalbibliothek (DNB)](https://www.dnb.de/) SRU API (keyless,
MARC21-xml) and cover images from a keyless Amazon → iTunes fallback chain.

Fills the gap left by English-language providers: DNB covers the full German
ISBN space and exposes narrator relator codes that ABS cannot source elsewhere.

## Quick start

```bash
docker run -d --name abs-dnb -p 8000:8000 grusim/abs-dnb:0.1.0
```

Check it's up:

```bash
curl "http://localhost:8000/search?query=Leises+Gift&author=Iles"
```

## ABS configuration

In Audiobookshelf: **Settings → Item Metadata Utils → Custom Metadata Providers**

| Field         | Value                       |
|---------------|-----------------------------|
| Name          | DNB (German)                |
| URL           | `http://<host>:8000`        |
| Authorization | *(leave blank)*             |

## Disclaimers

**No authentication.** `abs-dnb` requires no API key and performs no access
control. Run it on a trusted private network only. Do not expose port 8000
to the public internet.

**Alpha / early release.** Version 0.1.0 is functional but not battle-tested.
Expect rough edges; file issues on GitHub.

**No warranty.** Distributed under the MIT License — see [LICENSE](LICENSE).

**Third-party cover sources.** Cover images are fetched from public Amazon and
iTunes endpoints. These are unofficial, undocumented interfaces that may change
without notice. No cover is returned rather than a broken URL.

## Design and specifications

Architecture decisions and requirements live under [`openspec/`](openspec/).
See [`openspec/changes/add-dnb-provider/design.md`](openspec/changes/add-dnb-provider/design.md)
for the full rationale including the MARC21 field mapping and the rejected
cover sources.

## CI / Publishing

Images are published to `docker.io/grusim/abs-dnb` on `v*` tag pushes via
GitHub Actions. The workflow requires **one** repository secret:

- `DOCKERHUB_TOKEN` — a Docker Hub personal access token with Read & Write
  scope (Docker Hub → Account settings → Personal access tokens → Generate).

The Docker Hub username is the public `grusim` namespace, set as a literal in
the workflow, so it is not a secret. Add the token under the GitHub repo:
Settings → Secrets and variables → Actions → New repository secret.

Images are signed with [cosign](https://github.com/sigstore/cosign) keyless
signing (GitHub OIDC). Verify with:

```bash
cosign verify docker.io/grusim/abs-dnb:0.1.0 \
  --certificate-identity-regexp 'github.com/grusim/abs-dnb' \
  --certificate-oidc-issuer 'https://token.actions.githubusercontent.com'
```

## License

MIT — see [LICENSE](LICENSE).
