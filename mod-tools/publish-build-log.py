"""Publish the tail of the Bazel compile log into the `ci-logs` branch.

Workflow job logs are not downloadable through the API without repository admin
rights (`403 Must have admin rights to Repository`), and the run page only shows
them to a signed-in owner. The `ci-logs` branch is readable by anyone through
`raw.githubusercontent.com`, which is not rate limited, so a failed
`Compile iPhone IPA` step copies its diagnostics there.

Files written to `ci-logs`:
    log-<run id>.txt   one per failed run
    latest.txt         copy of the most recent failure

Environment:
    GITHUB_TOKEN       token injected by the workflow (contents: write)
    GITHUB_REPOSITORY  owner/repo
    GITHUB_RUN_ID      run id
    GITHUB_SHA         commit being built
    RUNNER_TEMP        directory holding compile.log

Exit status is always 0: the failing build already failed the job, and a
diagnostics step must not mask or change that.
"""

from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

BRANCH = "ci-logs"
API = "https://api.github.com"
ERROR_PATTERN = re.compile(
    r"error:|ERROR:|fatal error|Traceback|BUILD FAILED|Undefined symbols|"
    r"error\]|xcodebuild: error|Failed to build|Analysis of target|no such module"
)
MAX_INTERESTING = 80
MAX_TAIL = 60
MAX_TEXT = 90000


def request(method: str, url: str, token: str, payload: dict | None = None) -> tuple[int, dict]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "tearsgram-ci")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8")
            return response.status, (json.loads(body) if body else {})
    except urllib.error.HTTPError as error:
        return error.code, {"message": error.read().decode("utf-8", "replace")[:500]}
    except urllib.error.URLError as error:
        return 0, {"message": str(error)}


def read_log() -> tuple[bool, str]:
    temp = os.environ.get("RUNNER_TEMP") or os.environ.get("TMPDIR") or "/tmp"
    path = Path(temp) / "compile.log"
    if not path.is_file():
        return False, ""
    return True, path.read_text(encoding="utf-8", errors="replace")


def build_text(found: bool, text: str) -> str:
    header = [
        f"commit: {os.environ.get('GITHUB_SHA', 'unknown')}",
        f"run: {os.environ.get('GITHUB_RUN_ID', 'unknown')}",
        "",
    ]
    if not found:
        header.append(
            "compile.log was not produced: the step failed before the Bazel build "
            "started (prepare-mod-icon.py or the shell pipeline)."
        )
        return "\n".join(header)

    lines = text.splitlines()
    interesting = [line for line in lines if ERROR_PATTERN.search(line)]
    header.append(f"log lines: {len(lines)}; error-like lines: {len(interesting)}")
    header.append("")
    header.append("=== error lines ===")
    header.extend(interesting[:MAX_INTERESTING])
    header.append("")
    header.append(f"=== last {MAX_TAIL} lines ===")
    header.extend(lines[-MAX_TAIL:])
    return "\n".join(header)[:MAX_TEXT]


def ensure_branch(repository: str, token: str) -> str | None:
    status, payload = request("GET", f"{API}/repos/{repository}/git/ref/heads/{BRANCH}", token)
    if status == 200:
        return payload.get("object", {}).get("sha")
    sha = os.environ.get("GITHUB_SHA", "")
    if not sha:
        print(f"cannot create {BRANCH}: no GITHUB_SHA")
        return None
    status, payload = request(
        "POST",
        f"{API}/repos/{repository}/git/refs",
        token,
        {"ref": f"refs/heads/{BRANCH}", "sha": sha},
    )
    if status in (200, 201):
        return sha
    print(f"cannot create {BRANCH}: {status} {payload}")
    return None


def put_file(repository: str, token: str, path: str, content: str) -> None:
    encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
    status, payload = request(
        "GET",
        f"{API}/repos/{repository}/contents/{path}?ref={BRANCH}",
        token,
    )
    body = {
        "message": f"ci log for run {os.environ.get('GITHUB_RUN_ID', '')}",
        "content": encoded,
        "branch": BRANCH,
    }
    if status == 200 and isinstance(payload, dict) and payload.get("sha"):
        body["sha"] = payload["sha"]
    status, payload = request(
        "PUT",
        f"{API}/repos/{repository}/contents/{path}",
        token,
        body,
    )
    print(f"{path}: {status} {payload.get('message', 'ok')}")


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN", "")
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or not repository:
        print("GITHUB_TOKEN or GITHUB_REPOSITORY is missing; nothing to publish")
        return 0

    found, raw = read_log()
    text = build_text(found, raw)
    print(text[:4000])

    if ensure_branch(repository, token) is None:
        return 0

    put_file(repository, token, "latest.txt", text)
    run_id = os.environ.get("GITHUB_RUN_ID", "unknown")
    put_file(repository, token, f"log-{run_id}.txt", text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())