---
name: resume
description: Start-of-session procedure for this repo. Reads M68000/sessions/<workstream>.md, checks the checkout and any concurrent sessions, reports the resume point and conflicts, then continues the workstream's "Next session" plan. Use when Dave types /resume <workstream> or asks to continue a workstream (populous, powermonger, cadaver, emulator, ...).
---

# /resume <workstream>

Thin wrapper: the procedure lives in the `continuity` plugin, this repo's data in `.claude/continuity.md`.

1. Call the Skill tool with skill `continuity:session-resume` and args `$ARGUMENTS`.
2. Follow it, using `.claude/continuity.md` as the repo profile (sessions in `M68000/sessions/`).
3. For a game workstream, follow the `reverse-engineer-st-game` skill during the session. Finish with
   `/handoff <workstream>`.

If `continuity:session-resume` is not available, tell Dave the `continuity` plugin is not installed, give the
install command `/plugin install continuity@tritone` (marketplace `tritone`, declared in `.claude/settings.json`),
and stop. Do not improvise a resume procedure.
