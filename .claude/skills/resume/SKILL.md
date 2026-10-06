---
name: resume
description: Start-of-session procedure for this repo. Reads M68000/sessions/<workstream>.md, checks the checkout and any concurrent sessions, reports the resume point and conflicts, then continues the workstream's "Next session" plan. Use when Dave types /resume <workstream> or asks to continue a workstream (populous, powermonger, cadaver, emulator, ...).
---

# /resume <workstream>

1. Read `M68000/sessions/README.md` and `M68000/sessions/<workstream>.md`. If the handoff does not
   exist, list `M68000/sessions/` and ask which workstream is meant; do not guess from old notes.
   If the argument is a cross-cutting task (docs, tools, the emulator) rather than a game, there is
   no workstream handoff to resume: do steps 3 and 4 against the shared resources the task touches,
   and write no handoff unless Dave asks for one.
2. Name this session after the workstream if the host lets you set a session title, so other
   sessions see who is working on what.
3. Check the ground truth against the handoff:
   - `git log --oneline -5` and `git status --short`: is the handoff's last commit in the history,
     and is there uncommitted work? Uncommitted files you did not make belong to another session:
     leave them alone, unless `ListAgents` shows no live session on this workstream: then it is a
     dropped pass (a prior session ended without committing or writing its own handoff), not
     someone else's in-progress work. Read the diff: if it is coherent, finished-looking prose (not a
     half-written fragment) and any tool or script it names exists in `tools/` or `py/`, verify and
     commit it as its own commit before continuing, rather than leaving it stranded.
   - `ListAgents`: which other sessions are live, and on what. Before touching a shared resource
     (sessions/README.md, "Shared resources"), message them.
   - `tasklist | grep -i dotnet`: emulator processes that are running (possibly another session's).
   - The working data and snapshot named in "Resume point" exist; if not, rebuild them with the
     recipe the handoff points to.
   - Before scoping a live test for a carried-over "Open" item, grep the topic doc for whether a
     numbered section already answers it: an Open item goes stale when a later section settles it
     without the handoff being updated.
4. Report in a few lines: resume point, anything that disagrees with the handoff, live sessions and
   what they hold, and the first step you will take. Then do it: the handoff's "Next session" is the
   plan, and "Open, in priority order" is the backlog.
5. Follow the workstream's own skill (for a game: `reverse-engineer-st-game`) and finish with
   `/handoff <workstream>`.
