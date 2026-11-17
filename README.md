# Ether plugin marketplace

This repository is the catalogue behind the **Marketplace** tab in Ether (Plugins › Marketplace). Every plugin listed here was reviewed. Its exact package is pinned by SHA-256, and the whole list is signed, so Ether shows and installs only what was merged here.

- Signed index: <https://braedonsaunders.github.io/ether-plugins/index.json> (signature: `index.json.sig`)
- Ether 0.3.14 and later read it out of the box.

## Submit a plugin

1. Build and check your plugin with the Ether SDK:

   ```sh
   ether plugin check ./my-plugin
   ether plugin pack -o my.plugin.id-1.0.0.etherpkg ./my-plugin
   ```

2. Attach the `.etherpkg` to a GitHub release in your own repository. The download URL must never change once published.
3. Run `ether plugin publish ./my-plugin --url <release asset URL>`. It prints the exact entry file for this repository, including the SHA-256.
4. Open a pull request that adds `plugins/<your.plugin.id>.yaml`. CI downloads your package, checks the digest and identity, and runs the conformance kit. A maintainer reviews the permissions and merges. The Marketplace picks it up within a few hours, or straight away when an owner presses Refresh.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the entry format and review rules.

## Updating or removing a plugin

- **New version:** add an item to `versions:` in your entry. Keep older versions: owners on them need them to roll back.
- **Pull a plugin:** set `revoked: true` and a `reason:`. Ether disables revoked plugins wherever they are installed and explains why.

## How the index is built

On every merge to `main`, CI compiles `plugins/*.yaml` into `index.json`, signs it with the catalogue key (`ETHER_CATALOGUE_PRIVATE_KEY`, held only as a repository secret), verifies the signature, and publishes both files to GitHub Pages. Ether verifies the signature against the public key it ships with, so a tampered index or package is refused.
