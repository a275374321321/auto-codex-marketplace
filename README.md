# Auto Codex Marketplace

This repository is a Codex plugin marketplace for Auto Codex.

## Install

```bash
codex plugin marketplace add <this-repo-url>
```

Then open the Codex app plugin directory, choose the `auto-codex-public`
marketplace, and install **Auto Codex**.

After installing, restart Codex and review/trust the plugin hooks with `/hooks`.

## Contents

- `.agents/plugins/marketplace.json`: marketplace catalog.
- `plugins/auto-codex`: Auto Codex plugin package.

Auto Codex syncs recent Codex session history into learning bundles, exposes MCP
tools for staging/promoting learning intents, and packages adaptive skills that
Codex can apply automatically on similar future projects.
