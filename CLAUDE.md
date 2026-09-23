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

## Rules

- Run through `M68000/run.ps1` or `dotnet exec M68000/bin/Debug/net8.0/M68000.dll` from
  `M68000/`. Addresses in docs are runtime absolute addresses.
- **Another Claude session is often working in this checkout.** Before `taskkill` on dotnet,
  `dotnet build`, or editing a file with uncommitted changes you did not make, check
  (`git status`, `tasklist | grep dotnet`) and ask. Subagents must be told: no build, no git,
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

## Shell pitfalls on this machine

- Git-bash `sed -i` rewrites a CRLF file with LF endings (`Program.fs` is CRLF), turning a
  one-line change into a whole-file diff. Edit such files with the Edit tool, or in Python
  opened in binary, and read `git diff --stat` before staging.

- Bash heredocs and inline `python -c` mangle backslashes (Windows paths, `\AUTO\`, regexes).
  For text containing backslashes use the Edit/Write tools, not shell string surgery.
- Ghidra 12.1 is at `C:/Program Files/ghidra_12.1_PUBLIC` (`support/analyzeHeadless.bat`).
  In Ghidra Java scripts write regexes as `"\\s+"`; `"\s"` is Java's single-space escape and
  silently matches no tabs.
