#!/usr/bin/env bash
set -uo pipefail

LOG_ROOT="${LOG_ROOT:-ci-logs}"

required=(
  clone-upstream
  setup-go
  upstream-compat
  go-environment
  apply-core-patch
  core-baseline-verify
  prepare-modules
  source-verify
  install-tools
  vendor
  apply-vendor-overlay
  gofmt
  verify-hybrid
  profile-audit
  tests
  compile
  wintun
  linux-smoke
  package
)

failed=0

for step in "${required[@]}"; do
  file="$LOG_ROOT/status/${step}.exit"

  if [[ ! -f "$file" ]]; then
    echo "FINAL_GATE ${step}=MISSING"
    failed=1
    continue
  fi

  rc="$(cat "$file" 2>/dev/null || echo unknown)"

  if [[ "$rc" == "0" ]]; then
    echo "FINAL_GATE ${step}=PASS"
  else
    echo "FINAL_GATE ${step}=FAILED(${rc})"
    failed=1
  fi
done

if [[ "$failed" -ne 0 ]]; then
  echo "FINAL_GATE build is not releasable; download the build logs."
  exit 1
fi

echo "FINAL_GATE all mandatory build steps passed."
