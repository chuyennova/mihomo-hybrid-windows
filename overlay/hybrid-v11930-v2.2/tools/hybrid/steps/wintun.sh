#!/usr/bin/env bash
set -Eeuo pipefail

version=0.14.1
expected=07c256185d6ee3652e09fa55c0b673e2624b565e02c4b9091c79ca7d2f24ef51

rm -f wintun.zip
curl --fail --location --retry 2 --retry-delay 3 --connect-timeout 20 \
  "https://www.wintun.net/builds/wintun-${version}.zip" -o wintun.zip

echo "${expected}  wintun.zip" | sha256sum -c -

mkdir -p dist
unzip -j -o wintun.zip 'wintun/bin/amd64/wintun.dll' -d dist
unzip -j -o wintun.zip 'wintun/LICENSE.txt' -d dist
mv -f dist/LICENSE.txt dist/LICENSE-wintun.txt

python3 "${BUILDER_ROOT:?BUILDER_ROOT required}/scripts/verify_pe.py" dist/wintun.dll
test -s dist/LICENSE-wintun.txt
