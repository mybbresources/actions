# MyBB Resources Actions

`package-mybb-plugin.yml` builds a deterministic ZIP from an explicit file map and
uploads it with an unsigned `meta.json` and the source commit. Call it from a
reviewed commit or a version tag. Pin the reusable workflow to a commit SHA.

Each caller keeps a `catalog-package.json` with two keys. `manifest` contains the
catalog identity, requirements and uninstall policy. `files` lists repository
`source` paths, their site-relative `destination` paths, and the catalog `role`.
The builder supplies the release version, archive entry names and package digest.

Download the `catalog-submission` artifact. Upload the ZIP and `meta.json` in
the [catalog admin](https://plugins.mybbresources.com/admin) with the changelog.
The catalog scans and signs the archive and a separate administrator approves it.
