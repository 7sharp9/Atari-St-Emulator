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
  The raw `dotnet exec` form traces every instruction unless `ATARI_NOTRACE=1` is set — **this
  applies to every invocation, including `resume <snap> repl` piped a REPL script on stdin, not
  just a cold `boot`/`<N>`**: a multi-hundred-million-step `resume ... repl` run without it writes
  a multi-GB per-instruction log and takes vastly longer than the same run traced off (cadaver 55th
  pass: an hour lost to four parallel `resume ... repl` pushes that forgot it, each writing
  >1GB before being killed and rerun correctly). On the Mac
  (no PowerShell) use it with `ps`/`pkill` for `tasklist`/`taskkill`: `M68000/DEVELOPING.md`, "macOS".
  **`run.ps1`'s subcommands are aliases, not real argv** (`run.ps1`'s own `switch` block is the
  source of truth): `rrepl <snap>` is raw argv `resume <snap> repl`, `snap <N> <path>` is
  `<N> snapshot <path>`, `resume <snap> [N]` is `<N> resume <snap>`. Passing an alias name like
  `rrepl` straight to the raw binary matches no argv pattern and silently falls through to a
  disk-less cold boot, which then sits forever in an early ROM wait loop — this looks exactly like
  a stuck or corrupt snapshot (blank `snap_render.py` output, a `bpc` that never hits) until you
  check the argv against `run.ps1`'s switch block (cadaver `mechanics.md` §45).
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
- Before writing a new interpretive claim into a topic doc, grep it for whether a later section
  already retired the framing you're about to reuse — a session's own new section can revive a
  retired reading without meaning to, not just a stale carried-over handoff item (cadaver
  `mechanics.md` §47c revived a "type-8 room-registration" reading §31/§38 had retired sixteen-plus
  passes earlier, caught and fixed only on a later re-read, 48th pass).
- Before disassembling a routine to decode it, grep the topic docs (including the other games'
  `ai.md`/`economy.md`/`strategy.md` if the routine might be shared engine code) for its hex
  address — it may already be pseudocode'd from an earlier pass. PowerMonger 125th spent a full
  read-and-decode pass on `$157e6`'s settlement-pulse/loyalty logic only to reproduce, line for
  line, the C-style pseudocode already proven in `economy.md` §3a (96th/97th) and `ai.md`.
- When a session decodes a graphics asset for the first time (spritesheet, tileset, icon/panel
  art, palette) well enough to render it, commit the rendered image (PNG) alongside the doc that
  proves the format, not just a prose description or an untracked scratchpad file — future
  sessions and Dave need to see the asset without re-running the decode. Table-index it in
  `graphics.md`/the README's files table the way screenshots already are.
- Every behavioural claim about a game needs an emulator check (callcap diff, frame capture or
  screenshot diff) with a match count, or is labelled inferred.
