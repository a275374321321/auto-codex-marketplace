# Auto Codex

Auto Codex is a Codex plugin that packages adaptive project skills, lifecycle
hooks, and an MCP staging server for self-learning skill maintenance.

## What Runs Automatically

- `SessionStart`: syncs recent Codex session history into learning bundles and
  periodically runs lifecycle pruning.
- `Stop`: every few turns, refreshes learning bundles for the active project.
- `PreCompact`: syncs a fuller bundle before context compaction.
- `PreToolUse`: records usage for self-authored learned skills when skill tool
  events expose a skill name.

Hooks create reflection bundles under `.codex/auto-codex/`. They do not write
learned skills directly.

## MCP Tools

- `stage_skill`: append one validated learning intent to the project queue.
- `drain_skill_intents`: promote queued intents through the deterministic writer.
- `auto_codex_status`: show roots, inbox status, and the current learned skill
  index.

## Install From A Marketplace

For a repo/team marketplace, keep this plugin under `plugins/auto-codex` and
the marketplace entry under `.agents/plugins/marketplace.json`. Users can add
the marketplace root with:

```bash
codex plugin marketplace add <repo-or-local-marketplace-root>
```

Then open the Codex app plugin directory, choose the marketplace, and install
**Auto Codex**. Some Codex CLI builds expose marketplace management before
command-line plugin installation, so the app plugin directory is the most
portable install path.

For workspace-wide sharing in the Codex app, open the installed plugin details
and use Share.

## Tuning

Environment variables:

- `AUTO_CODEX_SYNC_EVERY_STOPS`: default `3`.
- `AUTO_CODEX_SYNC_DAYS`: default `30`.
- `AUTO_CODEX_MAX_SESSIONS`: default `12`.
- `AUTO_CODEX_MAX_CHARS`: default `16000`.
- `AUTO_CODEX_ALL_PROJECTS=1`: scan all recent Codex projects instead of only
  the current working directory.
- `AUTO_CODEX_LIFECYCLE_EVERY_HOURS`: default `24`.
- `AUTO_CODEX_MATURITY`: default `3`.
- `AUTO_CODEX_CAPACITY`: default `50`.
