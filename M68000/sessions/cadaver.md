# Cadaver: handoff

Updated 2026-10-01 by the 83rd-pass session (door id words are keys; the walk from CAVERN to room 16 by natural input; the script census repaired).

## Resume point

- Last work commit: `61db170` (`cadaver: 83rd pass -- event 18 by natural input ...`); before it `c52ea62` (keys, `route_to_room12.py`, `verb_decode` fix) and the skill lesson `a1ebeaf`; this handoff is the commit after them.
- Read `reversing/cadaver/mechanics.md` §72 (door id words, the corrected door table, the walk to room 12) and §73 (event 18 by icon `$c`, the pickaxe wall, keys 240/155/104, room 16), then `secrets.md` "The keyed doors and the walk to room 12" and "Applying an item (event 18)".
- Scripts (from `M68000/` with `.venv`, table in `reversing/cadaver/py/secrets/README.md`): `overlay/action/trek.py` (BFS over natural holds), `route_to_room12.py` (about 4 min), `route_to_room16.py [all|a..e]` (about 5 min, `route_lib.py`), `door_reach.py` (reachability under opened doors and carried keys), `verb_decode.py` (corrected census). Snapshots: `scratchpad/cadaver/secrets_out/action/r12/`, `r16/ck_*.snap`; indexed in `scratchpad/ANCHORS.md`. Subagent working data: `scratchpad/cadaver/agent_door22/`, `agent_trek2/` (exploration scripts `e1.py`-`e58.py`, not for re-use).
- Start from: `scratchpad/cadaver/secrets_out/action/r16/ck_e_room16.snap` (room 16, hero (20,13,14,7), health 33, rucksack holds skeleton key 104, doors `$33 $3b $22 $23-$26 $20 $18` open) for the trek; `lever_after.snap` (TUNNEL, lever operated) for the route scripts; `gameplay_empire.snap` (CAVERN), `level1_loaded.snap` (level 1, room 0).
- No emulator source changed: no rebuild or regression-net run needed.
- Uncommitted and not this workstream's: `M68000/sessions/README.md` (a pre-existing line-wrap edit), `Cadaver/` (disk images), `.obsidian/`.

## Proven so far (counts in the docs)

Passes 77-82: main-loop keys, saves, rank table, assert layer, level overlay and export table, the consumer `$00fdbc` and the 94-entry verb table and grammar, the sound sequencer, the player action panel, 65 verbs measured, room-record script blocks, events 6/28/14/15/17/24 live, the regalia walk with natural input, the TUNNEL lever, jumping, regions.

