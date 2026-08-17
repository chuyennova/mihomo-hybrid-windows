# Validation report — Mihomo hybrid auto-builder v1.19.30+ / v2.2

## Input checked

Hybrid source overlay:

`mihomo-v1.19.30-hybrid-4profiles-overlay-v2.2-testtype-fix(2).zip`

SHA-256:

`6b6c86a86b830001cb097af95b76301307ee2e09a41c6b81204bd022973bc9bb`

The embedded source manifest was verified:

- entries: 44
- valid SHA-256: 44
- mismatches: 0
- missing: 0

## Upstream baseline checked

Clean source used for reconstruction: upstream Mihomo `v1.19.30`.

Verified hashes:

```text
adapter/outbound/wireguard.go
79e1112faaaf9fc7c5e84bc2811c7f7320c18504a734dc0bf399021f63c50868

go.mod
944b5c26fc12aec517a436d9204f034b513269b46ee66b900ba0855c9b53e9f3

go.sum
39e3b062203a576c15c217de36a0e82589e0deedd2225363554214bebbc7cdbf
```

These match `tools/hybrid/SOURCE_LOCKS.md` from the supplied v2.2 overlay.

## Auto core patch

Generated patch:

`overlay/hybrid-v11930-v2.2/patches/0001-mihomo-core-hybrid-4profiles-v11930.patch`

SHA-256:

`8dc56cad32bf41616aeb9b3363532182b22c40de24c2ed52efd06e753c37a07e`

The patch contains only these five adapter files:

```text
adapter/outbound/wireguard.go
adapter/outbound/wireguard_profile_gvisor.go
adapter/outbound/wireguard_profile_nogvisor.go
adapter/outbound/wireguard_profile_windows.go
adapter/outbound/wireguard_profile_windows_other.go
```

It does **not** contain the whole Mihomo source tree.

Applying the patch to clean v1.19.30 reproduced the supplied hybrid adapter
files byte-for-byte:

```text
be68f19eb83bdfde61f152fd9ff338182b9138e2da08d981230839ff1fa596ca  adapter/outbound/wireguard.go
6a1506c50a46a4cc57f7bf6b885494134d8775a42ba6f27140858adda966bb7e  adapter/outbound/wireguard_profile_gvisor.go
8064142ec21fb8be0f36787105542938ebfe61a9fc96ed51aa09ea91eeab4824  adapter/outbound/wireguard_profile_nogvisor.go
62a75134c7558b7dc3ce605bfe168e4a49f72977b84b059398c415f045d6caf3  adapter/outbound/wireguard_profile_windows.go
028858888337e8c73d31bf9935c9438367ee013f775626a93a05dc9dc9237755  adapter/outbound/wireguard_profile_windows_other.go
```

## Module graph policy

Known-good baseline `v1.19.30` installs the exact frozen graph supplied by the
hybrid v2.2 overlay:

```text
go.mod  239edfc51e752756e32367abd8feef379cb8e2b94891b78a6fc0438cabd2497a
go.sum  01424dfc0434d085a4ed9bab7046d1b3b1c16bea96e43a1f9ff8ebbe592f8546
```

For future tags, the builder does not blindly replace a changed upstream module
graph. It first requires the reviewed critical network dependency revisions,
adds only the native Windows WireGuard requirements, resolves the future tag
once, and then locks the graph for that run.

The vendor overlay still verifies the original SHA-256 of every gVisor /
sing-wireguard file before overwriting it. A dependency source change therefore
fails closed and produces logs instead of silently applying old code.

## Future-tag merge test

A synthetic future tag was created from v1.19.30 with an unrelated non-overlap
change in `adapter/outbound/wireguard.go`.

Result:

```text
git apply --3way: PASS
future upstream change preserved: PASS
4-profile selector preserved: PASS
```

This proves the auto patch can tolerate at least non-overlapping upstream
changes. It intentionally does not promise that every future WireGuard refactor
will merge.

## Static validation

Performed:

```text
Bash syntax for all *.sh: PASS
Python syntax for root scripts: PASS
YAML parse for all workflows: PASS
dynamic package script test: PASS
failure-log finalizer test: PASS
baseline core reconstruction: PASS
baseline module-lock reconstruction: PASS
```

Failure-log simulation produced:

```text
summary.txt
summary.json
full-build.log
downloadable-logs.zip
```

with `first_failed_step` and an error code.

## Windows/Wintun protections

The auto workflow:

- builds `GOOS=windows`, `GOARCH=amd64`, `GOAMD64=v2`;
- downloads Wintun 0.14.1;
- verifies the official Wintun archive SHA-256;
- verifies EXE and DLL as PE AMD64;
- on a Windows runner, loads `wintun.dll` using `NativeLibrary.Load`;
- runs `verge-mihomo.exe -v`;
- avoids the previous error where `wintun.dll` was copied onto itself.

## GitHub Actions behavior

No workflow has a `push` trigger.

- `auto-check.yml`: scheduled every two days + manual.
- `build-tag.yml`: reusable + manual exact-tag build.
- `test-baseline.yml`: manual known-good v1.19.30 dry-run.

A failed build does not publish a Release. Logs are uploaded with `if: always()`.
A single `auto-build-failed` Issue blocks repeated scheduled retries for the
same failed tag.

## Local validation limit

A complete dependency download, compilation, Windows DLL load, and executable
run require GitHub-hosted runners/network and therefore are not claimed by this
offline packaging validation.

Before relying on a future automatic tag, run once:

```text
Actions
-> Test known-good v1.19.30 hybrid baseline
-> Run workflow
```

Expected:

```text
Patch, audit, test and compile        PASS
Windows DLL and executable smoke     PASS
Publish GitHub Release               SKIPPED
```
