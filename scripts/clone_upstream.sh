#!/usr/bin/env bash
set -Eeuo pipefail

tag="${UPSTREAM_TAG:?UPSTREAM_TAG required}"
baseline="${BASELINE_TAG:-v1.19.30}"

[[ "$tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || {
  echo "E02_INVALID_TAG: $tag"
  exit 12
}

rm -rf source
git init -q source
git -C source remote add origin https://github.com/MetaCubeX/mihomo.git

# Fetch exact requested tag. Fetch the known-good baseline as well so
# git apply --3way has the baseline blobs available when a future tag changes.
git -C source fetch --no-tags --depth=1 origin "refs/tags/${tag}:refs/tags/${tag}"
if [[ "$tag" != "$baseline" ]]; then
  git -C source fetch --no-tags --depth=1 origin "refs/tags/${baseline}:refs/tags/${baseline}"
fi

git -C source checkout -q --detach "refs/tags/${tag}"

actual="$(git -C source describe --tags --exact-match HEAD)"
[[ "$actual" == "$tag" ]] || {
  echo "E03_TAG_COMMIT_MISMATCH expected=$tag actual=$actual"
  exit 13
}

git -C source rev-parse HEAD | tee source/.upstream-commit
