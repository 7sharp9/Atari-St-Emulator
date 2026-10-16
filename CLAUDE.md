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
  + scripts). Reverse-engineering a new game follows the `reverse-engineer-st-game` skill, which
  holds the method and the evidence rules; this file holds the repo and machine rules.
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

## Running

- Run through `M68000/run.ps1` or `dotnet exec M68000/bin/Debug/net8.0/M68000.dll` from
  `M68000/`. Addresses in docs are runtime absolute addresses.
- **Set `ATARI_NOTRACE=1` on every raw `dotnet exec` invocation.** Without it the emulator traces
  every instruction, including for `resume <snap> repl` with a REPL script on stdin, not just a cold
  `boot`/`<N>`: a multi-hundred-million-step run writes a multi-GB log and takes vastly longer.
  On the Mac (no PowerShell) use `ps`/`pkill` for `tasklist`/`taskkill`: `M68000/DEVELOPING.md`, "macOS".
- **`run.ps1`'s subcommands are aliases, not real argv** (its `switch` block is the source of
  truth): `rrepl <snap>` is raw argv `resume <snap> repl`, `snap <N> <path>` is `<N> snapshot <path>`,
  `resume <snap> [N]` is `<N> resume <snap>`. An alias name passed to the raw binary matches no argv
  pattern and silently falls through to a disk-less cold boot that sits forever in an early ROM wait
  loop. That looks exactly like a stuck or corrupt snapshot (blank `snap_render.py` output, a `bpc`
  that never hits); check the argv against the switch block first.
- **Another Claude session is often working in this checkout.** Before `taskkill` on dotnet,
  `dotnet build`, or editing a file with uncommitted changes you did not make, check
  (`git status`, `tasklist | grep dotnet`, `ListAgents`) and ask: message a live session with
  `SendMessage`, otherwise ask Dave. Subagents are told: no build, no git, no taskkill, write only
  under their own directory. If the other session holds `bin/Debug/net8.0/M68000.dll`, the build
  fails only at the copy step: confirm your change compiles with
  `dotnet build -c Debug M68000.fsproj -o <scratch dir>` and leave its process alone.

## Emulator changes

- Every emulator change goes behind the regression net in the skill's section 6 (verify, 30M-step
  snapshot compare, build, selftest 0 wrong).
- Hot path (`M68000/DEVELOPING.md`, "Performance"): a new decoder's `printfn`/`sprintf` goes behind
  `if Trace.enabled`, per-step constants stay literals, new active patterns are struct
  `ValueOption`. `selftest` runs the flat bus and does not exercise the MMU RAM fast path, so an
  MMU change is gated by the 30M snapshot compare plus a game snapshot compare.
- A speed claim needs an interleaved A/B of two builds. Allocation counts and profile estimates are
  hypotheses: a change that cut allocation 30% (struct `ResolveEa`) was 7% slower. Agents that time
  an A/B share the machine with other sessions: record `uptime` per run, interleave the variants,
  report median and min, and call a gap under about 5% noise unless it repeats in every pair.
- A finding that the emulator "cannot do X" is re-checked from a fresh cold boot, not only against
  an existing snapshot lineage (skill, section 5).

## Git

- Stage named files only, never `git add -A` (ROMs, game disks and cracked archives sit untracked in
  the tree); check `git diff --cached --stat` before committing. No `Co-Authored-By` trailers:
  history was scrubbed of them.
- Edits to `CLAUDE.md` and the skills go in their own small commit, never mixed into a workstream commit.

## Docs

- Docs are definitive reference text: correct stale claims in place, no pass-by-pass diary. A new
  finding is integrated into the surrounding prose (supersede, reconcile or fold in what it
  changes), not appended as one more dated clause to a long paragraph or table cell. A section that
  has become an unreadable run-on is rewritten into a normal narrative of current understanding in
  the same edit. The "what changed this pass" framing lives in `git log` and
  `M68000/sessions/<workstream>.md` only. This applies to `CLAUDE.md`, the skills and
  `DEVELOPING.md` as much as to the topic docs: write the rule or the process as it is now, with a
  pointer to the doc that holds the evidence, not the story of the pass that found it.
