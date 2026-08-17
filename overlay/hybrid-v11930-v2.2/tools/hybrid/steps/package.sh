#!/usr/bin/env bash
set -Eeuo pipefail

cd dist

for f in verge-mihomo.exe wintun.dll LICENSE-wintun.txt; do
  test -s "$f"
done

sha256sum verge-mihomo.exe wintun.dll LICENSE-wintun.txt > SHA256SUMS.txt

cat > build-info.json <<JSON
{
  "upstream_tag": "${UPSTREAM_TAG}",
  "upstream_commit": "${UPSTREAM_COMMIT}",
  "baseline_tag": "${BASELINE_TAG}",
  "patch_revision": "${PATCH_REVISION}",
  "goos": "windows",
  "goarch": "amd64",
  "goamd64": "v2",
  "wintun_version": "0.14.1",
  "built_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "workflow_run": "${GITHUB_SERVER_URL:-https://github.com}/${GITHUB_REPOSITORY:-local}/actions/runs/${GITHUB_RUN_ID:-local}"
}
JSON

sha256sum build-info.json >> SHA256SUMS.txt

zip_name="verge-mihomo-${UPSTREAM_TAG}-hybrid-windows-amd64.zip"
rm -f "$zip_name"
zip -9 -j "$zip_name" \
  verge-mihomo.exe \
  wintun.dll \
  LICENSE-wintun.txt \
  SHA256SUMS.txt \
  build-info.json
