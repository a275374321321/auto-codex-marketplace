---
name: adaptive-video-projects
description: Reusable workflow for video editing, short-form clips, subtitles, thumbnails, timelines, social media cuts, batch rendering, ffmpeg automation, and creative post-production projects that should adaptively learn via Codenomous.
---

# Adaptive Video Projects

Use this skill when the user works on video editing, clip production, subtitles, reels, thumbnails, batch rendering, or repeatable post-production workflows. Capture the creative brief, output platform, source assets, edit style, and render requirements.

## Default Workflow

1. Identify the deliverable: platform, aspect ratio, duration, resolution, codec, language, subtitle style, audio treatment, and naming convention.
2. Inspect source files and existing scripts/project files before proposing edits.
3. Use deterministic tooling such as ffmpeg or project-specific scripts for repeatable transforms. Preserve original media and write new outputs.
4. Keep edit decisions traceable: cuts, captions, overlays, color/audio adjustments, and export settings should be documented or encoded in scripts.
5. Run a short sample render before batch rendering long outputs.
6. After a style, template, or platform workflow repeats, invoke Codenomous to create or patch a project-specific video skill.

## Reusable Patterns

- Maintain reusable presets for aspect ratios, subtitle placement, bitrate, loudness, naming, and export folders.
- Store recurring brand or channel style rules in a project skill, not in one-off instructions.
- Treat user feedback on pacing, tone, subtitle density, thumbnail style, or platform format as a strong learning signal.

## Auto-Learning Rule

If video work repeats for a channel, campaign, creator, product, or platform, use `$codenomous` to learn the house style and render workflow into a project-level skill.
