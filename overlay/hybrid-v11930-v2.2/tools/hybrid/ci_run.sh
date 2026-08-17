#!/usr/bin/env bash
# Execute one CI command while recording a complete per-step log and a combined log.
set -uo pipefail

step="${1:?step name required}"
shift
if [[ "$#" -eq 0 ]]; then
  echo "ci_run: command required" >&2
  exit 64
fi

mkdir -p .ci-status logs/steps logs/diagnostics dist
full_log="full-build.log"
step_log="logs/steps/${step}.log"
: > "$step_log"

start_iso="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
start_epoch="$(date +%s)"
{
  echo
  echo "===== STEP: ${step} ====="
  echo "start=${start_iso}"
  echo "pwd=$(pwd)"
  printf 'command='; printf '%q ' "$@"; echo
  echo "environment: GOOS=${GOOS:-unset} GOARCH=${GOARCH:-unset} GOAMD64=${GOAMD64:-unset} CGO_ENABLED=${CGO_ENABLED:-unset} GOFLAGS=${GOFLAGS:-unset}"
} | tee -a "$step_log" "$full_log"

set +e
"$@" 2>&1 | tee -a "$step_log" "$full_log"
rc=${PIPESTATUS[0]}
set -e

end_iso="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
end_epoch="$(date +%s)"
duration="$((end_epoch - start_epoch))"
{
  echo "end=${end_iso}"
  echo "duration_seconds=${duration}"
  echo "exit_code=${rc}"
  echo "===== END STEP: ${step} ====="
} | tee -a "$step_log" "$full_log"
printf '%s\n' "$rc" > ".ci-status/${step}.exit"
printf '%s\n' "$start_iso" > ".ci-status/${step}.start"
printf '%s\n' "$end_iso" > ".ci-status/${step}.end"

if [[ "$rc" -ne 0 ]]; then
  diag="logs/diagnostics/${step}-failure.txt"
  {
    echo "failed_step=${step}"
    echo "exit_code=${rc}"
    echo "time_utc=${end_iso}"
    echo
    echo "--- last 200 lines of step log ---"
    tail -n 200 "$step_log" 2>/dev/null || true
    echo
    echo "--- git status --short ---"
    git status --short 2>&1 || true
    echo
    echo "--- disk ---"
    df -h 2>&1 || true
    echo
    echo "--- memory ---"
    free -h 2>&1 || true
    echo
    echo "--- process limits ---"
    ulimit -a 2>&1 || true
  } > "$diag"
  cat "$diag" >> "$full_log"
fi

exit "$rc"
