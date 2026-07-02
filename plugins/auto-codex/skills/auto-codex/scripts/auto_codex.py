#!/usr/bin/env python3
"""Auto Codex: deterministic writer for self-authored Codex skills.

The model proposes JSON intents. This script redacts evidence, validates shape,
writes skills atomically, records ledgers, and archives only skills it created.
It intentionally has no third-party dependencies.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

SKILL_FILE = "SKILL.md"
SIDECAR = ".auto-codex.json"
LEGACY_SIDECAR = ".codex-autoharness.json"
CREATED_BY = "auto-codex"
LEGACY_CREATED_BY = {"auto-codex", "codex-autoharness"}
LEDGER = ".ledger.jsonl"
ALLOWED_DIRS = {"references", "templates", "scripts", "assets"}
LAYERS = ("project", "global")

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n?", re.S)
PLACEHOLDER = re.compile(r"\b(TODO|FIXME|XXX)\b|<[A-Z][A-Z0-9_]{2,}>")
ABS_PATH = re.compile(r"(?:/home/|/Users/|/root/)[^\s`)\]]+|[A-Za-z]:\\[^\s`)\]]+")
SUBFILE_REF = re.compile(r"\b(?:references|templates|scripts|assets)/[A-Za-z0-9._/-]+")
SECRET_RULES = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[^'\"\s]+"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
]


def now() -> int:
    return int(time.time())


def project_root() -> Path:
    return Path.cwd() / ".codex"


def global_root() -> Path:
    return Path.home() / ".codex"


def codex_home(args) -> Path:
    return Path(args.codex_home).resolve() if getattr(args, "codex_home", None) else global_root().resolve()


def roots(args) -> dict[str, Path]:
    return {
        "project": Path(args.project_root).resolve() if args.project_root else project_root().resolve(),
        "global": Path(args.global_root).resolve() if args.global_root else global_root().resolve(),
    }


def skills_dir(root: Path) -> Path:
    return root / "skills"


def skill_dir(layer: str, name: str, rs: dict[str, Path]) -> Path:
    check_name(name)
    return skills_dir(rs[layer]) / name


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def redact(text: str) -> str:
    out = text
    for rule in SECRET_RULES:
        out = rule.sub("[REDACTED]", out)
    return out


def check_name(name: str) -> None:
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", name):
        raise ValueError(f"invalid skill name: {name!r}")


def check_subfile(rel: str) -> None:
    if not isinstance(rel, str) or "\\" in rel or rel.startswith("/") or ":" in rel:
        raise ValueError(f"invalid subfile path: {rel!r}")
    parts = rel.split("/")
    if len(parts) < 2 or parts[0] not in ALLOWED_DIRS:
        raise ValueError(f"subfile must live under {sorted(ALLOWED_DIRS)}: {rel}")
    for part in parts:
        if part in {"", ".", ".."} or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", part):
            raise ValueError(f"invalid subfile segment in {rel!r}")


def frontmatter(body: str) -> dict[str, str] | None:
    match = FRONTMATTER.match(body or "")
    if not match:
        return None
    data = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip().strip("\"'")
    return data


def validate_body(intent: dict, body: str | None, layer: str, repo_name: str | None, base: Path) -> list[list[str]]:
    findings: list[list[str]] = []
    files = intent.get("files") or {}
    if body is None:
        return findings

    fm = frontmatter(body)
    if not fm or not fm.get("name") or not fm.get("description"):
        findings.append(["structure", "SKILL.md needs frontmatter with name and description"])
    elif fm["name"] != intent.get("name"):
        findings.append(["structure", "frontmatter name must match intent name"])

    if PLACEHOLDER.search(body):
        findings.append(["completeness", "body contains TODO/FIXME/placeholder text"])

    if not isinstance(files, dict):
        findings.append(["files", "files must be an object"])
        files = {}

    for rel, content in files.items():
        try:
            check_subfile(rel)
        except ValueError as exc:
            findings.append(["files", str(exc)])
        if not isinstance(content, str):
            findings.append(["files", f"{rel}: content must be a string"])
        elif PLACEHOLDER.search(content):
            findings.append(["completeness", f"{rel}: contains placeholder text"])
        if isinstance(rel, str) and rel not in body:
            findings.append(["structure", f"carried subfile {rel} is not referenced in SKILL.md"])

    for ref in set(SUBFILE_REF.findall(body)):
        if ref.startswith("references/evidence-"):
            continue
        if ref not in files and not (base / ref).is_file():
            findings.append(["structure", f"referenced {ref} is neither carried nor live"])

    if layer == "global":
        markers = ABS_PATH.findall(body)
        if repo_name and repo_name in body:
            markers.append(repo_name)
        for content in files.values():
            if isinstance(content, str):
                markers.extend(ABS_PATH.findall(content))
                if repo_name and repo_name in content:
                    markers.append(repo_name)
        if markers:
            findings.append(["global_repo_agnostic", "global skill contains repo-local markers"])
    return findings


def is_self_authored(path: Path) -> bool:
    meta = read_json(path / SIDECAR, {})
    if meta.get("created_by") in LEGACY_CREATED_BY:
        return True
    legacy = read_json(path / LEGACY_SIDECAR, {})
    return legacy.get("created_by") in LEGACY_CREATED_BY


def find_skill(name: str, rs: dict[str, Path]) -> tuple[str, Path]:
    hits = []
    for layer in LAYERS:
        path = skill_dir(layer, name, rs)
        if (path / SKILL_FILE).is_file():
            hits.append((layer, path))
    if not hits:
        raise ValueError(f"skill not found: {name}")
    if len(hits) > 1:
        raise ValueError(f"ambiguous skill in layers: {', '.join(x[0] for x in hits)}")
    return hits[0]


def shape(intent: dict, rs: dict[str, Path]) -> tuple[str, Path, str | None]:
    action = intent.get("action")
    name = intent.get("name")
    check_name(name)
    if action == "create":
        layer = intent.get("level")
        if layer not in LAYERS:
            raise ValueError("create requires level: project or global")
        return layer, skill_dir(layer, name, rs), intent.get("body")
    layer, path = find_skill(name, rs)
    if action == "update":
        return layer, path, intent.get("body")
    if action == "patch":
        body = (path / SKILL_FILE).read_text(encoding="utf-8")
        old = intent.get("old_string")
        new = intent.get("new_string")
        if not old or not isinstance(new, str):
            raise ValueError("patch requires old_string and new_string")
        if body.count(old) != 1:
            raise ValueError("old_string must match live body exactly once")
        return layer, path, body.replace(old, new)
    if action == "delete":
        return layer, path, None
    raise ValueError(f"unknown action: {action!r}")


def materialize_evidence(path: Path, evidence: str) -> str:
    text = redact(evidence or "")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
    rel = f"references/evidence-{digest}.md"
    target = path / rel
    if not target.exists():
        atomic_write(target, text)
    return rel


def append_ledger(path: Path, entry: dict) -> None:
    path.mkdir(parents=True, exist_ok=True)
    with (path / LEDGER).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")


def land_files(path: Path, files: dict | None) -> None:
    if not files:
        return
    base = path.resolve()
    for rel, content in files.items():
        check_subfile(rel)
        target = (path / rel).resolve()
        if not target.is_relative_to(base):
            raise ValueError(f"subfile escapes skill dir: {rel}")
        atomic_write(target, content)


def archive(path: Path) -> Path:
    dest_root = path.parent / ".archive"
    dest_root.mkdir(parents=True, exist_ok=True)
    dest = dest_root / f"{path.name}-{now()}"
    shutil.move(str(path), str(dest))
    return dest


def promote(intent: dict, rs: dict[str, Path], repo_name: str | None = None) -> dict:
    action = intent.get("action")
    try:
        layer, path, body = shape(intent, rs)
        if action != "create" and not is_self_authored(path):
            raise ValueError("target is not self-authored by Auto Codex")
        if action in {"create", "update"} and not isinstance(body, str):
            raise ValueError(f"{action} requires body")
        if not (intent.get("reason") or "").strip() or not (intent.get("evidence") or "").strip():
            raise ValueError("intent requires reason and evidence")
        findings = validate_body(intent, body, layer, repo_name, path)
        if findings:
            return {"ok": False, "action": action, "level": layer, "findings": findings}
        if action == "delete":
            ev = materialize_evidence(path, intent["evidence"])
            append_ledger(path, {"ts": now(), "action": action, "reason": intent["reason"], "evidence": ev})
            archived = archive(path)
            return {"ok": True, "action": action, "level": layer, "archived": str(archived)}
        land_files(path, intent.get("files"))
        ev = materialize_evidence(path, intent["evidence"])
        atomic_write(path / SKILL_FILE, body)
        if action == "create":
            atomic_write(path / SIDECAR, json.dumps({"created_by": CREATED_BY, "created_at": now()}, indent=2))
        append_ledger(path, {"ts": now(), "action": action, "reason": intent["reason"], "evidence": ev})
        return {"ok": True, "action": action, "level": layer, "path": str(path)}
    except Exception as exc:
        return {"ok": False, "action": action, "findings": [["error", str(exc)]]}


def skill_index(rs: dict[str, Path]) -> str:
    lines = []
    for layer in LAYERS:
        root = skills_dir(rs[layer])
        if not root.exists():
            continue
        for skill in sorted(root.glob(f"*/{SKILL_FILE}")):
            fm = frontmatter(skill.read_text(encoding="utf-8", errors="replace")) or {}
            name = fm.get("name") or skill.parent.name
            desc = fm.get("description") or "(missing description)"
            marker = " self-authored" if is_self_authored(skill.parent) else ""
            lines.append(f"{name} [{layer}{marker}]: {desc}")
    return "\n".join(lines) if lines else "(no live skills yet)"


def queue_path(run_id: str, rs: dict[str, Path]) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", run_id)
    return rs["project"] / "auto-codex" / "intents" / f"{safe}.jsonl"


def cmd_index(args) -> int:
    print(skill_index(roots(args)))
    return 0


def cmd_bundle(args) -> int:
    trace = Path(args.trace).read_text(encoding="utf-8", errors="replace")
    base = Path(__file__).resolve().parents[1]
    spec = (base / "references" / "format_spec.md").read_text(encoding="utf-8")
    reflector = (base / "references" / "reflector.md").read_text(encoding="utf-8")
    text = (
        "# Redacted Episode Trace\n\n" + redact(trace).strip()
        + "\n\n# Existing Skills\n\n" + skill_index(roots(args))
        + "\n\n# Format Spec\n\n" + spec
        + "\n\n# Reflector Instructions\n\n" + reflector
    )
    atomic_write(Path(args.out), text)
    print(args.out)
    return 0


def load_intent(path: str | None) -> dict:
    raw = sys.stdin.read() if not path or path == "-" else Path(path).read_text(encoding="utf-8")
    raw = raw.lstrip("\ufeff")
    return json.loads(raw)


def cmd_promote(args) -> int:
    result = promote(load_intent(args.intent), roots(args), repo_name=args.repo_name)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


def cmd_stage(args) -> int:
    q = queue_path(args.run_id, roots(args))
    q.parent.mkdir(parents=True, exist_ok=True)
    intent = load_intent(args.intent)
    with q.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(intent, ensure_ascii=False) + "\n")
    print(str(q))
    return 0


def cmd_drain(args) -> int:
    rs = roots(args)
    q = queue_path(args.run_id, rs)
    verdicts = []
    if q.exists():
        for line in q.read_text(encoding="utf-8").splitlines():
            if line.strip():
                verdicts.append(promote(json.loads(line), rs, repo_name=args.repo_name))
        q.unlink()
    print(json.dumps(verdicts, ensure_ascii=False, indent=2))
    return 0 if all(v.get("ok") for v in verdicts) else 1


def cmd_count(args) -> int:
    layer, path = find_skill(args.name, roots(args))
    if not is_self_authored(path):
        print(json.dumps({"counted": False, "reason": "not_self_authored"}))
        return 0
    meta = read_json(path / SIDECAR, {})
    meta["created_by"] = CREATED_BY
    meta["calls"] = int(meta.get("calls", 0)) + 1
    meta["last_called_at"] = now()
    atomic_write(path / SIDECAR, json.dumps(meta, indent=2, sort_keys=True))
    print(json.dumps({"counted": True, "layer": layer, "calls": meta["calls"]}))
    return 0


def cmd_lifecycle(args) -> int:
    rs = roots(args)
    archived = []
    for layer in LAYERS:
        members = []
        root = skills_dir(rs[layer])
        if not root.exists():
            continue
        for sidecar in root.glob(f"*/{SIDECAR}"):
            meta = read_json(sidecar, {})
            if meta.get("created_by") in LEGACY_CREATED_BY:
                members.append((int(meta.get("calls", 0)), sidecar.parent))
        mature = [m for m in members if m[0] >= args.maturity]
        if len(mature) > args.capacity:
            for _, path in sorted(mature)[: len(mature) - args.capacity]:
                archived.append(str(archive(path)))
    print(json.dumps({"archived": archived}, indent=2))
    return 0


def _session_id_from_path(path: Path) -> str:
    match = re.search(r"([0-9a-f]{8}-[0-9a-f-]{27,})", path.name, re.I)
    return match.group(1) if match else path.stem


def _message_text(record: dict) -> tuple[str | None, str | None]:
    typ = record.get("type")
    payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
    if typ == "session_meta":
        return None, None
    if typ == "user_message":
        text = payload.get("message") or payload.get("text")
        return ("user", text) if isinstance(text, str) else (None, None)
    if typ == "agent_message":
        text = payload.get("message") or payload.get("text")
        return ("assistant", text) if isinstance(text, str) else (None, None)
    if typ == "response_item" and payload.get("type") == "message":
        role = payload.get("role")
        if role not in {"user", "assistant"}:
            return None, None
        parts = []
        for item in payload.get("content") or []:
            if isinstance(item, dict):
                text = item.get("text") or item.get("input_text")
                if isinstance(text, str):
                    parts.append(text)
        if role and parts:
            return role, "\n".join(parts)
    return None, None


def _session_summary(path: Path, cwd_filter: Path | None, max_chars: int) -> dict | None:
    session_id = _session_id_from_path(path)
    cwd = None
    chunks = []
    updated = path.stat().st_mtime
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("type") == "session_meta":
                payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
                if isinstance(payload.get("cwd"), str):
                    cwd = payload["cwd"]
                continue
            role, text = _message_text(record)
            if role and text:
                clean = redact(text.strip())
                if clean:
                    chunks.append(f"{role}: {clean}")
            if sum(len(c) for c in chunks) >= max_chars:
                break
    if cwd_filter and cwd:
        try:
            if Path(cwd).resolve() != cwd_filter.resolve():
                return None
        except OSError:
            return None
    if not chunks:
        return None
    return {
        "session_id": session_id,
        "path": str(path),
        "cwd": cwd,
        "updated": updated,
        "trace": "\n\n".join(chunks)[:max_chars],
    }


def _load_seen(path: Path) -> dict:
    return read_json(path, {})


def _write_bundle(summary: dict, out_dir: Path, rs: dict[str, Path]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", summary["session_id"])
    trace_path = out_dir / f"{safe}.trace.md"
    bundle_path = out_dir / f"{safe}.bundle.md"
    atomic_write(trace_path, summary["trace"])
    base = Path(__file__).resolve().parents[1]
    spec = (base / "references" / "format_spec.md").read_text(encoding="utf-8")
    reflector = (base / "references" / "reflector.md").read_text(encoding="utf-8")
    body = (
        "# Redacted Episode Trace\n\n" + summary["trace"].strip()
        + "\n\n# Existing Skills\n\n" + skill_index(rs)
        + "\n\n# Format Spec\n\n" + spec
        + "\n\n# Reflector Instructions\n\n" + reflector
    )
    atomic_write(bundle_path, body)
    return bundle_path


def cmd_sync(args) -> int:
    home = codex_home(args)
    sessions = home / "sessions"
    rs = roots(args)
    state_dir = rs["project"] / "auto-codex"
    state_path = state_dir / "sync_state.json"
    seen = {} if args.rescan else _load_seen(state_path)
    cutoff = time.time() - args.days * 86400
    cwd_filter = None if args.all_projects else Path.cwd().resolve()
    out_dir = state_dir / "bundles"
    created = []

    if not sessions.exists():
        print(json.dumps({"ok": False, "error": f"missing sessions dir: {sessions}"}, indent=2))
        return 1

    candidates = sorted(sessions.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in candidates:
        if len(created) >= args.max_sessions:
            break
        mtime = path.stat().st_mtime
        if mtime < cutoff:
            continue
        key = str(path)
        if seen.get(key) == mtime:
            continue
        summary = _session_summary(path, cwd_filter, args.max_chars)
        seen[key] = mtime
        if not summary:
            continue
        bundle = _write_bundle(summary, out_dir, rs)
        created.append({"session_id": summary["session_id"], "cwd": summary["cwd"], "bundle": str(bundle)})

    atomic_write(state_path, json.dumps(seen, indent=2, sort_keys=True))
    inbox = state_dir / "learning_inbox.md"
    lines = [
        "# Auto Codex Learning Inbox",
        "",
        "Review these bundles with references/reflector.md, then promote at most one durable intent per bundle.",
        "",
    ]
    for item in created:
        lines.append(f"- `{item['session_id']}`: `{item['bundle']}`")
    atomic_write(inbox, "\n".join(lines) + "\n")
    print(json.dumps({"ok": True, "created": created, "inbox": str(inbox)}, indent=2))
    return 0


def cmd_install_task(args) -> int:
    script_dir = roots(args)["project"] / "auto-codex"
    script_dir.mkdir(parents=True, exist_ok=True)
    script_path = script_dir / "run_auto_codex_sync.ps1"
    py = Path(__file__).resolve()
    workspace = py.parents[2]
    project_state = workspace / ".codex"
    interval = max(args.minutes, 15)
    ps = f"""$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath {json.dumps(str(workspace))}
