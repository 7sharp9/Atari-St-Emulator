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
- Emulator hot path (`M68000/DEVELOPING.md`, "Performance"): a new decoder's `printfn`/`sprintf` goes
  behind `if Trace.enabled`, per-step constants stay literals, new active patterns are struct
  `ValueOption`. `selftest` runs the flat bus and does not exercise the MMU RAM fast path, so an
  MMU change is gated by the 30M snapshot compare plus a game snapshot compare. A speed claim needs
  an interleaved A/B of two builds: a change that cut allocation 30% (struct `ResolveEa`) was 7% slower.
- **`tools/rdis.py` is not a whole-program listing.** It does not follow `lea T(PC),A0 / movea.l 0(A0,D0.w),A0 / jsr (A0)` longword state tables (they print as `ori.b` garbage), so every handler body behind one is missing: for Crude Buster it missed 67 of 94 sound-command callers and the first scan of a flag found no writer. For "who writes X / who calls Y" use a raw scan of the image or `tools/disassemble.py --rom <img> --base 0 --all <lo> <hi>` (code only: stop where code ends).
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
- Name a routine's role from its own body, not from where it is seen running: Impossamole's `$1c6de` was called "the shared depacker" for many passes because
  PC was seen at `$1c68e` during resource reloads (the tail of the VBL wait loop next to it); its first instructions are `Fopen` (`move.w #$3d`, `trap #1`), it is a file loader, and the depacking is a crack hook in low
  RAM (`reversing/impossamole/secrets.md`). Read the routine to its first branch before writing its role into a doc, and grep for such a label before reusing it.
- Name a table's contents by matching its entries against an independent record set, not by what its seeder or first reader is
  called: PowerMonger's `$4d252` was documented as herded animals for sixty passes; 203 of 203 live entries sit on byte6-4
  (tree) render records, none on the animal records, and the men working it are of every job, not shepherds
  (`reversing/powermonger/economy.md` §2, `py/tree_census.py`). The same applies to a mode or flag named from one observed user.
- Before naming a byte field from how code uses it, read the UI selector that prints it: the panel text tables in `$9000..$b000` (`$9ccc`, `$9c80`, `$90ca`, `$9d52`...) return a string
  pointer in A5 and are the developers' own words. PowerMonger's building kind 7 was "capital" for sixty passes; `housenam` at `$a15a` says WorkShop, the lord kind byte says Village/Hamlet/Town/City/
  Capital/Base, category 8 says Sheep, and the loyalty line is a constant (`reversing/powermonger/strategy.md` "The game's own text"). `py/doc_coverage.py` lists the routines no doc cites.
- A census column (class, type, kind) is only as good as the table the game's own routine reads it from: before building conclusions on one, find the game's reader of that field (here the
  description routine `$011066`) and check one live object against it. Cadaver's `item_census.py` read the class byte from the wrong record for four passes and named a potion "the MASSACRE scroll"
  and three stone-ammunition templates "magic missile scrolls", which scoped the dragon search around weapons that did not exist (`reversing/cadaver/mechanics.md` 76).
- When a session decodes a graphics asset for the first time (spritesheet, tileset, icon/panel
  art, palette) well enough to render it, commit the rendered image (PNG) alongside the doc that
  proves the format, not just a prose description or an untracked scratchpad file — future
  sessions and Dave need to see the asset without re-running the decode. Table-index it in
  `graphics.md`/the README's files table the way screenshots already are.
- Every behavioural claim about a game needs an emulator check (callcap diff, frame capture or
  screenshot diff) with a match count, or is labelled inferred.
- A door-graph or dataflow chain ("walk through door X, operate Y") is a hypothesis about geometry, hazards and one-way doors: drive each leg before building on it. Cadaver's 91st-pass
  137-action chain looked closed; the 92nd pass's first natural drive (`l1/route_level1_room89.py`, 46 legs, 40 s, `l1/explore.py`) found eight gates in the first twelve rooms (a lever for the
  pillars, a lever puzzle in front of a door, a trap region only a SLEEP cast clears, a lever on a shelf with no stairs, four tokens behind a slot) and a health budget the graph did not
  have (`reversing/cadaver/mechanics.md` 81). A hold that stalls, a room change that bounces back, or a health drop that arrives legs later (a POISON bite: check `2434(A5)`) is geometry
  or timing to read, not a dead end.
