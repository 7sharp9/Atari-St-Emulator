# Cadaver: handoff

Updated 2026-09-30 by the 81st-pass session (room-record script blocks decoded; the regalia-to-treasury path driven with natural input).

## Resume point

- Last work commit: see `git log` for `cadaver: 81st pass` (the room-script decode is `b3ff4c6`; the regalia walk, its docs and this handoff are the commit(s) after it).
- Read `reversing/cadaver/secrets.md` first: "Object scripts" > "How the script system fits together" (producer table, now with rows for events 6, 14, 15/17, 24, 28), "The player's action panel" (ends with "The regalia walk"), "The script language" and the new "Room scripts".
- Scripts: `reversing/cadaver/py/secrets/overlay/` (table in `py/secrets/README.md`); new this pass `room_blocks.py`, `room_regions.py`, `room_events_live.py`, `action/regalia_walk.py`. All run from `M68000/` with `uv run` or `.venv`, against `scratchpad/cadaver/gameplay_empire.snap` (CAVERN, level 0) or `level1_loaded.snap`. Decoded room scripts: `scratchpad/cadaver/secrets_out/room_scripts_level0.txt`, `..._level1.txt` (indexed in `scratchpad/ANCHORS.md`). Walk snapshots and logs: `scratchpad/cadaver/secrets_out/action/rw/`, `rw_full.log`, `rw_finish.log`.
- No emulator source changed: no rebuild or regression-net run needed.
- Uncommitted and not this workstream's: `M68000/sessions/README.md` (a pre-existing line-wrap edit), `Cadaver/` (disk images), `.obsidian/`.

## Proven so far (counts in `secrets.md`)

Earlier passes (77th-80th): main-loop keys, saves, rank table, assert layer, level code overlay and export table, the consumer `$00fdbc` and the 94-entry verb table, the verb grammar, the sound sequencer, the three-mechanism architecture, the player action panel driven live, 65 verbs measured.

81st, room scripts:
- Every block `len` is even; a 1-byte pad follows a block whose content through `$17` is odd (room pads are uninitialised, object pads happen to be `$17`). 212 + 264 object and 59 + 90 room blocks (`room_blocks.py`, `pad` rule).
- Room record: byte 0 = offset of the region list = end of the blocks (72/72, 97/97); byte 31 = block count, blocks at `+$20`; region list = count byte, zero byte, N six-byte records, present exactly when byte 23 has bits 1 and 4 (11/11, 24/24); all 27 + 37 event-15/17 gates lie in 1..N (`room_regions.py`).
- Room events: 28 = first entry (`$00e8a6`, latched by byte 23 bit 6), 6 = every entry (`$00eae4`), 14 = periodic room tick (byte 2 is the period), all live in `room_events_live.py` (28: 1,1,0,0; 6: 1,1,1,1; room 28's first-visit block ran verb 36 three times once; room 37's one-shot block paid 26 XP once; 34 timer passes, 2 pushes, 2 creates in 14M steps). 15/17 = an object overlapping region D7 (consumer half live, the overlap itself read); 24 = a cast spell (gate = spell id; read only). Level 1's SLEEP puzzle rooms give the stub spell its effect.
- 8 verbs the verb table shows with 0 / 0 uses occur in room blocks; 25 verbs are used by no block in either level.
- Regalia walk (`action/regalia_walk.py`, two identical runs): entry into room 33 injected, then natural input takes 28 (`L`), 16 (`UR`), 26 (`RUL`) with icon 2, walks `LDLUR` through rooms 32 and 34 to the BUTTON, icon 4 (`$00a43c` to `$00a486`, event 5) runs its script (34 x4, 58, 70, 37, 41 x4), room 34 to 37, XP 0 to 26. Decoys 25 and 29 are takeable too.

## Open, in priority order

