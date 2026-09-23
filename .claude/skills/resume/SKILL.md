---
name: resume
description: Start-of-session procedure for this repo. Reads M68000/sessions/<workstream>.md, checks the checkout and any concurrent sessions, reports the resume point and conflicts, then continues the workstream's "Next session" plan. Use when Dave types /resume <workstream> or asks to continue a workstream (populous, powermonger, cadaver, emulator, ...).
---

# /resume <workstream>

1. Read `M68000/sessions/README.md` and `M68000/sessions/<workstream>.md`. If the handoff does not
   exist, list `M68000/sessions/` and ask which workstream is meant; do not guess from old notes.
2. Name this session after the workstream if the host lets you set a session title, so other
   sessions see who is working on what.
3. Check the ground truth against the handoff:
   - `git log --oneline -5` and `git status --short`: is the handoff's last commit in the history,
     and is there uncommitted work? Uncommitted files you did not make belong to another session:
     leave them alone.
   - `ListAgents`: which other sessions are live, and on what. Before touching a shared resource
     (sessions/README.md, "Shared resources"), message them.
   - `tasklist | grep -i dotnet`: emulator processes that are running (possibly another session's).
   - The working data and snapshot named in "Resume point" exist; if not, rebuild them with the
     recipe the handoff points to.
4. Report in a few lines: resume point, anything that disagrees with the handoff, live sessions and
   what they hold, and the first step you will take. Then do it: the handoff's "Next session" is the
   plan, and "Open, in priority order" is the backlog.
5. Follow the workstream's own skill (for a game: `reverse-engineer-st-game`) and finish with
   `/handoff <workstream>`.