- A verb/opcode table named from reading its handler bodies is a hypothesis: call each handler under
  `callcap <addr> <steps> - A1=<scratch script> ...` (the `regdelta` line gives the final A1, so the operand
  length; the `mem` lines give the effect) and tile the whole script corpus with the grammar. Cadaver's 78th
  pass read verb 5 as "XP += n" and comparison op 2 as `!=`; both were wrong (`$0102e0` overwrites D0 with the
  sound id before the add; op 2 is `==`), found only by the live checks (`py/secrets/overlay/verb_effects_callcap.py`).
  A `callcap` that "does not return" is often a fatal assert on the poked state (e.g. an id missing from a
  list), not a hang: read the handler's error block before giving up on the check.
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
  whole-image listing: it can be truncated (Populous's `pop_ad58.asm` stopped at $1d462, short of
  the text segment's end at $21464: about 18% of the code, the last 4,500 lines, with no warning in
  the file itself; `$3d550` is the end of data and bss, not of code). Grepping it found no writer
  for two addresses and called them dead code; both writers were in the missing tail (`$02004e`,
  `$01fbc4`), found only by rerunning `find_field_writers.py`/`disassemble.py --all` fresh. Before
  trusting a "no writer" result from any pre-existing `.asm`/`.c` file, confirm its last address
  reaches the end of the text segment (the PRG header's text size), or just re-run the tool.
- A writer scan by operand text (`find_field_writers.py "148(A3)"`) cannot see a block clear or copy
  (`lea $3f364,A0 / clr.l (A0)+` loop) that reaches the field from a lower base. Before "display only"
  or "only writers X and Y", poke a marker into the field, run the land build, and `watch` it if it
  vanishes; PowerMonger's group aggression rank had a third writer, `$10768`, found only that way
  (`py/aggr/scan_block_writers.py` lists such loops).
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
- "No natural entry" / "never reached" holds only for the world-build roll and the address list it was measured with. PowerMonger's `$3248`, `$38ce`, `$6128` and `$5fa0` were
  "synthetic only" through every preview-roll run (`$5809c` non-zero); 59 Play Random Land snapshots (`PAGES0=1`, the roll a real random land runs with) hit them 101, 3, 1 and 28 times
  (`py/cmdai/census.py`, `strategy.md` "The order senders"). A census file with no line for an address says "not looked for", not zero: check the address list before writing "never".
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
- A `find_literal_ptr.py` hit written off as a "byte-alignment coincidence" needs the real table base
  from the code that installs the table, not from the neighbouring bytes: read the `move.l #<base>,<field>`
  and the routine that indexes it, and try both 2-byte alignments. Cadaver's 75th pass dismissed the raw
  bytes `$00010974` at `$0060a2` because the region looked like 4-byte-aligned `(word, word)` pairs from
  `$006080`; the table is the level overlay's engine export table, installed at `$00b5ec` as
  `move.l #$6082,392(A5)` (2 mod 4), and `$0060a2` is its entry 8, the very teleport verb the section then
  called unreachable (`reversing/cadaver/secrets.md`, `py/secrets/export_service8.py`). The hit was
  "even" in the tool's own output, which already ruled out an odd-alignment splice.
- "No caller anywhere" from a whole-image scan means no direct `bsr`/`jsr`/`jmp`; a block whose routines all
  read as uncalled is usually reached through a pointer table loaded per level (an overlay with an export or
  dispatch table). Look for the routine that does `movea.l <field>(A5),A6 / jmp (A6,Dn)` before writing "dead".
  And a keyboard "does nothing" verdict must watch the handler's own branches and flag bytes, not one output:
  Cadaver's 9th pass drove every `$01616c` dispatch id and watched only the player descriptor, while the
  main loop's own handler at `$006ba2` (pause, map, save, load, F2-F4 toggles) read the same key cell unseen.

## Proving routines with parallel subagents

What made the PowerMonger 122nd pass's three parallel proofs work, and what went wrong:
- Name the tool index in the brief (`M68000/DEVELOPING.md` "Other tools"): six Final Fight agents each wrote their own recursive-descent lister because
  `disassemble.py --all` loses sync over interleaved jump tables and animation data; it is now `tools/rdis.py`.
- One shared `BRIEF.md` in the working dir. Take its addresses, strides and struct offsets
  from the code (`tools/pm_common.py`, `tools/pm_fsm_ref.py`, the docs' proven sections), never
  from memory: that brief got the object table wrong, and every agent had to correct it.
- Subagents cannot write `report.md` (the tool refuses). Ask for the report as the final
  message and save it yourself into the agent's directory.
- Put addresses and symbol names in the BRIEF, not roles: all four PowerMonger 140th-pass area briefs
  gave a role read off the symbol names ("map and road drawing", "panel builders", "PSG music engine",
  "shifters", "soldier draw") and every agent found it wrong (terrain build with roads as causeways, panel
  templates, a Timer A sample player, masked sprite blitters). Write "role unknown: name it from its body".
- Corpus capture: `tools/capture_hits.py`. `callcap` runs with interrupts masked, so a routine
  that plays a sound waits forever on a flag the interrupt clears (PowerMonger: poke `$2c993`
  to 0 in the state).
- After the agents' reports, resume each one with `SendMessage` for the merge work instead of redoing it: promote its scripts to `reversing/<game>/py/<area>/`, rerun its gates from there with fresh callcaps, and edit the topic docs for its own findings (it knows which sentences it contradicts; four agents editing the same docs with small unique-string `Edit`s did not collide, PowerMonger 141st). Lift the "write only under your directory" rule for exactly those paths. Name a promoted directory anything but `build/`: `.gitignore` ignores it and the scripts silently stay untracked (`py/worldbuild/`).
- `callcap` presets are hex (`D0=10` is `$10`, slot 8 not slot 10), and a routine listing that starts two bytes early turns its opening `movem.l` push into "no matching push, not callcapable": both made an agent report a wrong finding (fsm15, `$1699e`) before its own recheck retracted it.
- Tell agents to derive the repo root from `__file__` (or `M68000_ROOT`), never a literal `/Users/...` path, and to keep their temp files in one named scratchpad dir: both Cadaver 80th-pass agents hardcoded their own scratch dir and `M68000/`, so every script needed patching before it could live in `reversing/<game>/py/`. Promotion changes the directory depth too: Crude Buster's seven agents' fixed `../../../../..` chains all broke when their dirs moved from `scratchpad/<game>/agents/<x>/` to `reversing/<game>/<x>/` (35 files re-patched), so tell agents to locate the root by walking up to the directory that holds `tools/rdis.py` (or `M68000_ROOT`), not by a fixed `../` count. Also tell them to append injected ring-queue entries at the write pointer `304(A5)` (advance it by 8, `1154(A5)` += 1): an entry written at `152(A5)` alone is overwritten by the game's own pushes in level 1.
- Cadaver 91st pass (four agents plus a review, one doc merge): seed the topic doc with one placeholder heading per agent before resuming them to merge, and tell them to use `Edit`, never a whole-file rewrite (one did, and could have clobbered the others' concurrent edits; check every agent's section is still present afterwards). Re-run two or three of their gates yourself from the promoted paths before committing. Two of their briefs' claims were wrong (a record's byte names, "type-8 id is the template index"): agents correct the brief when told the code wins.
- When two agents transcribe the same callee, keep one version and run both corpora against it:
  that cross-check is free.
- Before merging: re-run every gate from fresh callcaps (no `reuse`), merge the transcriptions
  into the game's reference module, move the gates to `reversing/<game>/py/` (corpora stay in
  scratchpad, listed in `ANCHORS.md`), then run all older gates of that module again.

