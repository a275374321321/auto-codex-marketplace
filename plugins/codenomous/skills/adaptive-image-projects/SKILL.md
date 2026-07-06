---
name: adaptive-image-projects
description: Reusable workflow for image editing, photo retouching, p-tu/p图, thumbnails, product images, brand graphics, AI image generation/editing, batch asset preparation, and visual style projects that should adaptively learn via Codenomous.
---

# Adaptive Image Projects

Use this skill when the user works on image editing, photo retouching, p-tu, product visuals, thumbnails, ad graphics, AI-generated images, style variants, or repeatable visual asset pipelines.

## Default Workflow

1. Identify the desired output: size, format, background, subject preservation, style, platform, file naming, and whether transparent assets are needed.
2. Inspect source images and existing brand/project assets when available.
3. Preserve originals. Write edited variants or generated assets to clearly named outputs.
4. Match recurring visual style: composition, colors, typography, crop rules, watermark policy, product visibility, realism level, and retouching strength.
5. For batch image work, test one representative image before processing the full set.
6. After a visual style or asset workflow repeats, invoke Codenomous to create or patch a project-specific image skill.

## Reusable Patterns

- Store brand-specific colors, fonts, logo usage, crop ratios, prompt styles, and export settings in the project skill.
- Treat user corrections on realism, face/body edits, product accuracy, text placement, or color tone as strong learning signals.
- For AI image tasks, keep prompts concise and preserve exact constraints that repeatedly matter.

## Auto-Learning Rule

If image work repeats for a brand, store, campaign, creator, product catalog, or design style, use `$codenomous` to learn the style and workflow into a project-level skill.
