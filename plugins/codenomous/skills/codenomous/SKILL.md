---
name: codenomous
description: Codenomous self-learning skill maintenance for Codex. Use at the start of recurring project work, when a user asks Codex to automatically learn from sessions, sync project history and habits, summarize all projects and applied skills, distill recurring workflow lessons into Codex skills, update or prune self-authored skills, compare existing skill descriptions, or work on any project that should adaptively learn from prior runs.
---

# Codenomous

Use this skill to maintain a bounded, self-authored Codex skill layer from real work. The design is adapted from tigerless-labs/autoharness and, when installed through the Codenomous plugin, combines Codex lifecycle hooks, history sync, an MCP staging tool, and a deterministic local writer.

## Workflow

1. Capture the episode trace from the current conversation, a log file, or a concise user-provided summary.
2. Run `scripts/codenomous.py bundle --trace <trace-file> --out <bundle-file>` to assemble a redacted reflection bundle with the existing skill index and authoring rules.
3. Read `references/reflector.md`, then produce at most one JSON intent. Prefer patching an existing skill before creating a new one.
4. Stage or promote the intent through the script. Do not write learned skills directly unless the user explicitly asks for a manual override.
5. Run lifecycle pruning periodically with `scripts/codenomous.py lifecycle`; it archives mature low-use self-authored skills and never deletes them.

## Automatic Sync

Use `scripts/codenomous.py sync` to scan recent Codex session history from `~/.codex/sessions`, filter it to the current project by default, redact sensitive text, and write reflection bundles under `.codex/codenomous/bundles/`.

When installed as the Codenomous plugin, bundled hooks run this sync automatically on `SessionStart`, periodically on `Stop`, and before compaction. The plugin MCP server exposes `stage_skill`, `drain_skill_intents`, and `codenomous_status` so Codex can stage and promote learned skills through the same deterministic validator.

Use `scripts/codenomous.py install-task` on Windows to generate a PowerShell sync script and a `schtasks` command. The scheduled task automates history scanning and learning-bundle creation; a Codex session still reviews each bundle and emits a validated intent before skills are changed.

Prefer this automation policy:

- Auto-sync historical traces and lifecycle pruning through hooks.
- Auto-stage only after a model reflection has produced an intent, preferably through the plugin MCP `stage_skill` tool.
- Auto-promote only through `promote`, `drain`, or MCP `drain_skill_intents`, never through direct file edits.
- Keep project-specific habits in project skills and user-wide preferences in global skills.
- For any new or recurring project, check whether a similar learned skill exists. If none exists, let Codenomous create a project-level skill after the first meaningful run, then patch it as the workflow evolves.
- Summarize learning by project and by applied skill. A durable project skill should capture the repo/workspace conventions, recurring commands, output formats, user preferences, validation steps, and pitfalls that will matter in future similar work.

## Intent Contract

The model proposes only JSON. The script is the only writer.

Use one of these actions:

- `create`: needs `name`, `level`, `body`, `reason`, `evidence`, optional `files`.
- `update`: needs `name`, `body`, `reason`, `evidence`, optional `files`; target must be self-authored.
- `patch`: needs `name`, `old_string`, `new_string`, `reason`, `evidence`; target must be self-authored and `old_string` must match once.
- `delete`: needs `name`, `reason`, `evidence`; archives the target if it is self-authored.

`level` is `project` for repo-specific skills under `<repo>/.codex/skills/`, or `global` for repo-agnostic skills under `~/.codex/skills/`.

## Safety Rules

- Compare against both project and global skill indexes before creating a new skill.
- Keep skill names class-level: no row numbers, issue IDs, dates, transient error strings, or one-off task names.
- Never modify skills that lack the `.codenomous.json` self-authored sidecar. Legacy `.codex-autoharness.json` sidecars remain readable for migration.
- Put evidence in the intent as a real excerpt from the trace; the script redacts and stores it as `references/evidence-*.md`.
- Keep generated `SKILL.md` bodies concise. Move detailed examples into `references/` and mention every carried file path in `SKILL.md`.
- Do not encode temporary failures as permanent rules. Capture the reusable fix or workflow pattern instead.

## Resources

- `scripts/codenomous.py`: local harness for bundle creation, intent staging, deterministic promotion, ledger writes, skill indexing, call accounting, and lifecycle archiving.
- `references/reflector.md`: the prompt/procedure Codex should follow when distilling an episode into one skill change.
- `references/format_spec.md`: the validation rules enforced by the script for generated Codex skills.
