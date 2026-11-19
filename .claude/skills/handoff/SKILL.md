---
name: handoff
description: End-of-session procedure for this repo. Commits or lists the session's work, applies verified lessons to CLAUDE.md / skills / tools / docs, rewrites M68000/sessions/<workstream>.md and prints the one-line next-session prompt. Use when Dave asks to wrap up, hand over, write a next-session prompt, or when the context is getting too full to work efficiently. Argument: the workstream name (populous, powermonger, cadaver, emulator, ...).
disable-model-invocation: true
---

# /handoff <workstream>

Call the Skill tool with skill `continuity:session-handoff` and args `$ARGUMENTS`, then follow it, using this repo's
profile `.claude/continuity.md`. This wrapper carries no rules of its own.

If `continuity:session-handoff` is unavailable, tell Dave the continuity plugin is not installed, give the one-time install for this machine (`/plugin marketplace add 7sharp9/claude_plugins`, then
`/plugin install continuity@tritone`, `evidence@tritone` and `academic@tritone`, then restart the session), and stop. Do not improvise a handoff procedure.
