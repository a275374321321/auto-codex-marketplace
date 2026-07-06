#!/usr/bin/env python3
"""MCP stdio server exposing Codenomous learning-intent tools.

The server has no third-party dependencies. It stages intents into Codenomous's
queue and can drain that queue through the deterministic promoter.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True


PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "codenomous_stage_skill"
SERVER_VERSION = "0.1.0"
TOOL_STAGE = "stage_skill"
TOOL_DRAIN = "drain_skill_intents"
TOOL_STATUS = "codenomous_status"
ACTIONS = ("create", "update", "patch", "delete")
BODY_ACTIONS = ("create", "update")


def _plugin_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_codenomous():
    path = _plugin_root() / "skills" / "codenomous" / "scripts" / "codenomous.py"
    spec = importlib.util.spec_from_file_location("codenomous_runtime", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load Codenomous runtime from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _project_root() -> Path:
    return Path.cwd().resolve() / ".codex"


def _global_root() -> Path:
    return Path.home().resolve() / ".codex"


def _roots(runtime) -> dict[str, Path]:
    class Args:
        project_root = str(_project_root())
        global_root = str(_global_root())

    return runtime.roots(Args())


def _run_id(raw: str | None = None) -> str:
    value = raw or os.environ.get("CODENOMOUS_RUN_ID") or f"mcp-{int(time.time())}"
    return re.sub(r"[^A-Za-z0-9_.-]", "_", value)[:120] or "mcp"


def _schema_errors(params: dict) -> list[list[str]]:
    action = params.get("action")
    errors: list[list[str]] = []
    if action not in ACTIONS:
        errors.append(["schema", f"action must be one of {ACTIONS}"])
    if not isinstance(params.get("name"), str) or not params["name"].strip():
        errors.append(["schema", "name is required"])
    if not isinstance(params.get("reason"), str) or not params["reason"].strip():
        errors.append(["schema", "reason is required"])
    if not isinstance(params.get("evidence"), str) or not params["evidence"].strip():
        errors.append(["schema", "evidence is required"])

    has_body = params.get("body") is not None
    has_delta = params.get("old_string") is not None or params.get("new_string") is not None
    has_files = params.get("files") is not None

    if action in BODY_ACTIONS:
        if not has_body:
            errors.append(["schema", f"{action} requires body"])
        if has_delta:
            errors.append(["schema", f"{action} uses body, not old_string/new_string"])
        if has_files and not isinstance(params.get("files"), dict):
            errors.append(["schema", "files must be an object"])
        if action == "create" and params.get("level", "project") not in {"project", "global"}:
            errors.append(["schema", "level must be project or global"])
    elif action == "patch":
        if has_body or has_files:
            errors.append(["schema", "patch uses old_string/new_string and no files"])
        if not isinstance(params.get("old_string"), str) or not isinstance(params.get("new_string"), str):
            errors.append(["schema", "patch requires old_string and new_string"])
    elif action == "delete":
        if has_body or has_delta or has_files:
            errors.append(["schema", "delete takes no body, delta, or files"])
    return errors


def _intent(params: dict) -> dict:
    action = params["action"]
    out = {
        "action": action,
        "name": params["name"],
        "reason": params["reason"],
        "evidence": params["evidence"],
    }
    if action == "create":
        out["level"] = params.get("level", "project")
    if action in BODY_ACTIONS:
        out["body"] = params["body"]
        if params.get("files"):
            out["files"] = params["files"]
    if action == "patch":
        out["old_string"] = params["old_string"]
        out["new_string"] = params["new_string"]
    return out


def stage_skill(params: dict) -> dict:
    runtime = _load_codenomous()
    errors = _schema_errors(params)
    if errors:
        return {"ok": False, "errors": errors}
    intent = _intent(params)
    rs = _roots(runtime)
    try:
        runtime.shape(intent, rs)
        layer, path, body = runtime.shape(intent, rs)
        findings = runtime.validate_body(intent, body, layer, Path.cwd().name, path)
        if findings:
            return {"ok": False, "errors": findings}
        run_id = _run_id(params.get("run_id"))
        q = runtime.queue_path(run_id, rs)
        q.parent.mkdir(parents=True, exist_ok=True)
        with q.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(intent, ensure_ascii=False) + "\n")
        return {"ok": True, "run_id": run_id, "queue": str(q), "intent": intent}
    except Exception as exc:
        return {"ok": False, "errors": [["stage", f"{type(exc).__name__}: {exc}"]]}


def drain_skill_intents(params: dict) -> dict:
    runtime = _load_codenomous()
    rs = _roots(runtime)
    run_id = _run_id(params.get("run_id"))
    q = runtime.queue_path(run_id, rs)
    verdicts = []
    try:
        if q.exists():
            for line in q.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    verdicts.append(runtime.promote(json.loads(line), rs, repo_name=Path.cwd().name))
            q.unlink()
        return {"ok": all(v.get("ok") for v in verdicts), "run_id": run_id, "verdicts": verdicts}
    except Exception as exc:
        return {"ok": False, "run_id": run_id, "errors": [["drain", f"{type(exc).__name__}: {exc}"]]}


def status(_: dict) -> dict:
    runtime = _load_codenomous()
    rs = _roots(runtime)
    inbox = rs["project"] / "codenomous" / "learning_inbox.md"
    return {
        "ok": True,
        "project_root": str(rs["project"]),
        "global_root": str(rs["global"]),
        "learning_inbox": str(inbox),
        "learning_inbox_exists": inbox.exists(),
        "skills": runtime.skill_index(rs),
    }


def _tools() -> list[dict]:
    return [
        {
            "name": TOOL_STAGE,
            "description": "Stage one Codenomous skill-change intent. This appends to a queue and never writes live skills directly.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": list(ACTIONS)},
                    "name": {"type": "string"},
                    "level": {"type": "string", "enum": ["project", "global"]},
                    "body": {"type": "string"},
                    "old_string": {"type": "string"},
                    "new_string": {"type": "string"},
                    "reason": {"type": "string"},
                    "evidence": {"type": "string"},
                    "files": {"type": "object", "additionalProperties": {"type": "string"}},
                    "run_id": {"type": "string"}
                },
                "required": ["action", "name", "reason", "evidence"]
            }
        },
        {
            "name": TOOL_DRAIN,
            "description": "Promote staged Codenomous intents through the deterministic validator/writer.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "run_id": {"type": "string"}
                }
            }
        },
        {
            "name": TOOL_STATUS,
            "description": "Show Codenomous roots, inbox status, and current learned skill index.",
            "inputSchema": {"type": "object", "properties": {}}
        }
    ]


def _ok(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _err(req_id, code, message):
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def handle(request: dict) -> dict | None:
    method = request.get("method")
    req_id = request.get("id")
    if method == "initialize":
        return _ok(req_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        })
    if method == "tools/list":
        return _ok(req_id, {"tools": _tools()})
    if method == "tools/call":
        params = request.get("params") or {}
        name = params.get("name")
        args = params.get("arguments") or {}
        if name == TOOL_STAGE:
            result = stage_skill(args)
        elif name == TOOL_DRAIN:
            result = drain_skill_intents(args)
        elif name == TOOL_STATUS:
            result = status(args)
        else:
            return _err(req_id, -32602, f"unknown tool: {name}")
        return _ok(req_id, {
            "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
            "isError": not result.get("ok", False),
        })
    if req_id is None:
        return None
    return _err(req_id, -32601, f"method not found: {method}")


def serve() -> None:
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            response = handle(json.loads(raw.lstrip("\ufeff")))
        except Exception as exc:
            response = _err(None, -32603, f"{type(exc).__name__}: {exc}")
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    serve()
