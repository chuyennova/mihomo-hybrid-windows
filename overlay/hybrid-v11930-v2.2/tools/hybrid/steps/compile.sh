#!/usr/bin/env bash
set -Eeuo pipefail

mkdir -p dist
version="${UPSTREAM_TAG:?UPSTREAM_TAG required}-hybrid-4profiles-${PATCH_REVISION:?PATCH_REVISION required}"
buildtime="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

GOWORK=off GOFLAGS=-mod=vendor go env

GOWORK=off GOFLAGS=-mod=vendor go build -v -tags with_gvisor -trimpath \
  -ldflags "-extldflags --static -X github.com/metacubex/mihomo/constant.Version=${version} -X github.com/metacubex/mihomo/constant.BuildTime=${buildtime} -w -s -buildid=" \
  -o dist/verge-mihomo.exe .

test -s dist/verge-mihomo.exe
