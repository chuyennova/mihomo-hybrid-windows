# V4 — Go module tidy fix

## Failure fixed

GitHub Actions run `30753065418` stopped in `vendor` with:

```text
go: updates to go.mod needed; to update it:
    go mod tidy
```

The v3 workflow downloaded modules and immediately ran `go mod vendor`. The
standalone Windows/Wintun build, however, correctly normalized the module graph
with `go mod tidy` first. V4 restores that required step.

## What changed from v3

- `vendor.sh` now runs `go mod tidy -v` before download/vendor.
- Before/after `go.mod` and `go.sum`, hashes and a full tidy diff are archived.
- Exact `sing-wireguard`, `gvisor` and `wireguard-go` pins are rechecked after
  tidy.
- `vendor/modules.txt` hash and its resolved module headers are archived.
- Source verification explicitly checks all four profile selectors and both MTU
  default branches.

## What did not change

The profile implementation is byte-for-byte unchanged from v3:

- `windows` — lazy per-outbound Wintun/Winsock.
- `macos` — per-outbound macOS-like gVisor stack.
- `linux` — per-outbound Linux-like gVisor stack.
- `android` — per-outbound Android-like gVisor stack.
- Android defaults to MTU 1360 when YAML omits `mtu`; the other profiles retain
  MTU 1408. Explicit YAML `mtu` always wins.