83rd pass:
- **A positive door id word is an item id** (`$00716e`-`$0071bc`): `$011256` scans the type-8 list = the rucksack; descriptor byte `+7` bit 1 consumes the key and clears the word, bit 2 clears it and keeps the key, 0 makes it a permanent pass (the crown at `$2a`). Live: iron key 73 gives rucksack `(73, 57)`; without it CAVERN's east door `$3b` stalls, with it the word 73 -> 0, rucksack 1 -> 0, room 8 (`route_to_room12.py`, two byte-identical runs). Retires §13/§47c/§49-§50/§59's "id word encodes nothing / type-8 registration / permanent self-loop".
- **The census had dropped 49 level-0 objects** (odd-length blocks followed by a pad byte that is not `$17`): fixed, level 0 = 315 blocks in 224 objects, level 1 = 442 in 328, all decode exactly (`verb_decode.py`). Verb 10/27 door sites: 17 in level 0, every one of the 13 `$ffff` doors has an opener (§72 table). Retired "no opener for `$12 $1c $22`".
- **Door `$22`**: LEVER 472 in room 8 (behind `$3b`), icon 7, `05 05 | 0a 22 | 17`: word `ffff` -> 0, XP 40 -> 66, then Down along room 7's south wall at x lead 66 enters room 12 (arrival (20,13,14,7)); without the lever 11 sentinel cues, room stays 7 (subagent control).
- **Event 18 by natural input** (`route_to_room16.py`, re-run here: log identical to the agent's two runs, 15 checkpoint snapshots byte-identical): Space opens the rucksack panel, icon `$c` first in front of a class-`$b` object (239, 81, 474), fire runs `$00a682` -> `$00a6f4`; steel key 240 on 239 opens `$23-$26`, skeleton key 104 on 81 opens `$18` (door `$1c` with 474 in a side run); bronze key 155 opens `$20`. Room 12's wall (class-10 blocks gated on pickaxe 168 / axe 169) falls to two thrown pickaxes (icon `$d` select, fire with nothing in front = throw `$00a19e`). Key 104 appears only after object 325 is EXAMINEd (`SHOW #104`).
- `door_reach.py`: opening `$22` with keyed doors closed reaches 21 rooms; every later door on the road to the regalia (16 -> `$1d` -> 30 -> 31 -> 32 -> 33) is a hardcoded open link.

## Open, in priority order

1. **Walk room 16 to room 33 and the BUTTON by natural input, replacing `regalia_walk.py`'s injected entry** (doors `$1d`, `$2b`, `$2c`, `$2d` are id-0 links per `door_walk_level0.txt`). Health is the limit (33 at room 16; objects 902/904 beside 81 and 474 cost about 5 per 150,000 steps, CAVERN's south and room 68's west end more): first find how health is restored (potions: `potions_callcap.py`, food, resting, the day clock `2166(A5)`) or route around hazards. Proof: a script from `ck_e_room16.snap` ending in room 33 and then `regalia_walk.py full` without the poke, XP 0 -> 26 in the treasury.
2. **The other item doors by natural input**: `$09` (object 391, item 110, room 40), `$14` (458, item 459, room 53), `$3f`/`$40` (454, item 455 "KEY", room 24; creates three #447 objects), `$12` (FLAMEs 211/212 touched in room 38), `$2a` (BUTTON 179, room 14, plus the crown), `$29` (486, crown), keyed `$31` (167, room 69), `$3c` (244, room 4), and `$1c` as a script (it was driven only in a side run).
3. **Rooms 27-29 are unreachable by any door** even with all doors open (`door_reach.py`): what leads there (a teleport verb 37, a drop)? Read the teleport scripts (ids 2, 86, 56, 129) and any trapdoor.
4. **Events 26 and icons 3, `$e` naturally** (class-8 chests ids 83, 224; class-`$c` id 70): the rucksack panel showed icon `$c` needs class `$b`; `$00a682` also tests `2476(A5) = 8` for containers (not driven).
5. **Event 17 by a natural mover**, spell scroll and entry into level 1 room 1 without injection, byte 23's other bits, the regions' upper and z bounds.
6. **Reach the rest of the game**: walk level 1 from `level1_loaded.snap` through its teleport scripts and room blocks (room 87's disarming, room 88's level exit); level 1's census also changed (442 blocks), re-read its tables from the regenerated `scripts_level1.txt`.
7. **The Disk 2 builds**: levels' scripts and room blocks (`level2_load.py`); overlays with two extra header words, negative class-1 record, service table `$005eee`, spell 28.
8. **Still read, not run**: verbs 56 and 90, verb 44's class-bit-7 branch, verb 41's collision search; producers of events 1, 4, 10-13, 25; class handlers reached through verb 66 other than class 10; the jump's table (`$5ce6`/`$5d09`/`$5cc3`, state `2266(A5)`), `$006f80`.
9. Older loose ends in `secrets.md` "Open": F2/F3 effects, the escape-number lock, class bytes of type-6 templates, which sound ids fire in play, `$0115a2`, whether XP 60,000 is reachable; mechanics.md §67 census oddities, STOPACTI's `$f8ba`, the sconce's art source, the tile-stack direction (graphics.md 5e).

## Known traps

- **A hold starts moving about 40,000 steps after the press and then covers one grid cell per ~10,000 steps**; a stall detector needs six 20,000-step chunks (`trek.hold`), and an exact cell needs `goto` with 5,000-step chunks. Door positions: world cell -> local x = (wx - room.x0)*8, y likewise (`py/world_map.py` rectangles); a mid-edge door needs the right x/y band, a BFS over stall-to-stall holds finds only edge-aligned crossings.
- **`Repl.__init__` runs `s 1`, so a hold's outcome depends on a one-step phase**: `route_to_room16.py` snapshots, closes and reopens the REPL at the points where its explorations did (`RL`/`hops`); a continuous run diverged in room 19. After a room arrival wait about 100,000 steps before Space or a hold.
- **A fire probe sees only the object directly ahead of the facing direction**: an item that is no obstacle (key 104) is found only by stopping next to it facing it. Fire with an object in front opens a panel instead of throwing.
- **Census filters hide objects**: compare the decoded count with the data's own count bytes (`verb_decode.collect` fixed, the lesson is in the skill). Door words in the dumps and `door_walk.py` are hex door numbers; `sound ... NN` after CLEAR FLAG is the door in hex.
- "No input opens X" needs every icon of the object's panel confirmed and the z axis checked (in the skill); the item-apply path needs the rucksack panel (Space), not the fire panel.
- Fire is both the probe and the jump: with an object in front it opens the panel, with nothing in front it jumps (starts about 55,000 steps later, keeps running after release). `drv.walk` stops on an unchanged x/y, so it can end mid-jump or mid-fall; read z (`0x3833c`) as well.
- The placement table at `56(A5)` (stride `$46`) starts with the hero (index 0); rectangle bytes 0-3 are (x lead, y lead, x trail, y trail), z top/bottom are bytes 4/5; room-local coordinates (0..79); a deleted object's rect is 255s. The mover's entry flag byte is entry + 49.
- A queue entry is 8 bytes (`op.w`, `ptr.l`, `word.w`), 12 with bit 15's fourth long. Advancing the write pointer `304(A5)` by 10 misaligns the ring.
- `verbs2/h.py real()` overwrites the owner object's first block (object 2 by default, the treasury BUTTON): set `h.owner` to an unrelated event-5 object (`regalia_walk.py` uses 86, `cast_sleep_live.py` searches level 1 for one).
- A cast reads the spell at the item's body, `A2 = record + byte 12` of the record; poking `inst + 0` works only when byte 12 is 0.
- `watch` prints to stderr: read `Repl.err`, not `cmd()`'s output. `Tally.run` counts only `KEYSITES`; steps run with a bare `r.cmd('s N')` are invisible to `hits`.
- Room blocks end on a pad byte that is not `$17`; do not cap `len`. The type-8 index format the game writes is `[flag 4][offset 4*slot]`.
- Earlier traps still standing: name an event from a live drive, not from the producer body; the REPL prints at most 4096 lines; joystick fire is one `kbd ff 80` command; object ids read after an action can be wrong (a DELETE compacts the resource block); a `callcap` of verb 66 with a class other than 10 kills the REPL; `cadaver.sym` labels are nearest-below; `tools/disassemble.py` takes bare hex arguments; verbs 8 and 75 assert unless the id is in the creature list, verb 29 needs A4 in valid RAM, verb 79 with lo = hi divides by zero; zsh does not word-split an unquoted variable.
- Subagent practice that worked: one brief in the agent's own scratchpad directory with the facts taken from the docs, a hard "no build, no git, write only under your directory", and the report as the final message; re-run its script in the checkout and diff against its log before documenting (done for both agents this pass). One agent's helper treated keyed doors as open and overstated reachability (40 rooms instead of 21): check any graph computation against `door_reach.py`.

## Next session

`/resume cadaver` and start with open item 1: from `ck_e_room16.snap` walk 16 -> `$1d` -> 30 -> 31 -> 32 -> 33 by natural holds (`trek.py`), first sorting out health (how it is restored, which hazards to avoid); then run the regalia walk without the injected entry. Do item 2's doors as their items come into reach (item 455 in room 24 and the FLAMEs in room 38 are the nearest unexplored ones).
Prompt: `/resume cadaver`.
