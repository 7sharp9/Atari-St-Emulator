# Cadaver: handoff

Updated 2026-09-30 by the 79th-pass session (the script-system architecture write-up and the event-producer scan), on top of the 78th-pass verb decode. Commits: see `git log` for `cadaver: 79th pass` and `78th pass`.

## Resume point

- Last work commit: `e7758cb` cadaver: 79th pass (doc and tool only; the handoff itself is the commit after it).
- Read `reversing/cadaver/secrets.md` first, "Object scripts": the new subsection "How the script system fits together" (three mechanisms, event queue, consumer, gate, verbs, where state lives, who pushes events), then "The script language" (block layout, IF/ELSE grammar, the 94-verb table, what the scripts do). Scripts are in `reversing/cadaver/py/secrets/overlay/` (table in `py/secrets/README.md`); all run from `M68000/` against `scratchpad/cadaver/gameplay_empire.snap` (CAVERN, level 0) or `scratchpad/cadaver/level1_loaded.snap` (level 1 loaded). Decoded scripts of both levels: `scratchpad/cadaver/secrets_out/scripts_level0.txt`, `scripts_level1.txt` (regenerate: `verb_decode.py [snap] --dump`); the producer scan writes `secrets_out/overlay/queue_producers.txt`; indexed in `scratchpad/ANCHORS.md`.
- No emulator source changed, so no rebuild or regression-net run is needed.
- Uncommitted and not this workstream's: `M68000/sessions/README.md` (a pre-existing line-wrap edit), `Cadaver/` (disk images), `.obsidian/`.

## Proven so far (counts in `secrets.md`)

Earlier passes (77th): main-loop keys, gold-priced saves, rank table overrun, assert layer, level code overlay and export table, the consumer `$00fdbc` and the 94-entry verb table at `$00ffba`, the LZHUF expander and two-level directory, the sound sequencer, day clock, RNG.

78th (item 1 closed):
- The verb grammar: 212 of 212 level-0 blocks and 264 of 264 level-1 blocks decode to exactly their `len`, end on `$17` and agree with every IF/ELSE length byte (`verb_decode.py`); 61 of the 94 verbs occur in the two levels.
- Operand lengths of 92 of the 94 handlers measured under `callcap` (`verb_lengths_callcap.py`: ok 99, bad 0); effects of 14 verbs plus the comparison ops (`verb_effects_callcap.py`: 45 of 45); object 2's script under the real consumer (`treasury_gate_live.py`, 3 of 3 runs).

79th (architecture; static, nothing driven):
- The system is written up as prose: three separate mechanisms (sound bytecode, native overlay code, object verb scripts), scripts are data on type-6 templates, events go through the one ring queue `304(A5)`, a block runs to completion in one consumer call, all state lives outside the script, scripts affect each other only by queueing events.
- `queue_producers.py` finds 48 push sites and 25 distinct events. From the producer bodies (*inferred*): 9 is physical contact (movement collision test), 5 the player's use action, 16 examine, 18 pick-up, 26/27 select, 23 kill, 8 the name banner (not a script event). Correction: event 5 was labelled "touched"; it was only ever proven by injection.
- Script blocks of both levels answer events 3 and 21, and no immediate-opcode push produces either.

## Open, in priority order

