---
name: adaptive-projects
description: Universal adaptive-learning workflow for all Codex project sessions, recurring projects, and applied skills. Use when Codex starts, maintains, summarizes, or transfers any project workflow, including coding, research, automation, data, crawler, app, media, image, writing, analysis, operations, or design work, and should automatically learn project-specific skills via Auto Codex.
---

# Adaptive Projects

Use this skill as the universal entry point for repeatable project work. It decides whether an existing learned skill applies, whether a domain-specific adaptive skill should guide the work, and whether Auto Codex should create or patch a project-level skill afterward.

## Project Routing

1. Identify the project type, workspace, artifacts, tools, user goal, and expected outputs.
2. Check existing project and global skills for a close match before inventing a new workflow.
3. If a more specific adaptive skill applies, use it as the starting pattern.
4. If no specific skill applies, proceed with careful project discovery and let Auto Codex learn after the first meaningful run.

## What To Learn

Capture durable project knowledge such as:

- Repo or workspace structure.
- Commands, scripts, build steps, render steps, data pipelines, or validation checks.
- Output naming, folder layout, file formats, and delivery expectations.
- Domain rules, source priorities, confidence rules, style rules, or acceptance criteria.
- User preferences about verbosity, format, design taste, pacing, examples, or review style.
- Failure recovery, resume/checkpoint patterns, common pitfalls, and QC checklists.

## Workflow

1. Read the local project before acting.
2. Do the concrete task using the best existing skill or local pattern.
3. Verify the output with task-appropriate checks.
4. After meaningful progress, invoke `$auto-codex` to sync the trace and create or patch a project-specific skill.
5. Keep broad reusable lessons in global adaptive skills and repo/domain-specific lessons in project skills.

## Skill Output Rule

Every repeated project should eventually have one concise project-level skill if it develops stable conventions. The skill should help future Codex sessions start with the right commands, files, style, source rules, validation checks, and user expectations.
