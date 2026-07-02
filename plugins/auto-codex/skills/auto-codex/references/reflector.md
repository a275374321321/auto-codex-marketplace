# Auto Codex Reflector

Distill a finished episode into at most one aligned skill change. Propose an intent; let `scripts/auto_codex.py` validate and write it.

## Inputs

Use the reflection bundle as the source of truth. It contains:

1. A redacted trace window.
2. Existing skill descriptions from project and global layers.
3. The format spec.

Only inspect a live skill body when the index suggests it is a likely patch target.

For auto-sync bundles generated from past Codex sessions, weigh repeated patterns more strongly than isolated messages. Treat thread titles, project paths, and repeated user corrections as clustering signals; avoid creating a skill from a single stale or ambiguous historical exchange.

When summarizing all projects, cluster lessons by:

- Project/workspace path, repo name, output artifact family, or product/domain.
- Applied skill or workflow type, including coding, data work, research, design, media, writing, automation, debugging, operations, or analysis.
- Recurring user preferences, acceptance criteria, validation commands, naming rules, source priorities, and failure recovery patterns.

If a bundle shows a new repeated project category without a project-level skill, create one. If the lesson is broadly reusable across projects, patch a global adaptive skill instead.

## Capture

Capture a durable lesson when:

- The user corrected style, tone, format, workflow, ordering, or tool usage in a way that should recur.
- A reusable technique, debugging path, verification step, script pattern, or data handling rule emerged.
- A loaded or relevant skill proved incomplete, stale, or too narrow.
- A project repeatedly uses the same tools, file structure, output conventions, quality checks, or domain rules.
- A user applies the same skill category across multiple projects and expects the pattern to transfer.

Do not capture:

- One-off task narrative.
- Temporary environment failure.
- Negative claims like "tool X is broken".
- Secrets, credentials, private raw data, or unredacted customer material.
- The assistant's base instructions, sandbox policy text, or generic system/developer messages from session metadata.

## Decision Ladder

Compare first, then choose the earliest rung that fits:

1. Patch a self-authored skill that was in play.
2. Patch a self-authored class-level skill already covering the scenario.
3. Update a self-authored skill with a supporting file when the lesson is detailed backing material.
4. Create a new skill only when no existing skill covers the class of work.

Prefer `project` for repo-specific lessons. Use `global` only for user preferences and general techniques that contain no repo-local identifiers.

## Intent JSON

Return one JSON object, or say that no durable skill change is warranted.

```json
{
  "action": "create",
  "name": "example-skill",
  "level": "project",
  "body": "---\nname: example-skill\ndescription: ...\n---\n\n# Example Skill\n\n...",
  "files": {
    "references/example.md": "Concise backing material"
  },
  "reason": "Why this skill change should exist",
  "evidence": "Verbatim redacted excerpt from the trace"
}
```

For `patch`, use `old_string` and `new_string` instead of `body`. The old string must be unique in the live `SKILL.md`.
