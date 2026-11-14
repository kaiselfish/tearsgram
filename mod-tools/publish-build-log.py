"""Publish the tail of the Bazel compile log as a public issue.

Workflow job logs on a repository without admin rights are not downloadable
through the API (`403 Must have admin rights to Repository`), and the run page
only shows them to a signed-in owner. A public issue is readable by anyone, so
a failed `Compile iPhone IPA` step hands its diagnostics to this script.

Environment:
    GITHUB_TOKEN       token injected by the workflow
    GITHUB_REPOSITORY  owner/repo
    GITHUB_RUN_ID      run id
    GITHUB_SHA         commit being built
    RUNNER_TEMP        directory holding compile.log

Exit status is always 0: the failing build already failed the job, and a
diagnostics step must not mask or alter that.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

ERROR_PATTERN = re.compile(
    r"error:|ERROR:|fatal error|Traceback|BUILD FAILED|Undefined symbols|"
    r"error\]|xcodebuild: error|Failed to build"
)
MAX_INTERESTING = 60
MAX_TAIL = 40
MAX_BODY = 60000


def read_log() -> tuple[bool, str]:
    temp = os.environ.get("RUNNER_TEMP") or os.environ.get("TMPDIR") or "/tmp"
    path = Path(temp) / "compile.log"
    if not path.is_file():
        return False, ""
    return True, path.read_text(encoding="utf-8", errors="replace")


def build_body(found: bool, text: str) -> str:
    header = [
        f"Commit: `{os.environ.get('GITHUB_SHA', 'unknown')}`",
        f"Run: {os.environ.get('GITHUB_RUN_ID', 'unknown')}",
        "",
    ]
    if not found:
        header.append(
            "compile.log was not produced: the step failed before the Bazel "
            "build started (prepare-mod-icon.py or the shell pipeline)."
        )
        return "\n".join(header)

    lines = text.splitlines()
    interesting = [line for line in lines if ERROR_PATTERN.search(line)]
    tail = lines[-MAX_TAIL:]
    parts = list(header)
    parts.append(f"Lines in log: {len(lines)}; error-like lines: {len(interesting)}")
    parts.append("")
    if interesting:
        parts.append("Error lines:")
        parts.append("```")
        parts.extend(interesting[:MAX_INTERESTING])
        parts.append("```")
    parts.append("Last 40 lines:")
    parts.append("```")
    parts.extend(tail)
    parts.append("```")
    body = "\n".join(parts)
    return body[:MAX_BODY]


def request(method: str, url: str, token: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "tearsgram-ci")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN", "")
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or not repository:
        print("GITHUB_TOKEN or GITHUB_REPOSITORY is missing; nothing to publish")
        return 0

    found, text = read_log()
    body = build_body(found, text)
    title = f"build log {os.environ.get('GITHUB_RUN_ID', '')}"
    payload = {
        "title": title,
        "body": body,
        "labels": [],
    }
    try:
        issue = request(
            "POST",
            f"https://api.github.com/repos/{repository}/issues",
            token,
            payload,
        )
        print(f"published {issue.get('html_url')}")
    except urllib.error.HTTPError as error:
        print(f"could not publish log: {error.code} {error.read()[:500]!r}")
    except urllib.error.URLError as error:
        print(f"could not publish log: {error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())