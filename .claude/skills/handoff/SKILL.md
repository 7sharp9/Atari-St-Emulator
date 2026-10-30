---
name: handoff
description: End-of-session procedure for this repo. Commits or lists the session's work, applies verified lessons to CLAUDE.md / skills / tools / docs, rewrites M68000/sessions/<workstream>.md and prints the one-line next-session prompt. Use when Dave asks to wrap up, hand over, write a next-session prompt, or when the context is getting too full to work efficiently. Argument: the workstream name (populous, powermonger, cadaver, emulator, ...).
---

# /handoff <workstream>

Thin wrapper: the procedure lives in the `continuity` plugin, this repo's data in `.claude/continuity.md`.

1. Call the Skill tool with skill `continuity:session-handoff` and args `$ARGUMENTS`.
2. Follow it, using `.claude/continuity.md` as the repo profile (sessions in `M68000/sessions/`, its
   "Handoff: land the work", "Handoff: extra checks", "Lesson routing" and "Commit rules").
3. For a game workstream, the `reverse-engineer-st-game` skill is where reversing-method lessons go.

If `continuity:session-handoff` is not available, tell Dave the `continuity` plugin is not installed, give the
install command `/plugin install continuity@tritone` (marketplace `tritone`, declared in `.claude/settings.json`),
and stop. Do not improvise a handoff procedure.
