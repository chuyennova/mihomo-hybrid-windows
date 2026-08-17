#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import time
import zipfile

root = pathlib.Path(os.environ.get("LOG_ROOT", "ci-logs"))
root.mkdir(parents=True, exist_ok=True)
status_dir = root / "status"
diagnostics = root / "diagnostics"
diagnostics.mkdir(parents=True, exist_ok=True)

order = [
    "clone-upstream",
    "setup-go",
    "upstream-compat",
    "go-environment",
    "apply-core-patch",
    "core-baseline-verify",
    "prepare-modules",
    "source-verify",
    "install-tools",
    "vendor",
    "apply-vendor-overlay",
    "gofmt",
    "verify-hybrid",
    "profile-audit",
    "tests",
    "compile",
    "wintun",
    "linux-smoke",
    "package",
    "windows-smoke",
    "release",
]

failure_codes = {
    "clone-upstream": "E03_CHECKOUT",
    "setup-go": "E04_GO_SETUP",
    "upstream-compat": "E08_UPSTREAM_COMPAT",
    "go-environment": "E09_GO_ENV",
    "apply-core-patch": "E10_CORE_PATCH",
    "core-baseline-verify": "E10_CORE_VERIFY",
    "prepare-modules": "E11_MODULE_PREP",
    "source-verify": "E12_PATCH_VERIFY",
    "install-tools": "E19_TOOLS",
    "vendor": "E20_DEPENDENCY",
    "apply-vendor-overlay": "E21_VENDOR_PATCH",
    "gofmt": "E22_GOFMT",
    "verify-hybrid": "E23_PATCH_VERIFY",
    "profile-audit": "E24_PROFILE_AUDIT",
    "tests": "E25_TEST",
    "compile": "E30_COMPILE",
    "linux-smoke": "E40_SMOKE",
    "windows-smoke": "E41_WINDOWS_SMOKE",
    "wintun": "E42_WINTUN_DLL",
    "package": "E50_PACKAGE",
    "release": "E60_RELEASE_UPLOAD",
}

def read_status(step: str):
    p = status_dir / f"{step}.exit"
    if not p.exists():
        return None
    text = p.read_text(encoding="utf-8", errors="replace").strip()
    try:
        return int(text)
    except Exception:
        return None

def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

steps = {step: read_status(step) for step in order}
first_failed = next(
    (step for step in order if steps[step] is not None and steps[step] != 0),
    None,
)

summary = {
    "upstream_tag": os.getenv("UPSTREAM_TAG", "unknown"),
    "upstream_commit": os.getenv("UPSTREAM_COMMIT", "unknown"),
    "baseline_tag": os.getenv("BASELINE_TAG", "v1.19.30"),
    "patch_revision": os.getenv("PATCH_REVISION", "unknown"),
    "workflow_run_id": os.getenv("GITHUB_RUN_ID", "local"),
    "workflow_run_attempt": os.getenv("GITHUB_RUN_ATTEMPT", "local"),
    "workflow_run_url": (
        f"{os.getenv('GITHUB_SERVER_URL', 'https://github.com')}/"
        f"{os.getenv('GITHUB_REPOSITORY', 'unknown')}/actions/runs/"
        f"{os.getenv('GITHUB_RUN_ID', 'unknown')}"
    ),
    "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "first_failed_step": first_failed,
    "failure_code": failure_codes.get(first_failed) if first_failed else None,
    "steps": steps,
}

for file_name in (
    "source/go.mod",
    "source/go.sum",
    "source/dist/verge-mihomo.exe",
    "source/dist/wintun.dll",
    "source/dist/SHA256SUMS.txt",
    "source/dist/build-info.json",
):
    p = pathlib.Path(file_name)
    if p.exists() and p.is_file():
        summary[file_name.replace("/", "_") + "_sha256"] = sha256(p)
        summary[file_name.replace("/", "_") + "_size"] = p.stat().st_size

# Pull the source-side audit and detailed diagnostics into the always-uploaded
# root log tree. This remains available even when compile/package fails later.
source_logs = pathlib.Path("source/logs")
if source_logs.exists():
    dest = root / "source-logs"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(source_logs, dest)

for rel in (
    "source/tools/hybrid/SOURCE_LOCKS.md",
    "source/tools/hybrid/INTEGRATION_REPORT.md",
    "source/tools/hybrid/V2_2_FIX_NOTES.md",
    "source/tools/hybrid/STATIC_CHECK_REPORT.txt",
    "source/tools/hybrid/MANIFEST-SHA256.txt",
):
    p = pathlib.Path(rel)
    if p.exists():
        shutil.copy2(p, diagnostics / p.name)

(root / "summary.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)

lines = [
    "Mihomo hybrid auto-build summary",
    f"upstream_tag={summary['upstream_tag']}",
    f"upstream_commit={summary['upstream_commit']}",
    f"baseline_tag={summary['baseline_tag']}",
    f"patch_revision={summary['patch_revision']}",
    f"workflow_run_url={summary['workflow_run_url']}",
    f"generated_utc={summary['generated_utc']}",
    f"first_failed_step={summary['first_failed_step'] or 'none'}",
    f"failure_code={summary['failure_code'] or 'none'}",
    "",
    "Step results:",
]

for step in order:
    value = steps[step]
    if value is None:
        state = "SKIPPED"
    elif value == 0:
        state = "PASS"
    else:
        state = f"FAILED({value})"
    lines.append(f"{step:24} {state}")

(root / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

# Always provide a single downloadable archive, independent of Release creation.
archive = root / "downloadable-logs.zip"
if archive.exists():
    archive.unlink()

with zipfile.ZipFile(
    archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9
) as zf:
    for p in sorted(root.rglob("*")):
        if p.is_file() and p != archive:
            zf.write(p, p.relative_to(root))

print(root / "summary.txt")
