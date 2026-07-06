---
name: adaptive-app-projects
description: Reusable workflow for app, website, frontend, mobile, dashboard, game, or interactive tool projects that should adaptively learn from prior implementation, design, testing, build, and deployment sessions. Use when Codex starts or maintains an app-like project and should later create a project-specific skill via Codenomous.
---

# Adaptive App Projects

Use this skill when a project involves building or maintaining an app, website, dashboard, mobile prototype, game, or interactive tool. Start with the repo's existing architecture and user-facing workflow, then let Codenomous create a project-specific skill after patterns emerge.

## Default Workflow

1. Inspect the stack, package scripts, routes, component conventions, styling system, test commands, and existing product behavior before editing.
2. Preserve the current design language unless the user asks for a redesign. Match spacing, controls, typography scale, density, and interaction patterns.
3. Build the usable experience first, not a marketing shell, unless the request is explicitly for a landing page.
4. Keep feature work scoped to the requested user journey, but include expected states such as loading, empty, error, disabled, success, and mobile layouts.
5. Run available syntax, build, lint, test, or smoke checks. For visual or interactive work, verify the screen or asset renders as intended when tools are available.
6. After the first meaningful implementation cycle, invoke Codenomous to sync the trace and create or patch a project-specific app skill.

## Reusable Patterns

- Keep project-specific UI rules, API contracts, commands, routing conventions, and asset choices in the project skill.
- Keep broad app-building habits here, such as reading the codebase first, testing real workflows, and preserving user data.
- When a bug fix reveals a durable local pattern, patch the project skill instead of relying on memory.

## Auto-Learning Rule

If the app project repeats across sessions or develops a stable product style, use `$codenomous` to create a project-level skill that captures stack commands, design conventions, testing workflow, and known pitfalls.