python {json.dumps(str(py))} sync --project-root {json.dumps(str(project_state))} --codex-home {json.dumps(str(codex_home(args)))} --days {args.days} --max-sessions {args.max_sessions}
"""
    atomic_write(script_path, ps)
    task_name = args.task_name
    command = (
        f'schtasks /Create /TN "{task_name}" /SC MINUTE /MO {interval} '
        f'/TR "powershell -NoProfile -ExecutionPolicy Bypass -File ""{script_path}""" /F'
    )
    print(json.dumps({"ok": True, "script": str(script_path), "install_command": command}, indent=2))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--project-root", help="Project .codex root; default: cwd/.codex")
    common.add_argument("--global-root", help="Global .codex root; default: ~/.codex")
    common.add_argument("--codex-home", help="Codex home for sessions; default: ~/.codex")
    sub = parser.add_subparsers(required=True)

    p = sub.add_parser("index", parents=[common])
    p.set_defaults(func=cmd_index)

    p = sub.add_parser("bundle", parents=[common])
    p.add_argument("--trace", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_bundle)

    p = sub.add_parser("promote", parents=[common])
    p.add_argument("--intent", default="-")
    p.add_argument("--repo-name")
    p.set_defaults(func=cmd_promote)

    p = sub.add_parser("stage", parents=[common])
    p.add_argument("--run-id", required=True)
    p.add_argument("--intent", default="-")
    p.set_defaults(func=cmd_stage)

    p = sub.add_parser("drain", parents=[common])
    p.add_argument("--run-id", required=True)
    p.add_argument("--repo-name")
    p.set_defaults(func=cmd_drain)

    p = sub.add_parser("count", parents=[common])
    p.add_argument("name")
    p.set_defaults(func=cmd_count)

    p = sub.add_parser("lifecycle", parents=[common])
    p.add_argument("--maturity", type=int, default=3)
    p.add_argument("--capacity", type=int, default=50)
    p.set_defaults(func=cmd_lifecycle)

    p = sub.add_parser("sync", parents=[common])
    p.add_argument("--days", type=int, default=14)
    p.add_argument("--max-sessions", type=int, default=8)
    p.add_argument("--max-chars", type=int, default=20000)
    p.add_argument("--all-projects", action="store_true")
    p.add_argument("--rescan", action="store_true")
    p.set_defaults(func=cmd_sync)

    p = sub.add_parser("install-task", parents=[common])
    p.add_argument("--minutes", type=int, default=60)
    p.add_argument("--days", type=int, default=14)
    p.add_argument("--max-sessions", type=int, default=8)
    p.add_argument("--task-name", default="AutoCodexSync")
    p.set_defaults(func=cmd_install_task)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
