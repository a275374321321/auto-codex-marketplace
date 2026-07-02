#!/usr/bin/env python3
"""Codex lifecycle hooks for Auto Codex.

The hook layer is deliberately thin: it observes sessions and invokes the
deterministic Auto Codex writer. It never writes skills directly.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path


DEFAULT_SYNC_EVERY_STOPS = 3
DEFAULT_SYNC_DAYS = 30
DEFAULT_MAX_SESSIONS = 12
DEFAULT_MAX_CHARS = 16000
DEFAULT_LIFECYCLE_EVERY_HOURS = 24


def _plugin_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _auto_codex_script() -> Path:
    return _plugin_root() / "skills" / "auto-codex" / "scripts" / "auto_codex.py"


def _project_root() -> Path:
    return Path.cwd().resolve() / ".codex"


def _global_root() -> Path:
    return Path.home().resolve() / ".codex"


def _state_path() -> Path:
    return _project_root() / "auto-codex" / "hook_state.json"


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def _run_auto_codex(*args: str) -> dict:
    cmd = [
        sys.executable,
        str(_auto_codex_script()),
        *args,
        "--project-root",
        str(_project_root()),
        "--global-root",
        str(_global_root()),
        "--codex-home",
        str(_global_root()),
    ]
    completed = subprocess.run(
        cmd,
        cwd=str(Path.cwd()),
        text=True,
        capture_output=True,
        check=False,
        timeout=115,
    )
    return {
        "cmd": cmd,
        "returncode": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
    }


def _sync(reason: str, *, small: bool) -> dict:
    max_sessions = _int_env("AUTO_CODEX_MAX_SESSIONS", DEFAULT_MAX_SESSIONS)
    max_chars = _int_env("AUTO_CODEX_MAX_CHARS", DEFAULT_MAX_CHARS)
    days = _int_env("AUTO_CODEX_SYNC_DAYS", DEFAULT_SYNC_DAYS)
    if small:
        max_sessions = min(max_sessions, 4)
        max_chars = min(max_chars, 12000)
    args = [
        "sync",
        "--days",
        str(days),
        "--max-sessions",
        str(max_sessions),
        "--max-chars",
        str(max_chars),
    ]
    if os.environ.get("AUTO_CODEX_ALL_PROJECTS") in {"1", "true", "TRUE", "yes", "YES"}:
        args.append("--all-projects")
    result = _run_auto_codex(*args)
    result["reason"] = reason
    return result


def _lifecycle_if_due(state: dict) -> dict | None:
    every = _int_env("AUTO_CODEX_LIFECYCLE_EVERY_HOURS", DEFAULT_LIFECYCLE_EVERY_HOURS)
    if every <= 0:
        return None
    now = int(time.time())
    last = int(state.get("last_lifecycle_at", 0))
    if now - last < every * 3600:
        return None
    state["last_lifecycle_at"] = now
    return _run_auto_codex(
        "lifecycle",
        "--maturity",
        str(_int_env("AUTO_CODEX_MATURITY", 3)),
        "--capacity",
        str(_int_env("AUTO_CODEX_CAPACITY", 50)),
    )


def _skill_name(event: dict) -> str | None:
    candidates = []
    tool_input = event.get("tool_input")
    if isinstance(tool_input, dict):
        candidates.extend([
            tool_input.get("name"),
            tool_input.get("skill"),
            tool_input.get("skill_name"),
        ])
    for key in ("skill", "skill_name", "name"):
        candidates.append(event.get(key))
    for value in candidates:
        if isinstance(value, str) and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", value):
            return value
    return None


def _count_skill(event: dict) -> dict:
    name = _skill_name(event)
    if not name:
        return {"counted": False, "reason": "missing_skill_name"}
    return _run_auto_codex("count", name)


def dispatch(event: dict) -> dict:
    name = event.get("hook_event_name")
    state_path = _state_path()
    state = _read_json(state_path, {})
    results: list[dict] = []

    if name == "SessionStart":
        results.append(_sync("session_start", small=True))
        lifecycle = _lifecycle_if_due(state)
        if lifecycle:
            results.append(lifecycle)
    elif name == "Stop":
        stops = int(state.get("stop_count", 0)) + 1
        state["stop_count"] = stops
        every = _int_env("AUTO_CODEX_SYNC_EVERY_STOPS", DEFAULT_SYNC_EVERY_STOPS)
        if every and stops % every == 0:
            results.append(_sync("stop", small=True))
    elif name == "PreCompact":
        results.append(_sync("pre_compact", small=False))
    elif name == "PreToolUse":
        results.append(_count_skill(event))
    else:
        return {"ignored": True, "event": name}

    _atomic_write(state_path, json.dumps(state, indent=2, sort_keys=True))
    return {"ok": True, "event": name, "results": results}


def main() -> int:
    try:
        raw = sys.stdin.read().lstrip("\ufeff")
        event = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, ValueError):
        event = {}
    verdict = dispatch(event)
    if os.environ.get("AUTO_CODEX_HOOK_DEBUG") in {"1", "true", "TRUE"}:
        print(json.dumps(verdict, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
