---
name: catchup
description: Use when the user asks for /catchup, to resume from a handoff file, get oriented from a preselected project note, or explain what Codex will do next after reading project continuation context.
metadata:
  short-description: Resume work from a handoff note
---

# Catchup

Resume work from a compact project handoff without rereading the whole repository.

## Workflow

1. Find the handoff source in this order unless the user specifies a file:
   - `docs/HANDOFF.md`
   - `.codex/HANDOFF.md`
   - `HANDOFF.md`
   - `docs/CATCHUP.md`
2. Read the handoff file first.
3. Inspect only the files and directories named in the handoff, plus `git status --short --branch`.
4. If the handoff points to tests or commands, inspect enough project metadata to know how to run them.
5. Output a brief understanding check before making changes, unless the user explicitly asked to proceed directly.

## Default Output

Use this structure:

```markdown
**Catchup**
I read `<handoff path>` and checked the current workspace state.

What I understand:
- ...

Relevant files:
- `path`: why it matters.

Current git state:
- ...

Next move:
- ...
```

## Behavior

- Keep the summary short and operational.
- Name stale or missing handoff details plainly.
- If the handoff is absent, say so and do a light repo orientation instead of a full deep dive.
- Do not ingest broad directories unless the handoff is too stale to act on.
