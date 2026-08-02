#!/usr/bin/env bash
set -Eeuo pipefail
root="${1:-source}"
patch="${BUILDER_ROOT:?BUILDER_ROOT required}/overlay/hybrid-v6/patches/0001-mihomo-core-hybrid-4profiles.patch"
test -f "$patch"
git -C "$root" apply --3way --whitespace=error-all "$patch"
if git -C "$root" ls-files -u | grep -q .; then
  echo "E10_CORE_PATCH: merge conflicts detected"
  git -C "$root" ls-files -u
  exit 20
fi
mkdir -p "$root/tools"
rm -rf "$root/tools/hybrid"
cp -a "${BUILDER_ROOT}/overlay/hybrid-v6/tools/hybrid" "$root/tools/hybrid"
printf '%s\n' "${PATCH_REVISION:?}" > "$root/tools/hybrid/PATCH_REVISION"
git -C "$root" diff --check
git -C "$root" diff --stat
