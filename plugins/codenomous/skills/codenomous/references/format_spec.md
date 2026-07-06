# Codenomous Skill Format

Generated skills are folders with `SKILL.md` and optional resources. The promoter validates these rules before writing.

## Frontmatter

`SKILL.md` must start with YAML frontmatter containing non-empty `name` and `description`. The `description` must say what the skill does and when Codex should use it.

## Resource Paths

Optional intent `files` must be a map of relative path to string content. Allowed top-level directories are:

- `references/`
- `templates/`
- `scripts/`
- `assets/`

Paths must be relative, contain at least two segments, avoid dot segments and backslashes, and use only letters, digits, dot, underscore, and hyphen in each segment. Every carried file must be mentioned by exact relative path in `SKILL.md`.

## Completeness

Generated skill bodies and resources must not contain `TODO`, `FIXME`, `XXX`, or placeholder tokens such as `<NAME>`.

## Project vs Global

Global skills must be repo-agnostic. If a lesson names a local path, workbook, project, customer dataset, or repo-specific convention, create or patch a project skill instead.

## Self-Authored Boundary

`create` stamps `.codenomous.json`. `update`, `patch`, and `delete` are rejected unless that sidecar exists and says `created_by: codenomous`. Legacy `.codex-autoharness.json` sidecars remain readable for migration.

## Auto-Sync Boundary

Historical sync may create trace bundles and inbox entries, but those files are not live skills. A live skill change still requires a JSON intent and promoter validation.
