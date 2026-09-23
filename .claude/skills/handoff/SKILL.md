---
name: handoff
description: End-of-session procedure for this repo. Commits or lists the session's work, applies verified lessons to CLAUDE.md / skills / tools / docs, rewrites M68000/sessions/<workstream>.md and prints the one-line next-session prompt. Use when Dave asks to wrap up, hand over, write a next-session prompt, or when the context is getting too full to work efficiently. Argument: the workstream name (populous, powermonger, cadaver, emulator, ...).
---

# /handoff <workstream>

The goal: the next session (or a concurrent one) can continue from `M68000/sessions/<workstream>.md`
alone, and every lesson this session paid for is written where it will be read. Read
`M68000/sessions/README.md` first if you have not this session.

## 1. Land the work

- `git status`. For each file you changed this session: commit it (named files only, never
  `git add -A`; read `git diff --cached --stat` first; no Co-Authored-By trailer), or list it under
  "Uncommitted work left behind" with the reason. Never commit files you did not change; if a
  file has both your edits and another session's, ask before committing it.
- Emulator changes only after the regression net (reverse-engineer-st-game skill, section 6), and a
  build into `bin/` only after checking and messaging live sessions (sessions/README.md, "Shared
  resources").

## 2. Retro: what would have made this session faster

List for yourself what cost time: wrong assumptions, rediscovered facts, missing tools, rules that
were not written down, prompts that were ambiguous. For each, apply the fix where it will be read:

| lesson | goes to |
|---|---|
| a repo-wide rule or shell/tool pitfall | `CLAUDE.md` (keep it short; one line per rule) |
| a step in reverse-engineering a game | `.claude/skills/reverse-engineer-st-game/SKILL.md` |
| a tool that was missing or rewritten ad hoc | the tool itself, plus its row in `M68000/DEVELOPING.md` "Other tools" |
| a fact about a game | that game's topic doc, as definitive text |
| a trap specific to this workstream | the handoff's "Known traps" |
| a correction of how you worked | a `feedback` memory naming the failure mode |

Only verified lessons. Edits to `CLAUDE.md` or a skill: check `ListAgents`, tell any live session
what you are changing, and commit those files in their own small commit. If nothing is worth
changing, say so; do not invent improvements.

## 3. Re-check the design digest

If the game's `reversing/<game>/README.md` has a "Design digest" section (the game's rules
restated for re-use: what carries the game, what limits became features, what are bugs), check it
against this session's work before the handoff:

- List the session's changes to the topic docs and reference models (`git diff <start>..HEAD --stat`
  over `reversing/<game>/`, where `<start>` is the handoff's last commit when the session began).
- For each change, find every digest line that relies on the changed section, and each digest line
  that names a routine, rule or count this session touched. Correct it in place, or add the rule
  if the session proved a new core mechanic or bug.
- Every digest line cites the topic-doc section that proves it; a line whose section no longer
  says so is wrong until fixed. Anything not proven stays labelled inferred.
- Commit the digest with the session's work, and say in the report whether it changed.

## 4. Rewrite the handoff

Rewrite `M68000/sessions/<workstream>.md` from `M68000/sessions/_template.md` (create it, and add its
row to `sessions/README.md`, if this is the first handoff). It replaces the old content entirely:

- Resume point: the last commit, the working-data location, the snapshot to start from.
- Proven so far: short, with counts and scripts; point at the topic docs for detail.
- Open, in priority order: what is still missing in the understanding of the game or system, each
  with how it would be proven. Order by what unblocks the most, not by what is easiest.
- Known traps; Next session (3-6 lines).

Fold in and delete any older continuation note this workstream used (a scratchpad `NEXT_SESSION.md`,
a root `next_session.md`, a memory RESUME block); leave a memory entry that only points at the
handoff file. Commit the handoff.

## 5. Report

Tell Dave: what was committed, what is left uncommitted and why, the lessons applied and where,
whether the design digest changed, and
the next-session prompt, which is always exactly:

```
/resume <workstream>
```
