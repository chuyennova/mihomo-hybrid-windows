#!/usr/bin/env bash
set -Eeuo pipefail
echo "time_utc=$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
echo "pwd=$PWD"
echo "tag=${UPSTREAM_TAG:-unknown}"
echo "upstream_commit=${UPSTREAM_COMMIT:-unknown}"
echo "patch_revision=${PATCH_REVISION:-unknown}"
git --version
git rev-parse HEAD
go version
go env GOOS GOARCH GOAMD64 GOMOD GOTOOLCHAIN
python3 --version
