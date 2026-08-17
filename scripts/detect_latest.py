#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

baseline = os.getenv("BASELINE_TAG", "v1.19.30")
revision = os.getenv("RELEASE_REVISION", "r1")
repo = os.environ["GITHUB_REPOSITORY"]
token = os.getenv("GITHUB_TOKEN", "")

def api(path: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "mihomo-hybrid-auto-builder",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(
        "https://api.github.com" + path,
        headers=headers,
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)

def version(tag: str):
    return tuple(map(int, tag.removeprefix("v").split(".")))

release = api("/repos/MetaCubeX/mihomo/releases/latest")
tag = release.get("tag_name", "")
stable = (
    bool(re.fullmatch(r"v\d+\.\d+\.\d+", tag))
    and not release.get("draft", False)
    and not release.get("prerelease", False)
)

result = {
    "latest_tag": tag,
    "stable": stable,
    "release_tag": "",
    "release_exists": False,
    "blocked_by_issue": False,
    "should_build": False,
}

if stable:
    result["release_tag"] = f"hybrid-{tag}-{revision}"

# Do not spend more API calls when the latest stable is not newer than baseline.
if stable and version(tag) > version(baseline):
    release_path = (
        f"/repos/{repo}/releases/tags/"
        f"{urllib.parse.quote(result['release_tag'], safe='')}"
    )

    try:
        api(release_path)
        result["release_exists"] = True
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise

    issues = api(
        f"/repos/{repo}/issues?state=open&labels=auto-build-failed&per_page=100"
    )
    marker = f"<!-- mihomo-upstream-tag:{tag} -->"
    result["blocked_by_issue"] = any(
        marker in (item.get("body") or "") for item in issues
    )

    result["should_build"] = (
        not result["release_exists"] and not result["blocked_by_issue"]
    )

print(json.dumps(result, indent=2, sort_keys=True))

github_output = os.getenv("GITHUB_OUTPUT")
if github_output:
    with open(github_output, "a", encoding="utf-8") as stream:
        for key, value in result.items():
            if isinstance(value, bool):
                value = str(value).lower()
            stream.write(f"{key}={value}\n")
