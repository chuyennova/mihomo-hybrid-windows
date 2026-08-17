#!/usr/bin/env bash
set -Eeuo pipefail

root="${1:-source}"
overlay="${BUILDER_ROOT:?BUILDER_ROOT required}/overlay/hybrid-v11930-v2.2"
LOG_ROOT="${LOG_ROOT:?LOG_ROOT required}"
tag="${UPSTREAM_TAG:?UPSTREAM_TAG required}"
baseline="${BASELINE_TAG:-v1.19.30}"

cd "$root"
mkdir -p "$LOG_ROOT/diagnostics"

cp -f go.mod "$LOG_ROOT/diagnostics/go.mod.upstream"
cp -f go.sum "$LOG_ROOT/diagnostics/go.sum.upstream"

module="$(awk '$1=="module"{print $2;exit}' go.mod)"
[[ "$module" == "github.com/metacubex/mihomo" ]] || {
  echo "E11_MODULE_PREP: unexpected module=$module"
  exit 21
}

if [[ "$tag" == "$baseline" ]]; then
  # Reproduce the exact resolved graph that produced the known-good v1.19.30
  # hybrid binary. Never overwrite a non-matching baseline silently.
  test "$(sha256sum go.mod | awk '{print $1}')" = "944b5c26fc12aec517a436d9204f034b513269b46ee66b900ba0855c9b53e9f3"
  test "$(sha256sum go.sum | awk '{print $1}')" = "39e3b062203a576c15c217de36a0e82589e0deedd2225363554214bebbc7cdbf"

  cp -f "$overlay/module-lock/go.mod" go.mod
  cp -f "$overlay/module-lock/go.sum" go.sum
  echo "MODULE_MODE=frozen-baseline"
else
  # For a future tag, preserve its own dependency graph. Add only the native
  # Windows requirements, let Go resolve the minimum required graph once, then
  # lock it for the remainder of this run. The vendor source-lock gate below
  # will still reject incompatible gVisor/sing-wireguard changes.
  GOWORK=off GOFLAGS=-mod=mod go mod edit \
    -require=golang.zx2c4.com/wireguard@v0.0.0-20250521234502-f333402bd9cb \
    -require=golang.zx2c4.com/wireguard/windows@v1.0.1

  set +e
  GOWORK=off GOFLAGS=-mod=mod go mod tidy -v \
    2>&1 | tee "$LOG_ROOT/diagnostics/go-mod-tidy-future-tag.log"
  rc=${PIPESTATUS[0]}
  set -e
  [[ "$rc" -eq 0 ]] || exit "$rc"

  echo "MODULE_MODE=future-tag-resolved"
fi

# Critical upstream network revisions must remain the exact source base that
# the v2.2 vendor overlay was reviewed against.
grep -F "github.com/metacubex/sing-wireguard v0.0.0-20260810013230-110eac03c3f0" go.mod
grep -F "github.com/metacubex/gvisor v0.0.0-20260810011720-3cc44cf9ac22" go.mod
grep -F "github.com/metacubex/wireguard-go v0.0.0-20250820062549-a6cecdd7f57f" go.mod
grep -F "golang.zx2c4.com/wireguard v0.0.0-20250521234502-f333402bd9cb" go.mod
grep -F "golang.zx2c4.com/wireguard/windows v1.0.1" go.mod

cp -f go.mod "$LOG_ROOT/diagnostics/go.mod.prepared"
cp -f go.sum "$LOG_ROOT/diagnostics/go.sum.prepared"
sha256sum go.mod go.sum | tee "$LOG_ROOT/diagnostics/go-module-hashes.prepared.txt"

git diff --no-ext-diff -- go.mod go.sum \
  > "$LOG_ROOT/diagnostics/go-module-graph.diff" || true
