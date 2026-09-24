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
  decompile tools. Python deps (`numpy`, `pillow`) are managed with `uv`, not bare `pip`:
  `cd M68000 && uv sync` once per checkout, then `uv run python tools/foo.py ...` or activate
  `M68000/.venv` (`DEVELOPING.md` "Python tooling").
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
- Docs are definitive reference text: correct stale claims in place, no pass-by-pass diary. A new
  finding is integrated into the surrounding prose — supersede, reconcile or fold in what it
  changes — not just tacked on as one more dated clause appended to an already-long paragraph or
  table cell; if a section has become an unreadable pass-by-pass run-on, rewrite it into a normal
  narrative of current understanding as part of the same edit. Keep the "what changed this pass"
  framing only in `git log`/`M68000/sessions/<workstream>.md`, not in the topic doc's prose.
- When a session decodes a graphics asset for the first time (spritesheet, tileset, icon/panel
  art, palette) well enough to render it, commit the rendered image (PNG) alongside the doc that
  proves the format, not just a prose description or an untracked scratchpad file — future
  sessions and Dave need to see the asset without re-running the decode. Table-index it in
  `graphics.md`/the README's files table the way screenshots already are.
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
- zsh (the Mac shell) does not word-split an unquoted `$VAR`: a variable holding several REPL tokens
  arrives as one malformed line and the REPL stops there. Pass tokens separately. `echo =====` fails
  in zsh (`=word` expands to a command path); quote it.
- In a REPL drive the click is consumed during the settle after `mouse down`: start `hits` or
  `bp` before the down, or the census misses the handler.
- On the Mac, scratchpad data made on Windows lives on `gpubox` (`~/Documents/GitHub/Atari-St-Emulator`). scp fails
  there (its PowerShell profile errors); stream it: `ssh gpubox 'tar -cf - -C C:/Users/Dave/Documents/GitHub/Atari-St-Emulator/M68000/scratchpad <names>' | tar -xf -`.
- Ghidra 12.1 is at `C:/Program Files/ghidra_12.1_PUBLIC` (`support/analyzeHeadless.bat`); on the Mac at
  `~/Downloads/ghidra_12.1.4_PUBLIC` (natives built with `buildNatives`; 12.0 there lacks 17 functions).
  In Ghidra Java scripts write regexes as `"\\s+"`; `"\s"` is Java's single-space escape and
  silently matches no tabs.
