---
name: resume
description: Start-of-session procedure for this repo. Reads M68000/sessions/<workstream>.md, checks the checkout and any concurrent sessions, reports the resume point and conflicts, then continues the workstream's "Next session" plan. Use when Dave types /resume <workstream> or asks to continue a workstream (populous, powermonger, cadaver, emulator, ...).
disable-model-invocation: true
---

# /resume <workstream>

Call the Skill tool with skill `continuity:session-resume` and args `$ARGUMENTS`, then follow it, using this repo's
profile `.claude/continuity.md`. This wrapper carries no rules of its own.

If `continuity:session-resume` is unavailable, tell Dave the continuity plugin is not installed, give the install
command `/plugin install continuity@tritone` (marketplace `7sharp9/claude_plugins`, declared in
`.claude/settings.json`), and stop. Do not improvise a resume procedure.
