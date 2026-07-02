---
name: adaptive-crawler-projects
description: Reusable workflow for crawler, scraping, data-enrichment, identity-verification, retry-only repair, checkpointed batch processing, and quality-control projects. Use when Codex starts or maintains a project similar to EPC verification crawlers, website enrichment, BBB/Yelp/ENF/SolarReviews-style source checks, or any recurring extraction pipeline that should adaptively learn via Auto Codex.
---

# Adaptive Crawler Projects

Use this skill when a project has recurring crawler, scraping, enrichment, verification, or repair-pass patterns. Start with the local project context, then let Auto Codex create a project-specific skill after the first meaningful run.

## Default Workflow

1. Inspect the input schema, output expectations, existing scripts, logs, and partial workbooks before changing code.
2. Design the crawler as a resumable batch job with checkpoint saves, separate run/error logs, and per-row exception handling.
3. Preserve original identifiers and source fields unless the user explicitly requests overwrites. Prefer new fields such as `New xxx`, status columns, confidence columns, and notes.
4. Treat search results and directory pages as leads. Fill verified fields only after source identity is supported by evidence such as phone, domain, address, city, ZIP, name, slug, or official-page links.
5. Run one known-good row and one known-failure row before any full batch.
6. After the first real run, invoke Auto Codex to sync the project trace and create or patch a project-specific skill.

## Reusable Patterns

- Use retry-only passes for failures such as missing website, no usable website, could not fetch, weak identity, or review not found.
- Save repaired results to a new versioned output file instead of overwriting good rows.
- Keep confidence, fetch method, provider, and failure reason visible in notes so QC can focus on weak rows.
- Separate platform ratings from customer review ratings when a source has both.
- Archive or skip bad rows instead of stopping the batch.

## Auto-Learning Rule

If the project repeats across more than one session or develops domain-specific source rules, use `$auto-codex` to create a project-level skill. Keep broadly reusable crawler practices here and put domain-specific evidence rules in the new project skill.
