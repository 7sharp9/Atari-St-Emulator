# Cadaver: handoff

Updated 2026-10-01 by the 82nd-pass session (the regalia walk now has no poke; CAVERN's region events and a SLEEP cast driven live; the TUNNEL lever operated from its icon panel).

## Resume point

- Last work commit: see `git log` for `cadaver: 82nd pass` (regalium 32, regions and SLEEP cast, the lever); the skill lesson is `8dfce89`; this handoff is the commit after it.
- Read `reversing/cadaver/mechanics.md` §71 first (the lever, `$ffff`/0 door word, jumping), then `secrets.md` "The player's action panel" (ends with "The TUNNEL lever" and "The regalia walk") and "Room scripts".
- Scripts (all from `M68000/` with `.venv`, table in `reversing/cadaver/py/secrets/README.md`): new this pass `overlay/action/lever_operate.py [operate|control|jump]`, `overlay/action/regalia_walk.py [jump32|full]`, `overlay/room_regions_live.py [walk|bounds|obj]`, `overlay/cast_sleep_live.py [control]`. Door data: `scratchpad/cadaver/secrets_out/door_walk_level0.txt` (`py/door_walk.py gameplay_empire.snap`). Snapshots under `scratchpad/cadaver/secrets_out/action/` (`rw/` regalia, `lever_before.snap`, `lever_after.snap`, `lever_jump.snap`).
- Start from: `scratchpad/cadaver/room2_tunnel_entry.snap` (TUNNEL, hero (20,12,14,6)) for the trek, `gameplay_empire.snap` (CAVERN) for the rest, `level1_loaded.snap` (level 1, room 0).
- No emulator source changed: no rebuild or regression-net run needed.
- Uncommitted and not this workstream's: `M68000/sessions/README.md` (a pre-existing line-wrap edit), `Cadaver/` (disk images), `.obsidian/`.

## Proven so far (counts in the docs)

Passes 77-81: main-loop keys, saves, rank table, assert layer, level overlay and export table, the consumer `$00fdbc` and the 94-entry verb table, the verb grammar, the sound sequencer, the player action panel, 65 verbs measured, room-record script blocks (149 of 149), events 6/28/14 live, the regalia walk with natural input.

82nd pass:
- **The lever works** (`lever_operate.py`): from the stall one step short of it the probe returns (144, icons 7, 11, 6); fire opens the panel, icon 7 confirmed runs its event-5 block, door descriptor `$6d4f2` id word `$ffff` -> 0, lever byte 3 0 -> 1, Up then reaches room 2 and Left room 3; control without the panel stays in room 1. The word is read at `$00716e`-`$007182` (0: resolver, `$ffff`: sound cue). This retires §7, §10d and §20-§29's "no input opens it".
- **Jump**: fire with nothing in front starts a jump (z base 5, 10, 14, 18, ... peak 34 when held long enough, one frame per delta, the arc starts about 55,000 steps after the press, written by `$0070e8`); a mover whose z base equals an object's top z reaches `$008a02` and queues event 9 every frame (`lever_operate.py jump`: 11 pushes, lever untouched).
- **Regalium 32** is on top of object 31 (z 18..31 on 0..17): jump from 60,000 steps back, land on 31, `U`, probe returns (32, icons 2 10 11 6), TAKE gives record (32, 22). `regalia_walk.py full` (32 first, then 28, 16, 26 by `DUL`, `UR`, `RUL`, then the BUTTON by `LDLUR`): room 34 -> 37, XP 0 -> 26 with no poke; two runs byte-identical.
- **Regions** (`room_regions_live.py`): record = (x_lo, y_lo, x_hi, y_hi, z_lo, z_hi), inclusive overlap of the mover's `[trail, lead]` box; CAVERN region 1 by natural walking: 3 pushes, 3 health; D7 and first-contact step at three bounds; event 17 for a poked object: 1 push, 1 PLACE, object leaves the room.
- **SLEEP cast** (`cast_sleep_live.py`): level 1 room 1, event 24 pushed once (`$00f0a0`), XP 0 -> 26, object 659 byte 3 0 -> 1, three creature records at `1266(A5)`; control all 0.
- Door switches (*read*): verb 10 CLEAR FLAG names the door in 9 level-0 blocks: `$33` object 144, `$18` object 81 (event 18), `$23-$26` object 239 (event 18), `$09` object 391, `$29` object 486, `$14` object 458; 11 level-0 doors start with the `$ffff` word (`$09 $12 $18 $1c $22 $23 $24 $25 $26 $29 $33`); `$12`, `$1c`, `$22` have no clearing script in object or room blocks.

## Open, in priority order

1. **The trek from CAVERN to room 33** (rooms 0, 1, 2, 6, 7, 12, 13, 15, 16, 30, 31, 32, 33 on the rectangle graph): the lever opens `$33`, which makes {0, 1, 2, 3, 6, 7, 9, 10, 11, 70} reachable; the next gates are `$22` (room 7 to 12, no clearing script found: what opens it? read room 7's blocks and the level overlay, or find the writers of `$6d46a`+2 with `find_field_writers.py`) and, later, `$18` (room 15 to 16, object 81's event 18: which item is applied to it). A natural BFS as in `regalia_walk.py` from `lever_after.snap` (walk rooms 2, 3, 6, 7) with combat and hazards on the way; the five `always-miss` generic-lookup doors (`$20 $2a $31 $3b` and one more, CAVERN's east door `$3b` among them) are not yet shown to be passable.
2. **Event 18 doors by natural input**: object 81 (`$18`), 239 (`$23-$26`), 391 (`$09`), 486 (`$29`, the crown gate), 458 (`$14`): find which item is applied (icon list of each object, `probe`), walk to it, confirm the icon, and watch the descriptor word and a walk through (as `lever_operate.py` does).
3. **Events 18, 26 and icons 3, `$e` naturally** (class-8 chests ids 83, 224; class-`$c` id 70): the lever showed the panel route needs no poke.
4. **Event 17 by a natural mover**, spell scroll and entry into level 1 room 1 without injection, byte 23's other bits (0, 2, 3, 5, 7), the regions' upper and z bounds.
5. **Reach the rest of the game**: walk level 1 from `level1_loaded.snap` through its 13 teleport scripts and room blocks (room 87's disarming, room 88's level exit).
6. **The Disk 2 builds**: levels' scripts and room blocks (`level2_load.py`); overlays with two extra header words, negative class-1 record, service table `$005eee`, spell 28.
7. **Still read, not run**: verbs 56 and 90, verb 44's class-bit-7 branch, verb 41's collision search; producers of events 1, 4, 10-13, 25; class handlers reached through verb 66 other than class 10; the jump's table (`$5ce6`/`$5d09`/`$5cc3`, state `2266(A5)`), `$006f80` (jump start).
8. Older loose ends in `secrets.md` "Open": F2/F3 effects, the escape-number lock, class bytes of type-6 templates, which sound ids fire in play, `$0115a2`, whether XP 60,000 is reachable; mechanics.md §67 census oddities, STOPACTI's `$f8ba`, the sconce's art source, the tile-stack direction (graphics.md 5e).

## Known traps

- **"No input opens X" needs every icon of the object's panel confirmed and the z axis checked** (now in the reverse-engineer skill): the lever cost 20 passes. `probe` returns the icon list; `pick_icon_id` confirms one; run a no-panel control from the same snapshot.
- Fire is both the probe and the jump: with an object in front it opens the panel, with nothing in front it jumps (starts about 55,000 steps later, keeps running after release). `drv.walk` stops on an unchanged x/y, so it can end mid-jump or mid-fall; read z (`0x3833c`) as well.
- The placement table at `56(A5)` (stride `$46`) starts with the hero (index 0); rectangle bytes 0-3 are (x lead, y lead, x trail, y trail), z top/bottom are bytes 4/5; room-local coordinates (0..79). The mover's entry flag byte is entry + 49.
- A queue entry is 8 bytes (`op.w`, `ptr.l`, `word.w`), 12 with bit 15's fourth long. Advancing the write pointer `304(A5)` by 10 misaligns the ring.
- `verbs2/h.py real()` overwrites the owner object's first block (object 2 by default, the treasury BUTTON): set `h.owner` to an unrelated event-5 object (`regalia_walk.py` uses 86, `cast_sleep_live.py` searches level 1 for one).
- A cast reads the spell at the item's body, `A2 = record + byte 12` of the record, not at the record start (`cast_sleep_live.py`); poking `inst + 0` works only when byte 12 is 0.
- `watch` prints to stderr: read `Repl.err`, not `cmd()`'s output.
- Room blocks end on a pad byte that is not `$17`; do not cap `len`.
- `Tally.run` counts only `KEYSITES`; steps run with a bare `r.cmd('s N')` are invisible to `hits`.
- The type-8 index format the game writes is `[flag 4][offset 4*slot]`.
- Earlier traps still standing: name an event from a live drive, not from the producer body; the REPL prints at most 4096 lines; joystick fire is one `kbd ff 80` command; object ids read after an action can be wrong (a DELETE compacts the resource block); a `callcap` of verb 66 with a class other than 10 kills the REPL; `cadaver.sym` labels are nearest-below; `tools/disassemble.py` takes bare hex arguments; verbs 8 and 75 assert unless the id is in the creature list, verb 29 needs A4 in valid RAM, verb 79 with lo = hi divides by zero; zsh does not word-split an unquoted variable.

## Next session

`/resume cadaver` and start with open item 1: from `scratchpad/cadaver/secrets_out/action/lever_after.snap` (the lever operated, hero in TUNNEL) walk Up into room 2 and on toward room 7 with a BFS over walk-to-stall holds, find what opens door `$22`, and continue toward room 33; do item 2 (the item that opens `$18`, object 81) as the gate appears.
Prompt: `/resume cadaver`.