1. **Drive the player-action block `$00a3d0`-`$00a7d8` live** (use, examine, pick-up, select): it names the producers of events 5, 16, 18, 26, 27, and its pick-up half (`$00a6a6`, `move.w 4(A1),(A0)` into a free slot) is the lead for how the type-8 list is filled, which unblocks the treasury and every gate that tests it (verb 34). Prove it with `bpc` on the push sites while pressing the action key at an object, and `watch` on the list at `(A5)+96` type 8; then find the producers of events 3 and 21 (a register or computed opcode).
2. **Reach the rest of the game**: drive object 86 (room `$22`) and 84 (level 1) from their rooms by walking; walk level 1 with `level1_loaded.snap` and the 13 level-1 teleport scripts (`scripts_level1.txt`: rooms `$0c $22 $34 $46 $52 $55 $5b`).
3. **The Disk 2 builds**: decode the Disk 2 levels' scripts with `verb_decode.py` (needs a snapshot per level, made with `level2_load.py`; the 33 verbs neither level uses may occur there); overlays with two extra header words, a negative class-1 record, service table `$005eee` (29 entries), spell 28 as a real damage effect; the Empire `[t]` Disk 2 levels 3 and 5 look damaged (prefer Replicants).
4. **Verb semantics that are read, not run** (`secrets.md` "Open"): DELETE (0, 2), SHOW (1), GOANI/STOPANI/GOMOVE/STOPMOVE, the CREATE/PLACE family (36, 41, 44, 73, 84), the type-4 flag verbs (10, 27, 61), and verbs 9, 42, 60, 65, 66, 87, 88, 91. Prove each with a `callcap` memory delta as `verb_effects_callcap.py` does, or by running the level-1 scripts that use them (3, 4, 7, 11 are level-1 heavy).
5. The events the timer service and the engine code at `$00e8b2`-`$00fa62` queue (1, 4, 6, 7, 10-15, 17, 20, 24, 25, 28): what each means, by injecting it for an object that has a block for it.
6. The unfinished items in `secrets.md` "Open": F2/F3 effects, the escape-number lock (1044), the class bytes of type-6 templates, which sound ids fire in play, `$0115a2` (a rotating checksum nobody calls), whether XP 60,000 is reachable, the first-room-load writer check from a cold boot.
7. Older loose ends: the room-census oddities of mechanics.md §67 (slots 69 and 71 are probably not rooms), STOPACTI's `$f8ba`, the sconce's art source, the tile-stack direction (graphics.md 5e).

## Known traps

- An event or opcode named after the value you injected is not the name of what the game queues: name it from its producers. Event 5 sat as "touched" for a pass for that reason.
- `cadaver.sym` labels are the nearest symbol below an address, not a routine boundary: `QueueEntityIntoRing304_AndSetField2271_Direct` covers `$00e854`-`$00fb..` and `StatsScroll_RankTable176A5` covers `$00a1..`-`$00a7..`, both far past what the names say. Read the code, not the label.
- `tools/disassemble.py` takes bare hex arguments (`--all a3c0 a430`, no `0x`, no `--help`). macOS awk has no `strtonum`; use Python for hex ranges.
- A callcap that "does not return" is usually a fatal assert on the poked state: verbs 8 and 75 assert unless the id is in the creature list at `396(A5)`, verb 29 needs A4 in valid RAM, verb 79 with lo = hi divides by zero (`$011544`). Seeds are in `verb_lengths_callcap.py`/`verb_effects_callcap.py`.
- `callcap`'s `regdelta` shows A1 as `$snapshot->$final`, not relative to the preset: measure `final - preset`.
- Script operand bytes are hex in the dump but object ids print decimal (`#16`); the message text of verbs 28 and 72 is looked up through the packed table, so a stale snapshot prints `?`.
- The type-8 list is empty at CAVERN start (64 index words at type-8 descriptor +0, 4-byte data records `[id][+2]`); the four regalia have to be poked or acquired.
- Earlier traps still standing: a literal-pointer hit dismissed as alignment coincidence needs the real table base; a direct-call scan does not cover tables loaded per level; a "key does nothing" verdict must watch the handler's branches and flags (CLAUDE.md).

## Next session

`/resume cadaver` and start with open item 1: at an object in CAVERN, `bpc` the push sites of `$00a3d0`-`$00a7d8` while sending the action key (make, 40,000+ step hold, break) and read which event each key produces; pick up an item with `watch` on the type-8 list. Then walk to lever 86 and lever 84, and run level 1's teleporter chain from `level1_loaded.snap`.
Prompt: `/resume cadaver`.
