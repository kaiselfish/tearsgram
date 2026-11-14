"""Publish the step logs of a failed run into the `ci-logs` branch.

Workflow job logs are not downloadable through the API without repository admin
rights (`403 Must have admin rights to Repository`), and the run page only shows
them to a signed-in owner. The `ci-logs` branch is readable by anyone through
`raw.githubusercontent.com`, which is not rate limited, so a failed run copies
every log its steps captured with `tee` there.

Files written to `ci-logs`:
    log-<run id>.txt   one per failed run
    latest.txt         copy of the most recent failure

Environment:
    GITHUB_TOKEN       token injected by the workflow (contents: write)
    GITHUB_REPOSITORY  owner/repo
    GITHUB_RUN_ID      run id
    GITHUB_SHA         commit being built
    RUNNER_TEMP        directory holding the per-step *.log files

Exit status is always 0: the failing run already failed the job, and a
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
    r"error\]|xcodebuild: error|Failed to build|Analysis of target|no such module|"
    r"Assertion|Precondition|precondition failed|Fatal error"
)
MAX_INTERESTING = 80
MAX_TAIL = 60
MAX_TEXT = 90000
MAX_TOTAL = 160000


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


def temp_directory() -> Path:
    return Path(os.environ.get("RUNNER_TEMP") or os.environ.get("TMPDIR") or "/tmp")


def read_logs() -> list[tuple[str, str]]:
    directory = temp_directory()
    logs: list[tuple[str, str]] = []
    for path in sorted(directory.glob("*.log")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as error:
            text = f"could not read {path}: {error}"
        logs.append((path.name, text))
    return logs


def section(name: str, text: str) -> str:
    lines = text.splitlines()
    interesting = [line for line in lines if ERROR_PATTERN.search(line)]
    parts = [f"=== {name} ({len(lines)} lines, {len(interesting)} error-like) ==="]
    if interesting:
        parts.append("--- error lines ---")
        parts.extend(interesting[:MAX_INTERESTING])
    parts.append(f"--- last {MAX_TAIL} lines ---")
    parts.extend(lines[-MAX_TAIL:])
    return "\n".join(parts)[:MAX_TEXT]


def build_text(logs: list[tuple[str, str]]) -> str:
    header = [
        f"commit: {os.environ.get('GITHUB_SHA', 'unknown')}",
        f"run: {os.environ.get('GITHUB_RUN_ID', 'unknown')}",
        "",
    ]
    if not logs:
        directory = temp_directory()
        header.append(f"no *.log files in {directory}; the failing step captured no output.")
        header.append(f"directory listing: {sorted(p.name for p in directory.glob('*'))[:40]}")
        return "\n".join(header)
    header.append("logs: " + ", ".join(name for name, _ in logs))
    body = "\n".join(header) + "\n\n"
    body += "\n\n".join(section(name, text) for name, text in logs)
    return body[:MAX_TOTAL]


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

    logs = read_logs()
    text = build_text(logs)
    print(text[:6000])

    if ensure_branch(repository, token) is None:
        return 0

    put_file(repository, token, "latest.txt", text)
    run_id = os.environ.get("GITHUB_RUN_ID", "unknown")
    put_file(repository, token, f"log-{run_id}.txt", text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())