#!/usr/bin/env bash
# Finalizer always runs and never masks the original build failure.
set +e
set -uo pipefail
mkdir -p logs/steps logs/diagnostics dist .ci-status

steps=(prepare source-tree go-environment install-tools source-verify vendor apply-vendor gofmt verify profile-audit tests compile wintun package)
status_of() {
  local f=".ci-status/$1.exit"
  if [[ -f "$f" ]]; then
    local rc
    rc="$(cat "$f" 2>/dev/null)"
    [[ "$rc" == "0" ]] && echo OK || echo "FAILED(${rc:-unknown})"
  else
    echo SKIPPED
  fi
}

first_failed=""
for step in "${steps[@]}"; do
  state="$(status_of "$step")"
  if [[ -z "$first_failed" && "$state" == FAILED* ]]; then
    first_failed="$step"
  fi
done

{
  echo "Mihomo hybrid build summary"
  echo "upstream_tag=${UPSTREAM_TAG:-v1.19.30}"
  echo "patch_revision=${PATCH_REVISION:-hybrid-4profiles-v2.2-v11930}"
  echo "commit_sha=${GITHUB_SHA:-unknown}"
  echo "build_date_utc=$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  echo "workflow_run_id=${GITHUB_RUN_ID:-unknown}"
  echo "workflow_run_attempt=${GITHUB_RUN_ATTEMPT:-unknown}"
  echo "workflow_run_url=${GITHUB_SERVER_URL:-https://github.com}/${GITHUB_REPOSITORY:-unknown}/actions/runs/${GITHUB_RUN_ID:-unknown}"
  echo "runner_os=${RUNNER_OS:-unknown}"
  echo "runner_arch=${RUNNER_ARCH:-unknown}"
  echo "go_version=$(go version 2>/dev/null || echo unavailable)"
  echo "python_version=$(python3 --version 2>/dev/null || echo unavailable)"
  echo "first_failed_step=${first_failed:-none}"
  echo "GOOS=windows"
  echo "GOARCH=amd64"
  echo "GOAMD64=v2"
  [[ -f go.mod ]] && echo "go_mod_sha256=$(sha256sum go.mod | awk '{print $1}')"
  [[ -f go.sum ]] && echo "go_sum_sha256=$(sha256sum go.sum | awk '{print $1}')"
  echo
  echo "Dependency pins:"
  grep -E 'github.com/metacubex/(sing-wireguard|gvisor|wireguard-go)|golang.zx2c4.com/wireguard' go.mod 2>/dev/null || true
  echo
  echo "Step results:"
  for step in "${steps[@]}"; do
    printf '%-20s %s\n' "$step" "$(status_of "$step")"
  done
  echo
  if [[ -f dist/verge-mihomo.exe ]]; then
    echo "binary_sha256=$(sha256sum dist/verge-mihomo.exe | awk '{print $1}')"
    echo "binary_size=$(stat -c '%s' dist/verge-mihomo.exe 2>/dev/null || echo unknown)"
  fi
  if [[ -f dist/wintun.dll ]]; then
    echo "wintun_sha256=$(sha256sum dist/wintun.dll | awk '{print $1}')"
    echo "wintun_size=$(stat -c '%s' dist/wintun.dll 2>/dev/null || echo unknown)"
  fi
} > summary.txt

python3 - <<'PY' > summary.json 2>/dev/null || true
import json, os, pathlib
steps = ["prepare", "source-tree", "go-environment", "install-tools", "source-verify", "vendor", "apply-vendor", "gofmt", "verify", "profile-audit", "tests", "compile", "wintun", "package"]
result = {
    "upstream_tag": os.getenv("UPSTREAM_TAG", "v1.19.30"),
    "patch_revision": os.getenv("PATCH_REVISION", "hybrid-4profiles-v2.2-v11930"),
    "commit_sha": os.getenv("GITHUB_SHA", "unknown"),
    "workflow_run_id": os.getenv("GITHUB_RUN_ID", "unknown"),
    "workflow_run_attempt": os.getenv("GITHUB_RUN_ATTEMPT", "unknown"),
    "steps": {},
}
for step in steps:
    p = pathlib.Path(".ci-status") / f"{step}.exit"
    value = p.read_text().strip() if p.exists() else ""
    result["steps"][step] = int(value) if value.isdigit() else None
failed = [k for k,v in result["steps"].items() if v not in (None, 0)]
result["first_failed_step"] = failed[0] if failed else None
print(json.dumps(result, indent=2, sort_keys=True))
PY

{
  echo "===== FINAL DIAGNOSTICS ====="
  date -u +'%Y-%m-%dT%H:%M:%SZ'
  echo
  echo "--- summary ---"
  cat summary.txt
  echo
  echo "--- git status --short ---"
  git status --short 2>&1 || true
  echo
  echo "--- git diff --stat ---"
  git diff --stat 2>&1 || true
  echo
  echo "--- disk ---"
  df -h . 2>&1 || true
  echo
  echo "--- artifact files ---"
  find dist -maxdepth 2 -type f -printf '%p %s bytes\n' 2>/dev/null | sort || true
  echo "===== END FINAL DIAGNOSTICS ====="
} | tee -a full-build.log > logs/final-diagnostics.log

cp -f summary.txt logs/summary.txt 2>/dev/null || true
cp -f summary.json logs/summary.json 2>/dev/null || true
cp -f full-build.log logs/full-build.log 2>/dev/null || : > logs/full-build.log
cp -f tools/hybrid/SOURCE_LOCKS.md logs/SOURCE_LOCKS.md 2>/dev/null || true
cp -f tools/hybrid/MANIFEST-SHA256.txt logs/MANIFEST-SHA256.txt 2>/dev/null || true
cp -f tools/hybrid/INTEGRATION_REPORT.md logs/INTEGRATION_REPORT.md 2>/dev/null || true
[[ -f logs/profile-audit.txt ]] && cp -f logs/profile-audit.txt logs/diagnostics/profile-audit.final.txt 2>/dev/null || true
[[ -f logs/profile-audit.json ]] && cp -f logs/profile-audit.json logs/diagnostics/profile-audit.final.json 2>/dev/null || true

rm -f dist/hybrid-build-logs.zip
(
  cd logs || exit 0
  zip -9 -r ../dist/hybrid-build-logs.zip . >/dev/null 2>&1
)
exit 0