- Chaining segment scripts: a leg that costs nothing in its own agent's run is proven only for that lineage's creature phase. Roaming
  creatures (Cadaver rooms 38 and 39) move as a function of the steps spent inside their room, so a fixed wait is a lottery that differs
  per lineage: E2's room 38 walk cost 0 in its own run and 24 when the parent ran it from the real hand-off snapshot. Before merging, run each
  segment from the previous segment's actual end snapshot, then the whole chain twice and `cmp` every snapshot (Cadaver 88th pass: 427
  identical). Wait by reading the creature table (`overlay/action/exit_level0/g2/f1/route_cross38.py`), not by counting steps. A check that
  an id is "selected" must read the game's own item word (`1236(A5)`), not the cursor cell: with six or more items the Return grid's cursor
  names a different item than the one FIRE opens.

## Shell pitfalls on this machine

- Git-bash `sed -i` rewrites a CRLF file with LF endings (`Program.fs` is CRLF), turning a
  one-line change into a whole-file diff. Edit such files with the Edit tool, or in Python
  opened in binary, and read `git diff --stat` before staging.

- `watch <addr>` on an odd byte misses a word or long write that covers it (`MMU.fs` `checkWatch` tests only the write's start address; reproduced 16 hits on `$18318`, 0 on `$18319`) and all FDC DMA writes: before writing "nothing writes X", also watch the even byte below, and read the writers in the listing. macOS has no `timeout`: `... | timeout 60 dotnet ...` fails before running and a following `grep -c` prints 0, the same as "no hits"; run without it and read the first lines of output.
- REPL `w <addr> <8 hex digits>` writes a 4-byte longword: poking a one-byte field clobbers the next three. Impossamole's `w bb74 12120300` (health) also set the
  world index `$bb76` to 3 and zeroed the shop flag `$bb77`; read the neighbouring fields and write the whole longword deliberately.
- zsh reads `$f:name` as `$f` plus a history modifier (`:e` is the extension): `CB_SAVEAT=$f:e_l2` silently became an empty value and no state was saved. Write `"${f}:name"`. `cbmame.sh` changes into the run directory, so its script argument must be an absolute path.
- A long-running driver script (a bot) edited in place loses the versions that worked: the Crude Buster `natbot.lua` reached level 5's last screen in one state and stalled at level 5's first fight in the next, and the earlier state was not kept. Copy it aside (or commit) before each behaviour change and re-run the level that last cleared.
- zsh aborts a whole `for f in a/*.md a/*.sh; do ...` when one glob matches nothing (`no matches found`), so the loop body never runs: run such loops with `bash`, or `setopt nonomatch`.
- Bash heredocs and inline `python -c` mangle backslashes (Windows paths, `\AUTO\`, regexes).
  For text containing backslashes use the Edit/Write tools, not shell string surgery.
- The Bash tool's working directory drifts between calls: `cd` to an absolute path first. zsh also reads an unquoted `GR:x>=24` as a redirect to a file named `24`: quote REPL and `explore.py` words that contain `<` or `>`.
- zsh (the Mac shell) does not word-split an unquoted `$VAR`: a variable holding several REPL tokens
  arrives as one malformed line and the REPL stops there. Pass tokens separately. `echo =====` fails
  in zsh (`=word` expands to a command path); quote it.
- In a REPL drive the click is consumed during the settle after `mouse down`: start `hits` or
  `bp` before the down, or the census misses the handler.
- `hits <n> <addrs>` after a `bp` that stopped the run counts only what happens after the stop: a routine that ran before it reads "0 hits", which looks like "never called" (PowerMonger 142nd: `$13ece`, `$b85a`, `$b2dc` read 0 after a `bp 10d1e`; run `hits` from the end of the click, before any `bp`, to count a whole route).
- `grep -r` from `M68000/` walks the multi-GB `scratchpad/` and blows the 120 s tool timeout: name the directories (`reversing/ tools/ sessions/`) or pass `--exclude-dir=scratchpad`.
- A `kbd`/`mouse` status byte is a raw level in RAM, not an edge-latched event: it holds whatever
  the last packet wrote until the next one changes it. A press-then-release pulse timed only by the
  `s <n>` gap between one packet's two bytes can land entirely between two of the game's per-frame
  polls and never register as "pressed" on the frame that actually checks it. Hold the pressed state
  for at least one full VBL frame (check `instructionsPerFrame`: ~12000-15000 steps on an idle screen, but ~24,000 in impossamole's gameplay rooms, so 30,000 is the safe hold) before
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
- A game that polls the keyboard ACIA data register directly (`cmpi.b #$39,$fc02.w` / `bne` back) never sees a key here: `MMU.fs` pops the FIFO on a read of `$fffc02` and returns 0 when it is empty, so TOS's keyboard ISR (still installed at `$118`) takes the byte first; a real 6850 keeps the last byte. Black Tiger's cracktro `$a562` and trainer menu `$c658` both stall this way. Bypass with a labelled `w` poke of the branch in the drive script (`reversing/black_tiger/drive.txt`); the real fix is an emulator change behind the regression net. Check the game's own key service (TOS Bconin vs direct ACIA) before assuming input is broken.
- Ghidra 12.1 is at `C:/Program Files/ghidra_12.1_PUBLIC` (`support/analyzeHeadless.bat`); on the Mac at
  `~/Downloads/ghidra_12.1.4_PUBLIC` (natives built with `buildNatives`; 12.0 there lacks 17 functions).
  In Ghidra Java scripts write regexes as `"\\s+"`; `"\s"` is Java's single-space escape and
  silently matches no tabs.
