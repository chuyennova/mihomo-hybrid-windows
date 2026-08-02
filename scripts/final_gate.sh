#!/usr/bin/env bash
set -uo pipefail
LOG_ROOT="${LOG_ROOT:-ci-logs}"
required=(clone-upstream setup-go go-environment apply-core-patch prepare-modules source-verify vendor apply-vendor-patch gofmt verify-patch tests compile wintun package linux-smoke)
failed=0
for s in "${required[@]}"; do
  f="$LOG_ROOT/status/$s.exit"
  if [[ ! -f "$f" ]]; then echo "FINAL_GATE $s=MISSING"; failed=1
  elif [[ "$(cat "$f")" != 0 ]]; then echo "FINAL_GATE $s=FAILED($(cat "$f"))"; failed=1
  else echo "FINAL_GATE $s=PASS"; fi
done
exit "$failed"
