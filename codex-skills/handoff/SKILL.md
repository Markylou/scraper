---
name: handoff
description: Use when the user asks for /handoff, a continuation note, transfer brief, restart summary, compact project context, or a small document that lets future Codex sessions continue without rereading the whole project.
metadata:
  short-description: Create compact project continuation briefs
---

# Handoff

Create a compact continuation document that lets another Codex session pick up the work with minimal repo ingestion.

## Workflow

1. Inspect only the context needed to understand the current project state:
   - `git status --short --branch`
   - recent user-mentioned files, plans, docs, and active source files
   - existing handoff/catchup files if present
2. Prefer evidence from live files and command output over memory.
3. Write the smallest useful handoff. Avoid broad architecture summaries unless they are needed for continuity.
4. Include concrete file paths, commands, and next actions.
5. Clearly separate verified facts from guesses or stale context.

## Default Output

If the user does not specify a target file, write to `docs/HANDOFF.md` when a `docs/` directory exists. Otherwise write to `.codex/HANDOFF.md`, creating `.codex/` if needed.

Use this structure:

```markdown
# Handoff

## Project
- One or two sentences about what this repo/project is.

## Current State
- What is true right now, based on inspected files and git status.

## Recent Decisions
- Decisions or constraints that future work should preserve.

## Key Files
- `path`: why it matters.

## Commands
- `command`: what it verifies or runs.

## Open Work
1. Next concrete step.
2. Next concrete step.
3. Next concrete step.

## Watchouts
- Known blockers, stale outputs, fragile areas, or things not to touch.
```

## Style

- Keep it concise enough to paste into a new session.
- Do not include long code excerpts.
- Do not narrate everything inspected.
- Do not claim tests pass unless they were run in this session.
