# Auto-build policy — baseline v1.19.30 hybrid v2.2

This directory is copied from the known-good
`mihomo-v1.19.30-hybrid-4profiles-overlay-v2.2-testtype-fix` logic.

The auto-builder uses `v1.19.30` as its compatibility baseline.

## Exact baseline build

For `UPSTREAM_TAG=v1.19.30`:

- clean upstream `wireguard.go`, `go.mod`, and `go.sum` hashes are verified;
- the reviewed core patch must reproduce the exact five hybrid adapter files;
- the exact frozen `go.mod/go.sum` from the known-good hybrid build are installed;
- vendor source hashes must match the reviewed gVisor/sing-wireguard commits.

## Future tag build

For a tag newer than `v1.19.30`:

- the tag is fetched directly from `MetaCubeX/mihomo`;
- the core patch is attempted with `git apply --3way`;
- the critical network dependency pins must still match the reviewed baseline;
- only the two native Windows WireGuard requirements are added to the future tag;
- Go resolves that future tag's module graph once;
- the locked vendor overlay refuses to overwrite dependency files whose source
  hashes no longer match;
- semantic profile audit and targeted tests must pass.

If any compatibility gate fails, the build stops, no Release is published, and
downloadable diagnostics are retained. This is intentional: the builder must
never silently replace a future upstream dependency graph with an old one.
