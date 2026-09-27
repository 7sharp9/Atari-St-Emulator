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
     leave them alone — *unless* `ListAgents` shows no live session on this workstream, in which case
     it's a dropped pass (a prior session ended without committing or writing its own handoff), not
     someone else's in-progress work. Read the diff: if it's coherent, finished-looking prose (not a
     half-written fragment) and any tool/script it names actually exists in `tools/`/`py/`, verify and
     commit it as its own pass commit before continuing, rather than leaving it stranded (cadaver:
     a 75th-pass section sat uncommitted with no handoff update; the 76th-pass session confirmed no
     live session held it and committed it before starting its own work).
   - `ListAgents`: which other sessions are live, and on what. Before touching a shared resource
     (sessions/README.md, "Shared resources"), message them.
   - `tasklist | grep -i dotnet`: emulator processes that are running (possibly another session's).
   - The working data and snapshot named in "Resume point" exist; if not, rebuild them with the
     recipe the handoff points to.
   - Before scoping a live test for a carried-over "Open" item, grep the topic doc for whether a
     later numbered section already answers it — a handoff's Open item can go stale when a later
     pass's own section settles it without any handoff being updated to say so (cadaver 47th pass:
     item 3, "does a scripting/bytecode layer exist," had already been fully proven in §22-26 two
     passes earlier; the handoff kept restating it as an unscoped fresh question).
4. Report in a few lines: resume point, anything that disagrees with the handoff, live sessions and
   what they hold, and the first step you will take. Then do it: the handoff's "Next session" is the
   plan, and "Open, in priority order" is the backlog.
5. Follow the workstream's own skill (for a game: `reverse-engineer-st-game`) and finish with
   `/handoff <workstream>`.
