"""Authenticated cliagents broker client used by teacher workflows."""

import json
import os
import urllib.request
from pathlib import Path


CLIAGENTS_URL = os.environ.get("CLIAGENTS_URL", "http://127.0.0.1:4001").rstrip("/")


def cliagents_api_key():
    for env_name in ("CLIAGENTS_API_KEY", "CLI_AGENTS_API_KEY"):
        value = os.environ.get(env_name, "").strip()
        if value:
            return value

    candidates = []
    explicit_file = os.environ.get("CLIAGENTS_API_KEY_FILE", "").strip()
    data_dir = os.environ.get("CLIAGENTS_DATA_DIR", "").strip()
    if explicit_file:
        candidates.append(Path(explicit_file).expanduser())
    if data_dir:
        candidates.append(Path(data_dir).expanduser() / "local-api-key")
    candidates.append(Path.home() / ".codex/cliagents/local-api-key")

    for path in candidates:
        try:
            value = path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if value:
            return value
    return None


def call_cliagents(message, work_dir, *, max_output_tokens=1200, timeout_ms=300000):
    api_key = cliagents_api_key()
    if not api_key:
        raise RuntimeError("cliagents API key is unavailable")

    payload = json.dumps({
        "adapter": "codex-cli",
        "message": message,
        "workDir": str(Path(work_dir).resolve()),
        "timeout": timeout_ms,
        "max_output_tokens": max_output_tokens,
    }).encode("utf-8")
    broker_request = urllib.request.Request(
        f"{CLIAGENTS_URL}/ask",
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "X-API-Key": api_key,
        },
    )
    with urllib.request.urlopen(
        broker_request,
        timeout=(timeout_ms / 1000) + 10,
    ) as response:
        broker_result = json.loads(response.read().decode("utf-8"))

    result = broker_result.get("result") or broker_result.get("text") or ""
    if not result.strip():
        raise RuntimeError("cliagents returned an empty final response")
    return result
