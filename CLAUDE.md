# Atari-St-Emulator

An F# Atari ST emulator (`M68000/`: 68000 core, MMU/peripherals, TOS 1.00 ROM) used to boot,
run and reverse-engineer commercial ST games. Build, run and debugging tooling are documented
in `M68000/DEVELOPING.md`. Its "Other tools" table is the index of `M68000/tools/`: check it
before writing any helper, because several have been rewritten ad hoc by sessions that did not
know they existed.

## Layout

- `M68000/*.fs`: emulator. `Program.fs` holds the CLI and the stdin-driven REPL (`help` lists
  the commands: breakpoints, `callcap`, `hits`, `watch`, `kbd`/`mouse`, ...).
- `M68000/tools/`: disassembler, trace/CFG, graphics, disk-image, PRG-relocation and Ghidra
  decompile tools.
- `M68000/reversing/<game>/`: one directory per analysed program (README + topic docs + `.sym`
  + scripts). Reverse-engineering a new game follows the `reverse-engineer-st-game` skill.
- `M68000/scratchpad/`: gitignored working data (snapshots, extracted disk files, decompiles).
  `scratchpad/ANCHORS.md` indexes the reusable snapshots. Scripts worth re-running go in
  `reversing/<game>/py/` with a README table (`powermonger/py/`, `populous/py/`), writing
  their output under a scratchpad dir, not in `scratchpad/pmNNN/` where the next session
  cannot find them.

## Sessions and handoff

- Start a session with `/resume <workstream>` and end it with `/handoff <workstream>` (skills in
  `.claude/skills/`). `M68000/sessions/<workstream>.md` is the only continuation record: not
  scratchpad notes, not a root `next_session.md`, not a memory RESUME block. A session writes only
  its own workstream's handoff.
- Shared resources (the `bin/` DLL, `*.fs`, `CLAUDE.md`, skills, `tools/`) and how to coordinate on
  them: `M68000/sessions/README.md`.

## Rules

- Run through `M68000/run.ps1` or `dotnet exec M68000/bin/Debug/net8.0/M68000.dll` from
  `M68000/`. Addresses in docs are runtime absolute addresses.
  The raw `dotnet exec` form traces every instruction unless `ATARI_NOTRACE=1` is set. On the Mac
  (no PowerShell) use it with `ps`/`pkill` for `tasklist`/`taskkill`: `M68000/DEVELOPING.md`, "macOS".
- **Another Claude session is often working in this checkout.** Before `taskkill` on dotnet,
  `dotnet build`, or editing a file with uncommitted changes you did not make, check
  (`git status`, `tasklist | grep dotnet`, `ListAgents`) and ask: message a live session with
  `SendMessage`, otherwise ask Dave. Subagents must be told: no build, no git,
  no taskkill, write only under their own directory. If the other session holds
  `bin/Debug/net8.0/M68000.dll`, the build fails only at the copy step: confirm your change
  compiles with `dotnet build -c Debug M68000.fsproj -o <scratch dir>` and leave its process alone.
- Emulator changes go behind the regression net in the skill's section 6 (verify, 30M-step
  snapshot compare, build, selftest 0 wrong).
- Git: stage named files only, never `git add -A` (ROMs, game disks and cracked archives sit
  untracked in the tree); check `git diff --cached --stat` before committing. No
  `Co-Authored-By` trailers: history was scrubbed of them.
- Docs are definitive reference text: correct stale claims in place, no pass-by-pass diary.
- Every behavioural claim about a game needs an emulator check (callcap diff, frame capture or
  screenshot diff) with a match count, or is labelled inferred.
- A "nothing writes X" or "only Y writes X" claim needs every writer: grep a whole-image
  listing (`disassemble.py --snap <snap> --all <lo> <hi>`) and read each writer's full block;
  the next instruction can overwrite the value (PowerMonger `$2452` is undone by `$245c`).

## Proving routines with parallel subagents

What made the PowerMonger 122nd pass's three parallel proofs work, and what went wrong:
- One shared `BRIEF.md` in the working dir. Take its addresses, strides and struct offsets
  from the code (`tools/pm_common.py`, `tools/pm_fsm_ref.py`, the docs' proven sections), never
  from memory: that brief got the object table wrong, and every agent had to correct it.
- Subagents cannot write `report.md` (the tool refuses). Ask for the report as the final
  message and save it yourself into the agent's directory.
- Corpus capture: `tools/capture_hits.py`. `callcap` runs with interrupts masked, so a routine
  that plays a sound waits forever on a flag the interrupt clears (PowerMonger: poke `$2c993`
  to 0 in the state).
- When two agents transcribe the same callee, keep one version and run both corpora against it:
  that cross-check is free.
- Before merging: re-run every gate from fresh callcaps (no `reuse`), merge the transcriptions
  into the game's reference module, move the gates to `reversing/<game>/py/` (corpora stay in
  scratchpad, listed in `ANCHORS.md`), then run all older gates of that module again.

## Shell pitfalls on this machine

- Git-bash `sed -i` rewrites a CRLF file with LF endings (`Program.fs` is CRLF), turning a
  one-line change into a whole-file diff. Edit such files with the Edit tool, or in Python
  opened in binary, and read `git diff --stat` before staging.

- Bash heredocs and inline `python -c` mangle backslashes (Windows paths, `\AUTO\`, regexes).
  For text containing backslashes use the Edit/Write tools, not shell string surgery.
- The Bash tool's working directory drifts between calls: `cd` to an absolute path first.
- In a REPL drive the click is consumed during the settle after `mouse down`: start `hits` or
  `bp` before the down, or the census misses the handler.
- Ghidra 12.1 is at `C:/Program Files/ghidra_12.1_PUBLIC` (`support/analyzeHeadless.bat`); on the Mac at
  `~/Downloads/ghidra_12.1.4_PUBLIC` (natives built with `buildNatives`; 12.0 there lacks 17 functions).
  In Ghidra Java scripts write regexes as `"\\s+"`; `"\s"` is Java's single-space escape and
  silently matches no tabs.
