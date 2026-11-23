---
description: learned preferences, project conventions, and Do-Not-Repeat rules
budget_tokens: 2000
---
# Cerebrum

> OpenWolf's learning memory. Updated automatically as the AI learns from interactions.
> Do not edit manually unless correcting an error.
> Last updated: 2026-11-23

## User Preferences

<!-- How the user likes things done. Code style, tools, patterns, communication. -->
- [2026-11-23] Tamair wants a mobile UX overhaul of player + ref screens but KEEP the current big, high-contrast drunk-proof look.
- [2026-11-23] Commit as Tamair (repo git identity), no Claude author or co-author lines.

## Key Learnings

- **Project:** pub-crawl
- **Description:** Pub Crawl web app (Angular 21 SPA + Flask API + host MariaDB), live at crawl.tamairnv.co.uk. Facts in AGENT.md; roadmap ../docs/02-upgrade-plan.md.

## Do-Not-Repeat

<!-- Mistakes made and corrected. Each entry prevents the same mistake recurring. -->
<!-- Format: [YYYY-MM-DD] Description of what went wrong and what to do instead. -->
- [2026-11-23] Edits were made live on the server and left uncommitted for weeks while a Mac copy diverged. Commit on main here; one repo only.
- [2026-11-14] tar backups of this folder fail on the unreadable Tailscale *.key: always --exclude='*.key'.

## Decision Log

<!-- Significant technical decisions with rationale. Why X was chosen over Y. -->