1. **Regalium 32 (the circlet)**: not reachable by the probe; its box lies inside the large object 31's. Prove how it is obtained (a probe from a partial hold rather than a walk to a stall; object 31's or 32's z; the collision search `$008870` order; whether another route, room or creature carries it). `regalia_walk.py search 32` with finer moves is the start.
2. **Drive events 15/17 and 24 naturally**: walk into CAVERN's region 1 (room 0, hero: event 15, `HEALTH -1`; another object: event 17) and watch `$0092b4`/`$0092da`; cast SLEEP in level 1 room 1 (`$00f0a0`, gate `$17`). Also decode what the region records' six bytes are (bounds by the test at `$009160`), and byte 23's other bits.
3. **The trek from CAVERN to room 33** (and lever 86 / lever 84 the same way): only the entry into room 33 is injected. The rectangle adjacency of `world_map.py` is not the door graph; a natural BFS as in `regalia_walk.py` from `gameplay_empire.snap` would find the door path, with combat and hazards on the way.
4. **Events 18, 26 and icons 3, `$e` naturally**: walk to a class-8 chest (ids 83, 224 and others) and the class-`$c` object (id 70); a subclass-5 chest gives icon 3.
5. **Reach the rest of the game**: walk level 1 from `level1_loaded.snap` through its 13 teleport scripts (rooms `$0c $22 $34 $46 $52 $55 $5b`) and its room blocks (captors that talk, room 87's disarming, room 88's level exit).
6. **The Disk 2 builds**: decode their levels' scripts and room blocks (a snapshot per level from `level2_load.py`); overlays with two extra header words, negative class-1 record, service table `$005eee`, spell 28.
7. **Still read, not run**: verbs 56 and 90, verb 44's class-bit-7 branch, verb 41's collision search; producers of events 1, 4, 10-13, 25; the class handlers reached through verb 66 other than class 10.
8. Older loose ends in `secrets.md` "Open": F2/F3 effects, the escape-number lock, class bytes of type-6 templates, which sound ids fire in play, `$0115a2`, whether XP 60,000 is reachable; mechanics.md §67 census oddities, STOPACTI's `$f8ba`, the sconce's art source, the tile-stack direction (graphics.md 5e).

## Known traps

- A queue entry is 8 bytes (`op.w`, `ptr.l`, `word.w`), 12 with bit 15's fourth long. Advancing the write pointer `304(A5)` by 10 misaligns the ring: later entries read as opcodes inside pointers (`A0 = $401c0006`) and look like unmatched events.
- `verbs2/h.py real()` overwrites object 2's first block, and object 2 is the treasury BUTTON: every snapshot taken afterwards presses the scratch script, not the treasury (the first regalia run "teleported" to room 33 and paid no XP). Set `h.owner = 86` (any unrelated event-5 object) as `regalia_walk.py` does.
- Room blocks end on a pad byte that is not `$17`: do not reuse `verb_decode.collect()`'s `$17`-at-`len-1` filter on them, and do not cap `len` (room 11 of level 1 is one 122-byte block).
- `Tally.run` counts only `KEYSITES`; add verb-handler addresses to that list (in place) to see them during `pick_icon_id`, and steps run with a bare `r.cmd('s N')` are invisible to `hits`.
- The fire probe returns the first object in list order at the probed point: an object whose box lies inside another's (regalium 32 in object 31) is not reachable that way.
- The type-8 index format the game writes is `[flag 4][offset 4*slot]`; `treasury_gate_live.py` pokes flag 1 and works, but use 4 for a natural-looking list.
- Earlier traps still standing: name an event from a live drive, not from the producer body; the REPL prints at most 4096 lines (write callcap output to a JSON out-file); joystick fire is one `kbd ff 80` command; object ids read after an action can be wrong (a DELETE compacts the resource block); a `callcap` of verb 66 with a class other than 10 kills the REPL; `cadaver.sym` labels are nearest-below, not routine boundaries; `tools/disassemble.py` takes bare hex arguments; verbs 8 and 75 assert unless the id is in the creature list, verb 29 needs A4 in valid RAM, verb 79 with lo = hi divides by zero; zsh does not word-split an unquoted variable.

## Next session

`/resume cadaver` and start with open item 1 (regalium 32) and item 2 (drive events 15/17 in CAVERN region 1 and cast SLEEP in level 1 room 1), then item 3 (the natural trek from CAVERN to room 33 by a BFS over door walks).
Prompt: `/resume cadaver`.
