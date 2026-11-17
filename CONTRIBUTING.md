# Contributing a plugin

One file per plugin: `plugins/<id>.yaml`, named exactly after the plugin's manifest `id`.

```yaml
id: com.example.my-plugin          # must equal manifest.json "id"
name: "My Plugin"
summary: "One plain sentence, 140 characters at most, ending with a full stop."
description: "Optional longer text shown in the plugin's page."
kind: extension                    # source | integration | notification_channel | livetv_source | extension | content
category: lists                    # live_tv | subtitles | sources | automation | lists | ranking | metadata | insights | …
icon: https://example.com/icon.svg # optional, https
repo: https://github.com/you/my-plugin
homepage: https://example.com      # optional
author: Your Name
license: MIT
capabilities:                      # exactly the manifest's ether.capabilities
  - ui
  - tools
permissions:                       # exactly what the package asks for; reviewed by a maintainer
  catalog: read
screenshots:                       # optional, https
  - https://example.com/shot-1.png
versions:
  - version: 1.0.0                 # must equal manifest.json "version"
    url: https://github.com/you/my-plugin/releases/download/v1.0.0/com.example.my-plugin-1.0.0.etherpkg
    sha256: <64 hex characters, sha256 of the .etherpkg file>
    releasedAt: "2026-11-16T00:00:00Z"
    minEther: 0.3.14
```

`ether plugin publish ./my-plugin --url <asset URL>` writes this file for you from your manifest and package.

## What CI checks

- The YAML parses with no unknown fields. The id, kind and versions are valid, and the summary passes Ether's copy rules.
- Every non-revoked version downloads, is under 64 MiB, matches its `sha256`, and its manifest `id`/`version` match the entry.
- `ether plugin check` (the conformance kit) passes on the unpacked package.

## What a reviewer checks

- **Permissions are the minimum the plugin needs.** Network hosts are named, not wildcards, unless a wildcard is unavoidable. Viewer data needs a stated reason.
- **The summary says what the plugin does for an owner**, in plain words. No marketing.
- **The source is public**, and the release asset was built from it.
- **No piracy-specific scrapers or indexers**, and nothing that ships credentials.
- **Updates that widen permissions** are reviewed like a new plugin. Ether asks every owner to approve the added permissions before it updates.

Questions: open an issue in this repository.