- When reading a routine to explain why an input "does nothing," read to its next control-flow
  instruction (branch/jump/rts), not just to the first `jsr` whose target looks self-contained and
  irrelevant — an unconditional `jmp`/`bra` right after that call can be the actual mechanism, and
  stopping one instruction early reads as proof the input is a dead end. Impossamole: a fire-handler
  read stopped at `jsr $bb7e` (a red-herring cheat-word lookup keyed off a byte that stays 0) and
  concluded fire did nothing on the post-world-confirm logo screen; the very next instruction,
  `jmp $17c9c` (unconditional), was the world-select screen's own re-entry setup, missed for a full
  handoff (`reversing/impossamole/README.md`'s "Confirming a world" correction).
- A "nothing writes X" or "only Y writes X" claim needs every writer: grep a whole-image
  listing (`disassemble.py --snap <snap> --all <lo> <hi>`) and read each writer's full block;
  the next instruction can overwrite the value (PowerMonger `$2452` is undone by `$245c`).
  A game's static `<name>_ad58.asm`/`.c` export sitting in scratchpad is not automatically that
  whole-image listing: it can be truncated (Populous's `pop_ad58.asm` stops at $1d462, well short
  of the image's real end at $3d550 -- under 40% of the program) with no warning in the file
  itself. Grepping it found no writer for two addresses and called them dead code; both had a
  writer in the missing ~60%, found only by rerunning `find_field_writers.py`/`disassemble.py
  --all` fresh (populous mechanics.md/graphics.md's `$37eae`/`$3c4e4` correction). Before trusting
  a "no writer" result from any pre-existing `.asm`/`.c` file, confirm its address range actually
  covers the image end, or just re-run the tool.
- A field that reads the same static value across two far-apart snapshots is not proof it is
  "stuck" or ungated: it can be a value a busy-poll utility sets and clears within a couple hundred
  steps of each interrupt tick, in which case any snapshot taken during that poll's otherwise-idle
  majority (the loop's actual wait is ~98% empty re-reads) will show the same value, agreeing
  snapshots included. Prove it live before writing "isn't gated by the interrupt" or "handler never
  invoked": `hits <n> <handler-addr>` against the real vector target shows whether it's firing at
  all, and `watch <addr>` shows the value actually changing and who clears it back down
  (impossamole `reversing/impossamole/README.md`'s VBL-wait correction: two 30M-apart snapshots of
  `$1a2e9 = 0` were wrongly read as "never advances" when `hits`/`watch` proved the VBL handler
  fires every frame and the same wait routine consumes its own tick within ~233 steps).
- A sprite spotted "in roughly the right screen area" of a render is not proof it belongs to the
  object you think drew it, and a memory region's first N bytes are not proof of its whole content.
  Check an object's exact declared coordinates (a tight crop, or a live breakpoint on its own draw
  call) before attributing a visible sprite to it, and read a struct field at its real declared width
  and a buffer across its full extent, not a leading sample — both cost impossamole's 81st pass a
  wrongly-reported "this world's hero renders" finding (a different, unidentified sprite ~20-30px
  away from the hero's own position) and a wrongly-reported "empty buffer" (a legitimately
  zero-padded header read as proof the whole buffer was blank).
- The same "roughly the right area" trap applies to attributing *which object* satisfies a shared
  per-frame mechanism (a proximity/damage/contact check that runs generically over the whole object
  array), not just which object rendered a sprite: an object that merely looks like the right hazard
  from its static position is not proof it is the `A0` a live contact actually fires with. Pin the
  real object with a breakpoint on the mechanism's own write site (e.g. `bpc <addr> 1` on the exact
  instruction that writes the shared effect) and read `A0` there, rather than inferring it from
  nearby coordinates — impossamole's 83rd pass attributed a screen's hazard damage to a `type=2`
  object it had visually associated with the area; the 84th pass's `bpc` on `$e80e`'s damage-write
  instruction caught the real culprit as a different, static `type=1` object ten slots away in the
  array, with its own dx/dy only just inside the proximity test's threshold.
- A long-lived, repeatedly-resumed snapshot is not ground truth just because dozens of passes have
  built on it: if its own original cold boot silently took a wrong path (skipped a load, missed a
  timing-sensitive event), every snapshot descended from it inherits the same incomplete RAM state,
  and every pass that resumes it re-derives the same wrong conclusion, reading as independent
  confirmation when it's actually one mistake copied forward. A finding that looks like "this
  emulator can't do X" — especially one that contradicts a real-hardware cross-check — should be
  re-checked from a **fresh cold boot**, not just re-run against the existing lineage, before being
  written up as a bug: impossamole's 79th-81st passes spent three passes and a full real-Hatari
  cross-check concluding this emulator could never populate a game's hero-sprite bank or load one of
  its levels, all measured against one `after_select3.snap` lineage reused since very early in the
  workstream; the 82nd pass found a fresh cold boot with different (but reproducible) keypress timing
  reaches full parity with real hardware on both counts, and the old lineage's own boot — not this
  repo's F# core — was the actual divergence (`reversing/impossamole/README.md`'s "Real-hardware
  cross-check" retraction).
- A snapshot taken after holding a direction for a fixed step count is not proof of where movement
  stops — it can be a mid-motion frame, not a rest position. Check the mover's own state byte reads
  idle/settled (or re-run further steps and confirm the position stops changing) before writing that
  position up as where an input "walks to" or "settles at". Impossamole's 85th pass took `x=142` from
  a fixed-600000-step snapshot while the state byte still read "walking" (`$227f3=1`) and wrote it up
  as the hero's stopped position; the 86th pass found the hero actually kept walking to a real,
  confirmed-static stop 68px further at `x=74`, against a wall the `x=142` reading never reached
  (`reversing/impossamole/README.md`'s 86th-pass correction paragraph).
- A `bp`/`bpc`/`watch` check that finds nothing within its own step budget is not proof a maneuver is
  safe past that budget — the event you're checking for can land later than whatever window you
  happened to run. Re-run with a budget well past the maneuver's own known duration, not just past
  the point where it looks settled, before writing up "no hit"/"clean" as a final answer. And once a
  later check does catch a hit, read what actually caused it (`A0`, the exact contact address) rather
  than assuming it's the same hazard the trial was aimed at — it can be a different object entirely.
  Impossamole's 94th pass found three candidate dodge timings where `bp e82e` gave up clean (or hit)
  inside 700,000 steps and the hero looked settled — a further 400,000-step check caught a hit at all
  three, first written up as the original hazard catching up late; reading `A0` at the stop showed it
  was a second, different, previously-unconfirmed hazard the maneuver had actually already dodged.
  Both the short window and the assumed identity were wrong (`reversing/impossamole/README.md`'s
  "Known traps" section).
- A hero pinned at one screen coordinate is usually a camera-follow trigger, not a wall, and a
  trial that "lands at the same spot" has only shown the same *screen* spot. Before calling a position
  stuck, `watch` the scroll counter across the trial and find its writer (`find_field_writers.py`).
  Impossamole spent the 90th-97th passes on an `x=192` "wall" that was `addq.w #2,$227b6` at `$018fa2`,
  and disassembled the object-shift half (`$00bb5c`) without asking what advanced its delta
  (`reversing/impossamole/README.md`, camera-follow section).
- Before trial-driving a game to find out what is "past" a spot, dump the data structure its own
  scroll/loader reads: a level's whole tile map, room/exit tables and spawn list are usually resident in
  RAM from the start. Impossamole spent the 90th-98th passes hopping blind at `x=192`; the 99th read the
  1680-column map at `$31800`, found the scroll limit `$227b8` was only the first room's edge, and decoded
  the room-exit table (`$e0aa`) and spawn list (`$27200`) in one session
  (`reversing/impossamole/README.md`, "The level is one tile map of connected rooms").
- A fixed-length `kbd`/`mouse` hold shorter than the game's own poll cycle can silently never
  register at all, and the hero ending up where the maneuver would have left it is not proof the
  maneuver ran — a no-op can look identical to success when the test only checks position/damage.
  Impossamole's 94th pass held an up+right packet for 15,000 steps at nine idle delays and read the
  five delays that left the hero exactly where it started, undamaged, as a successful dodge; the 95th
  pass found (via a `watch` on the jump routine's own frame counter) that the jump never entered its
  entry point at all for those five — the packet was enqueued with no lead-in delay, and whether the
  game's own poll (period longer than the 15,000-step hold) happened to land inside that window
  depended on the idle delay's phase, which those five delays' phase excluded. When a test's "it did
  nothing" and "it worked as intended" outcomes can look the same from position/damage alone, watch a
  signal that only changes if the mechanism actually fired (a counter, a one-shot flag, a state
  transition) before trusting the outcome; holding for longer than one full poll cycle removes the
  ambiguity outright (`reversing/impossamole/README.md`'s "Known traps" section, 95th-pass entry).

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
- A `kbd`/`mouse` status byte is a raw level in RAM, not an edge-latched event: it holds whatever
  the last packet wrote until the next one changes it. A press-then-release pulse timed only by the
  `s <n>` gap between one packet's two bytes can land entirely between two of the game's per-frame
  polls and never register as "pressed" on the frame that actually checks it. Hold the pressed state
  for at least one full VBL frame (check `instructionsPerFrame`, ~12000-15000 steps typical) before
  sending the release packet when testing whether an input is read at all — a same-packet-timing
  pulse read as "this input does nothing" cost impossamole's world-select confirm a false negative
  for a full handoff (`reversing/impossamole/README.md`'s "Confirming a world" section).
- Before concluding a joystick/keyboard bit is not read in gameplay from a single-packet,
  single-frame test, check for a per-object "busy" flag that some games use to skip the whole
  per-frame input read on frames where the controlled object is mid-animation (impossamole's hero
  object, base+101), and hold/run for several frames past the packet, not just one, since the
  observable effect (a walk cycle, a state-machine transition) can take multiple frames to become
  visible even when the input was read correctly on the first one. A one-packet, one-frame test read
  impossamole's gameplay movement as unmapped for a full handoff before a busy-flag check and a
  longer run proved bits 0-3 use the exact same up/down/left/right layout as world-select
  (`reversing/impossamole/README.md`'s "Gameplay input" section).
- On the Mac, scratchpad data made on Windows lives on `gpubox` (`~/Documents/GitHub/Atari-St-Emulator`). scp fails
  there (its PowerShell profile errors); stream it: `ssh gpubox 'tar -cf - -C C:/Users/Dave/Documents/GitHub/Atari-St-Emulator/M68000/scratchpad <names>' | tar -xf -`.
- Ghidra 12.1 is at `C:/Program Files/ghidra_12.1_PUBLIC` (`support/analyzeHeadless.bat`); on the Mac at
  `~/Downloads/ghidra_12.1.4_PUBLIC` (natives built with `buildNatives`; 12.0 there lacks 17 functions).
  In Ghidra Java scripts write regexes as `"\\s+"`; `"\s"` is Java's single-space escape and
  silently matches no tabs.
