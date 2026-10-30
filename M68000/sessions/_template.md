# <Workstream>: handoff

Updated <YYYY-MM-DD> by the session that ended at commit `<hash>`.

## Resume point

- Last commit of this workstream: `<hash>` <subject>.
- Working data: `<path>` (rebuild recipe: `<doc section>`).
- Start from: `<snapshot>` (<what state it holds>).
- Uncommitted work left behind: none | <files and why>.

## Proven so far

One line per result: claim, match count, script that reproduces it. Detail lives in the topic docs;
link the section.

## Running

Emulator runs or agents still going: what, PID, expected end, and the commands to check them. "Nothing
running." if so.

## Open, in priority order

1. <item>: why it matters; how it would be proven (script / snapshot / match count to reach).
2. ...

## Known traps

Things that cost time this workstream and are not yet in CLAUDE.md or a skill (tool quirks, slow
paths, misleading snapshots). Delete an entry once it has moved into CLAUDE.md, a skill or a doc.

## Waiting on Dave

Decisions and proposals (proposed CLAUDE.md or plugin edits).

## Next session

What the next session should do first, in 3-6 lines. The prompt that starts it is `/resume <workstream>`.
