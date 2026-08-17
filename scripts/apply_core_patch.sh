#!/usr/bin/env bash
set -Eeuo pipefail

root="${1:-source}"
overlay="${BUILDER_ROOT:?BUILDER_ROOT required}/overlay/hybrid-v11930-v2.2"
patch="$overlay/patches/0001-mihomo-core-hybrid-4profiles-v11930.patch"

test -f "$patch"

git -C "$root" apply --3way --whitespace=error-all "$patch"

if git -C "$root" ls-files -u | grep -q .; then
  echo "E10_CORE_PATCH: merge conflicts detected"
  git -C "$root" ls-files -u
  exit 20
fi

mkdir -p "$root/tools"
rm -rf "$root/tools/hybrid"
cp -a "$overlay/tools/hybrid" "$root/tools/hybrid"
printf '%s\n' "${PATCH_REVISION:?PATCH_REVISION required}" > "$root/tools/hybrid/PATCH_REVISION"

git -C "$root" diff --check
git -C "$root" diff --stat
