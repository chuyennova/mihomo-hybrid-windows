#!/usr/bin/env bash
set -Eeuo pipefail

root="${1:-source}"
cd "$root"

echo "pwd=$PWD"
echo "upstream_tag=${UPSTREAM_TAG:-unknown}"
echo "upstream_commit=$(cat .upstream-commit 2>/dev/null || git rev-parse HEAD 2>/dev/null || echo unknown)"
echo "patch_revision=${PATCH_REVISION:-unknown}"
echo "go=$(go version)"
go env GOOS GOARCH GOAMD64 GOMOD GOTOOLCHAIN GOPATH GOCACHE
git status --short
df -h .
