---
name: clean
description: Use when the user asks for /clean, a cleanup pass, removal review, stale file audit, dead code scan, or a two-step project cleanup where Codex first documents removal candidates and waits for approval before deleting or editing.
metadata:
  short-description: Audit and safely remove project cruft
---

# Clean

Run a careful cleanup workflow that finds removable or questionable project material, gets user approval, then removes only approved items.

## Phase 1: Audit

Inspect the project for:

- stale generated output
- unused scripts, modules, components, assets, or docs
- duplicate data or compatibility leftovers
- dead references in imports, routes, commands, docs, and config
- obsolete plans, scratch files, or abandoned migration artifacts
- files whose purpose is unclear

Prefer targeted searches with `rg`, `git status`, project manifests, import graphs, and existing docs. Avoid expensive broad reads unless needed.

## Phase 1 Output

Do not delete anything during the audit phase. Produce a review like:

```markdown
**Cleanup Audit**

Safe removal candidates:
- `path`: evidence and expected impact.

Needs your call:
- `path`: why uncertain, what might depend on it.

Keep:
- `path`: why it looked suspicious but should stay.

Suggested cleanup order:
1. ...
2. ...
```

## Phase 2: Approved Cleanup

After the user approves items:

1. Remove or edit only the approved paths/sections.
2. Avoid touching unrelated dirty work.
3. Update docs or references that mention removed items.
4. Run focused verification appropriate to the project.
5. Summarize exactly what changed and what was not verified.

## Safety Rules

- Never remove files only because they are unfamiliar.
- Treat generated data carefully; confirm it is rebuildable before deleting.
- Keep compatibility files when the repo or docs still reference them.
- If a file is tracked and user-created, prefer asking before deleting unless approval is explicit.