- Before writing a new interpretive claim, grep the topic doc for whether a later section already
  retired that framing. Before disassembling a routine to decode it, grep the topic docs (including
  other games' `ai.md`/`economy.md`, for shared engine code) for its hex address: it may already be
  pseudocoded. When a correction lands, grep every doc for the routine's address and the old wording and
  fix each copy in the same edit: PowerMonger's melee drain was corrected in `ai.md` ("a hard `moveq #0`, not
  `min(44,6)`") while `economy.md` and two `strategy.md` pseudocode blocks kept `min(v,6)`, and SPEC's
  "no writer produces `>= $80`" outlived `strategy.md`'s forced `$84`/`$92` writes.
- A graphics asset decoded for the first time well enough to render is committed as a PNG next to the
  doc that proves the format and table-indexed in `graphics.md` or the README's files table.

## Evidence rules

The reasoning behind each is in the `reverse-engineer-st-game` skill, with a pointer to the doc
that holds its worked example.

- Every behavioural claim about a game needs an emulator check (callcap diff, frame capture or
  screenshot diff) with a match count, or is labelled inferred.
- Name a routine from its own body (read to its first branch), a table from a match against an
  independent record set, and a field from the game's own UI text, not from where the routine is
  seen running or who first reads the table.
- "Nothing writes X", "no caller" and "never reached" need a whole-image listing, every writer's
  full block, a block-clear check, and the address list and roll the census used. Confirm any
  pre-existing `.asm`/`.c` export reaches the end of the text segment before trusting a negative
  from it. `tools/rdis.py` is not a whole-program listing: it does not follow
  `lea T(PC),A0 / movea.l 0(A0,D0.w),A0 / jsr (A0)` longword state tables (they print as `ori.b`
  garbage, so every handler behind one is missing). For "who writes X / who calls Y" use a raw scan
  of the image or `tools/disassemble.py --rom <img> --base 0 --all <lo> <hi>` (code only: stop where
  code ends).
- A verb or opcode table named from reading its handlers is a hypothesis until each handler is
  called under `callcap`. A door graph or dataflow chain is a hypothesis until each leg is driven.
- A trial that varies more than one thing proves no cause. An input test needs a same-snapshot,
  same-budget control, a hold longer than the game's poll cycle, and a signal that changes only if
  the mechanism fired. A `bp`/`bpc`/`watch` that finds nothing is bounded by its own budget, and by
  its input: show the precondition live in the same run (PowerMonger's "sound event 17 never plays" came
  from a view with no lit fire, its count 0 at every dispatch; with the fire in view it plays, `py/ui/snd_slot.sh`).
  A count it does find is bounded the same way: "the rollout win's lead was engaged once" came from a 15M-step watch
  of a 1120M run, and a whole-run sample found a 65-health fight 7M steps after the window (`commander/leadkill/gate_standoff.sh`).
- A hero pinned at one screen coordinate is usually a camera-follow trigger; a position reached is
  not proof the maneuver was safe (check health and status bytes across the run); a snapshot after
  a fixed hold may be a mid-motion frame.
- "Never in state X" read from periodic snapshots is a sample, not a trace: `watch` the byte over the window. The
  commander's rollout-win lead "never left `$34`" at 5M samples; a watch found a melee at 1457M that lasted under one
  tick (`commander/leadkill/gate_leadkill.sh win`).
- A cause read off the state at a failure needs the run's trajectory before it rules a remedy out: the commander
  handoff said the captain starved with its own lords at 0 food, so fetching food could not help; that was true at
  330M, but at 150M those lords held 327 food it never took, and taking it won land 1 in half the steps
  (`reversing/powermonger/commander/README.md` "The campaign"). A variable that sets the losses apart is checked in a
  win too: every land-2 captain death was against a posture-2 group, but the win fought posture-2 groups as well; the
  lead's own melee mode is what differed ("Land 2 as a rate").

## Proving routines with parallel subagents

The brief, the hard rules, the promotion and merge steps are in the skill's section 3c. The ones
that are easy to forget:

- Name the tool index in the brief (`M68000/DEVELOPING.md` "Other tools") and take addresses, strides
  and struct offsets from the code, never from memory. Give addresses and symbol names, not roles:
  "role unknown: name it from its body".
- Subagents cannot write `report.md`: take the report as the final message and save it yourself.
- Tell agents to derive the repo root by walking up to the directory holding `tools/rdis.py` (or
  `M68000_ROOT`), never a literal path or fixed `../` count, and to keep temp files in one named
  scratchpad dir.
- Re-run every gate from fresh callcaps, from the promoted location, before merging.
  Give each promoted gate its own output subdirectory: two gates that both name an arm `ctl` in one directory overwrite
  each other, and one then checks the other's run (commander `gate_local.sh` and `gate_retire.sh` did). Name a promoted
  directory anything but `build/`: `.gitignore` ignores it.
- `callcap` runs with interrupts masked, so a routine that plays a sound waits forever on a flag the
  interrupt clears (PowerMonger: poke `$2c993` to 0 in the state). Corpus capture:
  `tools/capture_hits.py`.

## Shell pitfalls on this machine

- Git-bash `sed -i` rewrites a CRLF file with LF endings (`Program.fs` is CRLF), turning a
  one-line change into a whole-file diff. Edit such files with the Edit tool, or in Python
  opened in binary, and read `git diff --stat` before staging.
- Bash heredocs and inline `python -c` mangle backslashes (Windows paths, `\AUTO\`, regexes).
  For text containing backslashes use the Edit/Write tools, not shell string surgery.
- The Bash tool's working directory drifts between calls: `cd` to an absolute path first.
- zsh (the Mac shell):
  - does not word-split an unquoted `$VAR`: a variable holding several REPL tokens arrives as one
    malformed line and the REPL stops there. Pass tokens separately.
  - reads `$f:name` as `$f` plus a history modifier (`:e` is the extension): write `"${f}:name"`.
    `cbmame.sh` changes into the run directory, so its script argument must be an absolute path.
  - reads an unquoted `GR:x>=24` as a redirect to a file named `24`: quote REPL and `explore.py`
    words that contain `<` or `>`.
  - fails `echo =====` (`=word` expands to a command path): quote it.
  - aborts a whole `for f in a/*.md a/*.sh; do ...` when one glob matches nothing: run such loops
    with `bash`, or `setopt nonomatch`. An unquoted `grep --include=*.fs` or `ps aux | grep [d]otnet` fails the same way ("no matches found"), and the pipe then prints nothing, which reads as "no process": quote it.
- A waiter `until ! pgrep -f 'run.sh x'` matches its own shell's command line and never exits: bracket one
  character (`pgrep -f 'run[.]sh x'`), or wait on the background task's own notification.
- macOS has no `timeout`: `... | timeout 60 dotnet ...` fails before running, and a following
  `grep -c` prints 0, the same as "no hits". Print the raw output and a positive control before
  counting, and bound runs with step counts.
- `grep -r` from `M68000/` walks the multi-GB `scratchpad/` and blows the 120 s tool timeout: name
  the directories (`reversing/ tools/ sessions/`) or pass `--exclude-dir=scratchpad`.
- A long-running driver script (a bot) edited in place loses the versions that worked (Crude Buster's
  `natbot.lua` reached level 5's last screen in one state and stalled at its first fight in the
  next). Copy it aside, or commit, before each behaviour change, and re-run the level that last
  cleared.
- On the Mac, scratchpad data made on Windows lives on `gpubox`
  (`~/Documents/GitHub/Atari-St-Emulator`). scp fails there (its PowerShell profile errors); stream it:
  `ssh gpubox 'tar -cf - -C C:/Users/Dave/Documents/GitHub/Atari-St-Emulator/M68000/scratchpad <names>' | tar -xf -`.
- Ghidra 12.1 is at `C:/Program Files/ghidra_12.1_PUBLIC` (`support/analyzeHeadless.bat`); on the Mac
  at `~/Downloads/ghidra_12.1.4_PUBLIC` (natives built with `buildNatives`; 12.0 there lacks 17
  functions). In Ghidra Java scripts write regexes as `"\\s+"`: `"\s"` is Java's single-space
  escape and silently matches no tabs.

## Emulator behaviours that look like input bugs

- `watch <addr> [len]` reports every CPU write whose bytes overlap the range (a word write at `$1000`
  covers a watched `$1001`) and every FDC DMA sector landing in it (a `DMA read sector` line); it cannot name
  the PC of a REPL `w` poke (it is reported with the last step's `step=`/`pc=`). One region at a time: a
  second `watch` replaces the first.
  Its `step=` is the snapshot's cumulative step counter, not steps
  into the run (PowerMonger's rand1 starts near 828.75M): line it up with a `hits` first-hit inside the watch.
- REPL `w <addr> <8 hex digits>` writes a 4-byte longword: poking a one-byte field clobbers the next
  three. Read the neighbouring fields and write the whole longword deliberately.
- In a REPL drive the click is consumed during the settle after `mouse down`: start `hits` or `bp`
  before the down, or the census misses the handler. `hits <n> <addrs>` after a `bp` that stopped
  the run counts only what happens after the stop, so a routine that ran earlier reads 0 and looks
  uncalled: run `hits` from the end of the click, before any `bp`.
- `hits` on a routine every side runs (PowerMonger's executor `$6b38`, attack `$6c32`) counts all sides' calls, so a
  count after a poke is not the poked side's: attribute each call by its own data (`bp`, then the packet's side byte at
  A0). Side 2's 26 orders after side 3's captain died read as side 3's stale pigeons until `bp 6b38` showed byte 0 = 2.
- `hits`, `bp` and `bpc` count instruction starts: an interrupt taken at a counted address and its RTE
  back there count once, also when the interrupt was entered by an `s` before the command (`AtartSt.CensusStep`).
  Corpora captured before this change hold those duplicates: PowerMonger's `$1abaa` corpus has stops ~20 steps
  apart with the routine's state unchanged, which `py/season/gate_1abaa.py` dedupes (`REENTRY`). They and
  `until` compare 24-bit addresses, so a PC with junk upper bits (TOS 1.00's handlers run at `$04fc0a1a`)
  matches.
- A `kbd`/`mouse` status byte is a raw level in RAM, not an edge-latched event. A pulse shorter than
  the game's poll cycle can fall between two polls and never register: hold longer than the game's
  poll cycle. The VBL is raised every 12,000 steps exactly (`instructionsPerFrame`, a literal in
  `Program.fs`); a game loop that runs every second VBL, as Impossamole's gameplay rooms do, polls
  every 24,000, so 30,000 is the safe hold. Check for a per-object busy flag that skips the per-frame
  input read. Details: skill, section 2.
- A game that polls the keyboard ACIA data register directly (`cmpi.b #$39,$fc02.w` / `bne` back)
  never sees a key here: `MMU.fs` pops the FIFO on a read of `$fffc02` and returns 0 when it is
  empty, so TOS's keyboard ISR (still installed at `$118`) takes the byte first; a real 6850 keeps
  the last byte. Black Tiger's cracktro `$a562` and trainer menu `$c658` both stall this way. Bypass
  with a labelled `w` poke of the branch in the drive script (`reversing/black_tiger/drive.txt`); the
  real fix is an emulator change behind the regression net.
- `u <addr>` from a snapshot already stopped at `<addr>` (a `$f898`-frame snapshot) returns at once with "reached after 0 steps"; step past it first (`s 2000000`, then `u`), as `capture.sh` does.
- Appending to a game's ring-queue input at its read pointer is overwritten by the game's own
  pushes: append at the write pointer (Cadaver `304(A5)`, advance by 8, `1154(A5)` += 1).
