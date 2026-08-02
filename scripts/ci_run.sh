#!/usr/bin/env bash
set -uo pipefail
step="${1:?step required}"; shift
[[ $# -gt 0 ]] || { echo "ci_run: command required" >&2; exit 64; }
LOG_ROOT="${LOG_ROOT:-$PWD/ci-logs}"
mkdir -p "$LOG_ROOT/steps" "$LOG_ROOT/diagnostics" "$LOG_ROOT/status"
full="$LOG_ROOT/full-build.log"; log="$LOG_ROOT/steps/${step}.log"
touch "$full"; : > "$log"
start="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"; start_s="$(date +%s)"
{
  echo; echo "===== STEP ${step} ====="; echo "start=${start}"; echo "pwd=$PWD"
  printf 'command='; printf '%q ' "$@"; echo
} | tee -a "$log" "$full"
set +e
"$@" 2>&1 | tee -a "$log" "$full"
rc=${PIPESTATUS[0]}
set -e
end="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
{
  echo "end=${end}"; echo "duration_seconds=$(($(date +%s)-start_s))"; echo "exit_code=${rc}"; echo "===== END ${step} ====="
} | tee -a "$log" "$full"
printf '%s\n' "$rc" > "$LOG_ROOT/status/${step}.exit"
if [[ $rc -ne 0 ]]; then
  {
    echo "failed_step=${step}"; echo "exit_code=${rc}"; echo "time=${end}"
    echo; echo "--- tail ---"; tail -n 250 "$log" || true
    echo; echo "--- git status ---"; git status --short 2>&1 || true
    echo; echo "--- rejected hunks ---"; find . -maxdepth 8 -type f -name '*.rej' -print -exec sed -n '1,240p' {} \; 2>&1 || true
    echo; echo "--- disk ---"; df -h || true
    echo; echo "--- memory ---"; free -h || true
  } > "$LOG_ROOT/diagnostics/${step}-failure.txt"
fi
exit "$rc"
